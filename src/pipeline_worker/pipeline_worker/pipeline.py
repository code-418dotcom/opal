"""
In-memory pipeline executor.

Runs bg-removal -> scene-gen -> upscale in a single process with no
intermediate blob storage or queue hops. Each step receives bytes and
returns bytes.
"""
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Optional

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
) -> PipelineResult:
    """
    Execute the full image processing pipeline in-memory.

    Each enabled step transforms the image bytes sequentially.
    No intermediate blobs are stored — data stays in memory between steps.
    Retries automatically on transient errors (network, 5xx).
    """
    current_bytes = raw_bytes

    # Step 1: Background removal
    if remove_background and bg_provider:
        LOG.info("Step 1/3: Background removal (%s)", bg_provider.name)
        current_bytes = _run_step("bg_removal", bg_provider.remove_background, current_bytes)
    else:
        LOG.info("Step 1/3: Background removal — skipped")

    # Step 2: Scene generation + compositing
    if generate_scene and (img_gen_provider or saved_background_bytes):
        if saved_background_bytes:
            LOG.info("Step 2/3: Using saved background image (%d bytes)", len(saved_background_bytes))
            scene_bytes = saved_background_bytes
        else:
            LOG.info("Step 2/3: Scene generation (%s)", img_gen_provider.name)
            prompt = scene_prompt or (
                "empty clean surface for product placement, soft neutral background, "
                "diffused studio lighting, no objects, no clutter, photorealistic product photography backdrop"
            )
            scene_bytes = _run_step("scene_gen", img_gen_provider.generate, prompt)
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
