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
import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional, Callable

from PIL import Image, ImageFilter
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from pipeline_worker.retry import TransientError, PermanentError, classify_and_raise


def _detect_image_size(image_bytes: bytes) -> str:
    """Detect the best fal.ai image_size preset to match input aspect ratio.

    Returns one of the fal.ai presets: square_hd, portrait_4_3, portrait_16_9,
    landscape_4_3, landscape_16_9.
    """
    img = Image.open(BytesIO(image_bytes))
    w, h = img.size
    ratio = w / h

    if ratio > 1.5:
        return "landscape_16_9"
    elif ratio > 1.15:
        return "landscape_4_3"
    elif ratio > 0.87:
        return "square_hd"
    elif ratio > 0.67:
        return "portrait_4_3"
    else:
        return "portrait_16_9"

LOG = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    output_bytes: bytes
    error: Optional[str] = None
    failed_step: Optional[str] = None
    step_timings: dict = field(default_factory=dict)


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


def _preserve_product_details(product_rgba_bytes: bytes, scene_bytes: bytes,
                               erode_px: int = 8) -> bytes:
    """Composite original product pixels back onto the AI-generated scene.

    FLUX.2 Pro Edit produces great scenes but can corrupt fine details like
    text, logos, and patterns on the product surface. This function pastes
    the original product pixels back using an eroded alpha mask, so:
      - The product interior (text, labels, patterns) is pixel-perfect
      - Edge pixels (where FLUX added lighting/shadows) are kept from the scene
    """
    product = Image.open(BytesIO(product_rgba_bytes)).convert("RGBA")
    scene = Image.open(BytesIO(scene_bytes)).convert("RGBA")

    # Resize product to match scene dimensions (FLUX may change size)
    if product.size != scene.size:
        product = product.resize(scene.size, Image.Resampling.LANCZOS)

    # Extract and erode the alpha mask — shrink edges so FLUX's lighting
    # bleeds through at the boundary, but interior stays original
    alpha = product.split()[3]
    eroded_alpha = alpha.filter(ImageFilter.MinFilter(size=erode_px * 2 + 1))

    # Composite: scene as base, original product pixels pasted using eroded mask
    scene.paste(product, (0, 0), eroded_alpha)

    output = BytesIO()
    scene.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def _run_step(step_name: str, fn, *args, timings: dict | None = None, **kwargs):
    """Run a pipeline step with error classification and timing."""
    t0 = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        if timings is not None:
            timings[step_name] = round(time.monotonic() - t0, 2)
        return result
    except (TransientError, PermanentError):
        if timings is not None:
            timings[step_name] = round(time.monotonic() - t0, 2)
        raise
    except Exception as e:
        if timings is not None:
            timings[step_name] = round(time.monotonic() - t0, 2)
        LOG.error("Step '%s' failed: %s", step_name, e)
        classify_and_raise(e)


def _build_edit_prompt(scene_prompt: Optional[str], angle_type: Optional[str] = None) -> str:
    """Build a FLUX.2 Pro Edit prompt that instructs the model to place the
    product from the reference image into the described scene, optionally
    with a specific lighting style."""
    scene_desc = scene_prompt or (
        "a clean, professional product photography setting with soft studio "
        "lighting and a neutral background"
    )

    # Inject lighting instruction when requested — never reposition the product
    lighting_instruction = ""
    if angle_type:
        from shared.scene_types import ANGLE_PROMPTS
        angle_desc = ANGLE_PROMPTS.get(angle_type)
        if angle_desc:
            lighting_instruction = f" Use this lighting style: {angle_desc}."

    return (
        f"Change only the background to {scene_desc}. "
        "The product in the image must remain completely unchanged — "
        "same position, same orientation, same shape, same colors, same proportions, "
        "same textures, same labels, same text. "
        "Do not move, rotate, reposition, redraw, or reinterpret the product. "
        "Only replace the empty space around it with the new scene."
        f"{lighting_instruction} "
        "Add soft shadows and reflections on the surface beneath the product. "
        "Professional e-commerce product photography."
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
    timings: dict[str, float] = {}
    pipeline_start = time.monotonic()

    # Step 1: Background removal
    if remove_background and bg_provider:
        LOG.info("Step 1/3: Background removal (%s)", bg_provider.name)
        current_bytes = _run_step("bg_removal", bg_provider.remove_background, current_bytes, timings=timings)
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

            # Save bg-removed product for detail preservation after scene gen
            product_rgba_bytes = current_bytes

            # Match output dimensions to input image orientation
            image_size = _detect_image_size(raw_bytes)
            LOG.info("Detected input orientation → image_size=%s", image_size)

            # Upload bg-removed product so the API can fetch it
            if upload_tmp_image:
                product_url = _run_step(
                    "upload_product", upload_tmp_image, current_bytes, timings=timings,
                )
                gen_kwargs = {"image_urls": [product_url], "image_size": image_size}
            else:
                LOG.warning("No upload_tmp_image callback — edit mode without image reference")
                gen_kwargs = {"image_size": image_size}

            current_bytes = _run_step(
                "scene_edit", img_gen_provider.generate, edit_prompt, timings=timings, **gen_kwargs,
            )

            # Composite original product pixels back to preserve text/labels/details
            LOG.info("Step 2.5/3: Preserving product details (text, labels, patterns)")
            current_bytes = _run_step(
                "preserve_details", _preserve_product_details,
                product_rgba_bytes, current_bytes, timings=timings,
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
                scene_bytes = _run_step("scene_gen", img_gen_provider.generate, prompt, timings=timings, **gen_kwargs)
            current_bytes = _run_step("composite", composite_product_on_scene, current_bytes, scene_bytes, timings=timings)
    else:
        LOG.info("Step 2/3: Scene generation — skipped")

    # Step 3: Upscaling
    if upscale and upscale_provider and upscale_enabled:
        LOG.info("Step 3/3: Upscaling (%s)", upscale_provider.name)
        current_bytes = _run_step("upscale", upscale_provider.upscale, current_bytes, timings=timings)
    else:
        LOG.info("Step 3/3: Upscaling — skipped")

    timings["total"] = round(time.monotonic() - pipeline_start, 2)
    LOG.info("Pipeline timings: %s", timings)

    return PipelineResult(output_bytes=current_bytes, step_timings=timings)
