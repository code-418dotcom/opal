"""
In-memory pipeline executor.

Runs bg-removal -> scene-gen -> upscale in a single process with no
intermediate blob storage or queue hops. Each step receives bytes and
returns bytes.

Scene generation has two modes:
  • Legacy (FLUX-dev): generate background, then PIL-composite product on top
  • Edit  (FLUX.2 Pro Edit): upload bg-removed product, let the model
    composite it natively with realistic lighting / shadows
"""
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Optional, Callable

from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from pipeline_worker.retry import TransientError, PermanentError, classify_and_raise

LOG = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    output_bytes: bytes
    error: Optional[str] = None
    failed_step: Optional[str] = None


def composite_product_on_scene(product_png: bytes, scene_jpg: bytes) -> bytes:
    """Composite transparent product PNG onto generated scene background."""
    product_img = Image.open(BytesIO(product_png)).convert('RGBA')
    scene_img = Image.open(BytesIO(scene_jpg)).convert('RGBA')

    max_width = int(scene_img.width * 0.6)
    max_height = int(scene_img.height * 0.6)
    product_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    x = (scene_img.width - product_img.width) // 2
    y = (scene_img.height - product_img.height) // 2
    scene_img.paste(product_img, (x, y), product_img)

    output = BytesIO()
    scene_img.convert('RGB').save(output, format='PNG', optimize=True)
    return output.getvalue()


def _run_step(step_name: str, fn, *args, **kwargs):
    """Run a pipeline step with error classification."""
    try:
        return fn(*args, **kwargs)
    except (TransientError, PermanentError):
        raise
    except Exception as e:
        LOG.error("Step '%s' failed: %s", step_name, e)
        classify_and_raise(e)


def _build_edit_prompt(scene_prompt: Optional[str], angle_type: Optional[str] = None) -> str:
    """Build a FLUX.2 Pro Edit prompt that instructs the model to place the
    product from the reference image into the described scene, optionally
    from a specific camera angle."""
    scene_desc = scene_prompt or (
        "a clean, professional product photography setting with soft studio "
        "lighting and a neutral background"
    )

    # Inject angle instruction when requested
    angle_instruction = ""
    if angle_type:
        from shared.scene_types import ANGLE_PROMPTS
        angle_desc = ANGLE_PROMPTS.get(angle_type)
        if angle_desc:
            angle_instruction = f" Show a {angle_desc}."

    return (
        f"Place the product from the image into {scene_desc}."
        f"{angle_instruction} "
        "Create natural lighting, soft shadows and reflections. "
        "Keep the product exactly as-is — do not alter its shape, color or details. "
        "Professional e-commerce product photography style."
    )


@retry(
    retry=retry_if_exception_type(TransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=30),
    reraise=True,
)
def execute_pipeline(
    raw_bytes: bytes,
    remove_background: bool,
    generate_scene: bool,
    upscale: bool,
    scene_prompt: Optional[str],
    bg_provider=None,
    img_gen_provider=None,
    upscale_provider=None,
    upscale_enabled: bool = True,
    saved_background_bytes: Optional[bytes] = None,
    upload_tmp_image: Optional[Callable[[bytes], str]] = None,
    angle_type: Optional[str] = None,
) -> PipelineResult:
    """
    Execute the full image processing pipeline in-memory.

    Each enabled step transforms the image bytes sequentially.
    No intermediate blobs are stored — data stays in memory between steps.
    Retries automatically on transient errors (network, 5xx).

    Args:
        upload_tmp_image: Optional callback that uploads bytes to a
            publicly-accessible URL and returns that URL. Required for
            edit-mode providers (FLUX.2 Pro Edit) which need to receive
            the product image as a URL.
    """
    current_bytes = raw_bytes

    # Step 1: Background removal
    if remove_background and bg_provider:
        LOG.info("Step 1/3: Background removal (%s)", bg_provider.name)
        current_bytes = _run_step("bg_removal", bg_provider.remove_background, current_bytes)
    else:
        LOG.info("Step 1/3: Background removal — skipped")

    # Step 2: Scene generation
    if generate_scene and (img_gen_provider or saved_background_bytes):
        # --- Edit mode: provider composites the product natively ----------
        use_edit = (
            img_gen_provider
            and getattr(img_gen_provider, "supports_edit", False)
            and not saved_background_bytes
        )

        if use_edit:
            LOG.info("Step 2/3: Scene edit (%s) angle=%s", img_gen_provider.name, angle_type)
            edit_prompt = _build_edit_prompt(scene_prompt, angle_type=angle_type)

            # Upload bg-removed product so the API can fetch it
            if upload_tmp_image:
                product_url = _run_step(
                    "upload_product", upload_tmp_image, current_bytes,
                )
                gen_kwargs = {"image_urls": [product_url]}
            else:
                LOG.warning("No upload_tmp_image callback — edit mode without image reference")
                gen_kwargs = {}

            current_bytes = _run_step(
                "scene_edit", img_gen_provider.generate, edit_prompt, **gen_kwargs,
            )
        else:
            # --- Legacy mode: generate background, then PIL composite -----
            if saved_background_bytes:
                LOG.info("Step 2/3: Using saved background image (%d bytes)", len(saved_background_bytes))
                scene_bytes = saved_background_bytes
            else:
                LOG.info("Step 2/3: Scene generation (%s)", img_gen_provider.name)
                prompt = scene_prompt or (
                    "plain flat surface, solid soft neutral background, single diffused light source, "
                    "shallow depth of field, completely bare scene, nothing on the surface"
                )
                # Pass runtime-configurable generation settings
                gen_kwargs = {}
                try:
                    from shared.settings_service import get_setting
                    steps = get_setting("SCENE_GEN_STEPS")
                    if steps:
                        gen_kwargs["num_inference_steps"] = int(steps)
                    guidance = get_setting("SCENE_GEN_GUIDANCE")
                    if guidance:
                        gen_kwargs["guidance_scale"] = float(guidance)
                    fal_ep = get_setting("FAL_ENDPOINT")
                    if fal_ep:
                        gen_kwargs["fal_endpoint"] = fal_ep
                except Exception:
                    pass
                scene_bytes = _run_step("scene_gen", img_gen_provider.generate, prompt, **gen_kwargs)
            current_bytes = _run_step("composite", composite_product_on_scene, current_bytes, scene_bytes)
    else:
        LOG.info("Step 2/3: Scene generation — skipped")

    # Step 3: Upscaling
    if upscale and upscale_provider and upscale_enabled:
        LOG.info("Step 3/3: Upscaling (%s)", upscale_provider.name)
        current_bytes = _run_step("upscale", upscale_provider.upscale, current_bytes)
    else:
        LOG.info("Step 3/3: Upscaling — skipped")

    return PipelineResult(output_bytes=current_bytes)
