"""
Unified pipeline worker.

Reads from the 'jobs' queue and processes each item through the full
pipeline (bg-removal -> scene-gen -> upscale) in a single process.
Replaces the orchestrator + bg_removal_worker + scene_worker + upscale_worker.
"""
import json
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Shim: basicsr imports torchvision.transforms.functional_tensor which was
# removed in torchvision 0.17+.  Re-export from functional to keep it working.
try:
    import torchvision.transforms.functional_tensor  # noqa: F401
except ModuleNotFoundError:
    import types, torchvision.transforms.functional as _F  # noqa: E401
    torchvision = __import__("torchvision")
    torchvision.transforms.functional_tensor = types.ModuleType(
        "torchvision.transforms.functional_tensor"
    )
    import sys
    sys.modules["torchvision.transforms.functional_tensor"] = (
        torchvision.transforms.functional_tensor
    )
    # Copy commonly used functions that basicsr expects
    for _name in ("rgb_to_grayscale", "normalize", "resize", "adjust_brightness",
                  "adjust_contrast", "adjust_hue", "adjust_saturation"):
        if hasattr(_F, _name):
            setattr(torchvision.transforms.functional_tensor, _name, getattr(_F, _name))

from azure.servicebus import ServiceBusReceiveMode, AutoLockRenewer

from shared.config import settings
from shared.db import SessionLocal
from shared.models import JobItem, ItemStatus, User
from shared.storage import build_output_blob_path
from shared.pipeline import ProcessingOptions, finalize_job_status, mark_item_failed
from shared.scene_types import SCENE_PROMPTS
from shared.db_sqlalchemy import get_brand_profile, get_job_by_id as get_job_record, get_brand_style_context, get_user_subscription
from shared.util import new_id

from pipeline_worker.clients import (
    servicebus_client,
    generate_read_sas,
    generate_write_sas,
    download_blob,
    upload_blob,
    send_export_message,
)
from pipeline_worker.pipeline import execute_pipeline
from pipeline_worker.retry import TransientError, PermanentError

LOG = logging.getLogger(__name__)

# Provider singletons (initialized in main)
bg_provider = None
img_gen_provider = None
upscale_provider = None


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/healthz', '/readyz', '/livez', '/'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    LOG.info('Health server started on port %d', port)


CATEGORY_SURFACES = {
    "Jewelry & Accessories": "velvet fabric surface or polished stone slab",
    "Clothing & Apparel": "plain linen or cotton fabric draped flat",
    "Shoes & Footwear": "smooth concrete or plain wooden floor",
    "Beauty & Skincare": "smooth marble or ceramic tile surface",
    "Food & Beverages": "natural wood board or plain ceramic plate surface",
    "Electronics & Gadgets": "matte dark desk surface or brushed metal",
    "Home & Furniture": "plain hardwood floor or neutral carpet",
    "Toys & Games": "plain light-colored tabletop",
    "Sports & Outdoor": "grass turf or plain concrete surface",
    "Art & Handmade": "raw linen canvas or natural wood table",
}


def _resolve_scene_prompt(item_scene_prompt, item_scene_type, job_id, tenant_id, item_id):
    """Build scene prompt: item.scene_prompt -> scene_type lookup -> brand profile -> default."""
    if item_scene_prompt:
        LOG.info("Using item scene_prompt for item=%s", item_id)
        return item_scene_prompt

    if item_scene_type and item_scene_type in SCENE_PROMPTS:
        parts = [SCENE_PROMPTS[item_scene_type]]
        job_record = get_job_record(job_id, tenant_id)
        if job_record and job_record.get("brand_profile_id") and job_record["brand_profile_id"] != "default":
            bp = get_brand_profile(job_record["brand_profile_id"], tenant_id)
            if bp:
                if bp.get("product_category"):
                    surface = CATEGORY_SURFACES.get(bp["product_category"], "plain flat surface")
                    parts.append(surface)
                if bp.get("style_keywords"):
                    parts.append(", ".join(bp["style_keywords"]))
                if bp.get("mood"):
                    parts.append(bp["mood"])
        parts.append("completely bare scene, nothing on the surface, shallow depth of field")
        prompt = ", ".join(parts)
        LOG.info("Scene type prompt for item=%s type=%s", item_id, item_scene_type)
        return prompt

    job_record = get_job_record(job_id, tenant_id)
    if job_record and job_record.get("brand_profile_id") and job_record["brand_profile_id"] != "default":
        bp = get_brand_profile(job_record["brand_profile_id"], tenant_id)
        if bp:
            parts = []
            if bp.get("default_scene_prompt"):
                parts.append(bp["default_scene_prompt"])
            if bp.get("product_category"):
                surface = CATEGORY_SURFACES.get(bp["product_category"], "plain flat surface")
                parts.append(surface)
            if bp.get("style_keywords"):
                parts.append(", ".join(bp["style_keywords"]))
            if bp.get("mood"):
                parts.append(bp["mood"])
            # Add style context from reference images
            style_ctx = get_brand_style_context(job_record["brand_profile_id"], tenant_id)
            if style_ctx:
                parts.append(style_ctx)
            parts.append("completely bare scene, nothing on the surface, shallow depth of field")
            prompt = ", ".join(parts)
            LOG.info("Brand prompt for job=%s", job_id)
            return prompt

    return None


def _should_watermark(data: dict) -> bool:
    """Check if this job should get a watermark (free-tier user with no subscription)."""
    tenant_id = data.get('tenant_id', '')
    # Look up user by tenant_id to check subscription status
    try:
        with SessionLocal() as s:
            user = s.query(User).filter(User.tenant_id == tenant_id).first()
            if not user:
                return False  # API key users or unknown — no watermark
            # Users with active subscription skip watermark
            sub = get_user_subscription(user.id)
            if sub and sub.get('status') == 'active':
                return False
            # Users with meaningful token balance (purchased tokens) skip watermark
            if user.token_balance > 0:
                return False
            return True
    except Exception as e:
        LOG.warning("Watermark check failed (skipping watermark): %s", e)
        return False


def process_message(data: dict) -> None:
    tenant_id = data['tenant_id']
    job_id = data['job_id']
    item_id = data['item_id']
    correlation_id = data.get('correlation_id', '')

    opts = ProcessingOptions.from_dict(data.get('processing_options', {}))

    LOG.info(
        'Pipeline: job=%s item=%s (bg:%s scene:%s upscale:%s)',
        job_id, item_id, opts.remove_background, opts.generate_scene, opts.upscale,
    )

    # Validate item exists and isn't already done
    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if not item:
            LOG.warning('Item not found: %s', item_id)
            return
        if item.status == ItemStatus.completed:
            LOG.info('Item already completed, skipping: %s', item_id)
            return
        if not item.raw_blob_path:
            LOG.error('Missing raw_blob_path: %s', item_id)
            item.status = ItemStatus.failed
            item.error_message = 'Missing raw_blob_path'
            s.commit()
            return

        raw_blob_path = item.raw_blob_path
        item_scene_prompt = item.scene_prompt
        item_scene_type = item.scene_type
        item.status = ItemStatus.processing
        s.commit()

    # Resolve scene prompt
    scene_prompt = _resolve_scene_prompt(
        item_scene_prompt, item_scene_type, job_id, tenant_id, item_id
    )

    # Download raw image (single blob read for the entire pipeline)
    raw_sas = generate_read_sas(container='raw', blob_path=raw_blob_path)
    raw_bytes = download_blob(raw_sas)
    LOG.info('Downloaded raw image: %d bytes', len(raw_bytes))

    # Download saved background if "use exact background" mode
    saved_background_bytes = None
    saved_bg_path = data.get('saved_background_path')
    if saved_bg_path:
        LOG.info('Downloading saved background: %s', saved_bg_path)
        bg_sas = generate_read_sas(container='outputs', blob_path=saved_bg_path)
        saved_background_bytes = download_blob(bg_sas)
        LOG.info('Downloaded saved background: %d bytes', len(saved_background_bytes))

    # Execute full pipeline in-memory
    result = execute_pipeline(
        raw_bytes=raw_bytes,
        remove_background=opts.remove_background,
        generate_scene=opts.generate_scene,
        upscale=opts.upscale,
        scene_prompt=scene_prompt,
        bg_provider=bg_provider,
        img_gen_provider=img_gen_provider,
        upscale_provider=upscale_provider,
        upscale_enabled=settings.UPSCALE_ENABLED,
        saved_background_bytes=saved_background_bytes,
    )

    # Apply watermark for free-tier users (no subscription, low balance)
    output_bytes = result.output_bytes
    if _should_watermark(data):
        try:
            from shared.watermark import apply_watermark
            output_bytes = apply_watermark(output_bytes)
            LOG.info("Watermark applied for free-tier user")
        except Exception as e:
            LOG.warning("Watermark failed (using original): %s", e)

    # Upload final output (single blob write)
    out_id = new_id('out')
    out_path = build_output_blob_path(tenant_id, job_id, item_id, f'{out_id}.png')
    out_sas = generate_write_sas(container='outputs', blob_path=out_path)
    upload_blob(out_sas, output_bytes)
    LOG.info('Uploaded final output: %s (%d bytes)', out_path, len(output_bytes))

    # Generate SEO metadata (non-blocking — failures don't break the pipeline)
    seo_alt_text = None
    seo_filename = None
    try:
        from shared.seo_metadata import generate_seo_metadata
        brand_name = None
        product_category = None
        job_record = get_job_record(job_id, tenant_id)
        if job_record and job_record.get("brand_profile_id") and job_record["brand_profile_id"] != "default":
            bp = get_brand_profile(job_record["brand_profile_id"], tenant_id)
            if bp:
                brand_name = bp.get("name")
                product_category = bp.get("product_category")
        seo = generate_seo_metadata(
            output_bytes,
            data.get("filename", "product.jpg"),
            brand_name=brand_name,
            product_category=product_category,
        )
        seo_alt_text = seo.get("alt_text")
        seo_filename = seo.get("seo_filename")
        LOG.info("SEO metadata generated: alt=%s file=%s", seo_alt_text[:50] if seo_alt_text else None, seo_filename)
    except Exception as e:
        LOG.warning("SEO metadata generation failed (non-fatal): %s", e)

    # Mark item completed
    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if item:
            item.output_blob_path = out_path
            item.status = ItemStatus.completed
            if seo_alt_text:
                item.seo_alt_text = seo_alt_text
            if seo_filename:
                item.seo_filename = seo_filename
            s.commit()
            LOG.info('Item completed: %s', item_id)

    finalize_job_status(job_id)

    # Trigger export
    try:
        send_export_message({
            'tenant_id': tenant_id,
            'job_id': job_id,
            'item_id': item_id,
            'correlation_id': correlation_id,
        })
    except Exception as e:
        LOG.error('Export message failed: %s', e)


def _init_providers():
    """Initialize ML/API providers once at startup."""
    global bg_provider, img_gen_provider, upscale_provider

    # Background removal
    try:
        from shared.background_removal import get_provider
        bg_kwargs = {}
        if settings.BACKGROUND_REMOVAL_PROVIDER == 'remove.bg':
            bg_kwargs['api_key'] = settings.REMOVEBG_API_KEY
        elif settings.BACKGROUND_REMOVAL_PROVIDER == 'azure-vision':
            bg_kwargs['endpoint'] = settings.AZURE_VISION_ENDPOINT
            bg_kwargs['key'] = settings.AZURE_VISION_KEY
        bg_provider = get_provider(settings.BACKGROUND_REMOVAL_PROVIDER, **bg_kwargs)
        LOG.info('BG removal provider: %s', bg_provider.name)
    except Exception as e:
        LOG.error('Failed to init bg provider: %s', e)

    # Scene generation
    try:
        from shared.image_generation import get_image_gen_provider
        from shared.settings_service import get_setting
        provider_name = settings.IMAGE_GEN_PROVIDER
        api_key_attr = f'{provider_name.upper().replace(".", "_")}_API_KEY'
        api_key = get_setting(api_key_attr)
        if api_key:
            img_gen_provider = get_image_gen_provider(provider_name, api_key=api_key)
            LOG.info('Scene gen provider: %s', img_gen_provider.name)
        else:
            LOG.warning('No API key for %s — scene gen will pass through', provider_name)
    except Exception as e:
        LOG.error('Failed to init scene gen provider: %s', e)

    # Upscaling
    try:
        if settings.UPSCALE_ENABLED:
            from shared.upscaling import get_upscaling_provider
            upscale_provider = get_upscaling_provider(settings.UPSCALE_PROVIDER)
            LOG.info('Upscale provider: %s', upscale_provider.name)
        else:
            LOG.info('Upscaling: DISABLED')
    except Exception as e:
        LOG.error('Failed to init upscale provider: %s', e)


def main():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )

    LOG.info('=' * 50)
    LOG.info('OPAL PIPELINE WORKER STARTING')
    LOG.info('=' * 50)
    LOG.info('Queue: %s', settings.SERVICEBUS_JOBS_QUEUE)

    start_health_server(port=8080)
    _init_providers()

    LOG.info('Starting message processing loop...')

    while True:
        try:
            receiver = servicebus_client.get_queue_receiver(
                queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                max_wait_time=20,
                receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
            )
            renewer = AutoLockRenewer()

            with receiver:
                messages = receiver.receive_messages(max_message_count=5, max_wait_time=20)
                for m in messages:
                    item_id = None
                    job_id = None
                    try:
                        data = json.loads(str(m))
                        item_id = data.get('item_id')
                        job_id = data.get('job_id')
                        # Lock for full pipeline duration (bg + scene + upscale)
                        renewer.register(receiver, m, max_lock_renewal_duration=600)

                        process_message(data)

                        receiver.complete_message(m)
                        LOG.info('Message completed: job=%s item=%s', job_id, item_id)

                    except json.JSONDecodeError as e:
                        LOG.error('Invalid JSON: %s', e)
                        receiver.dead_letter_message(
                            m, reason='InvalidJSON', error_description=str(e)
                        )

                    except PermanentError as e:
                        LOG.error('Permanent error (dead-lettering): %s', e)
                        try:
                            mark_item_failed(job_id, item_id, str(e))
                        except Exception:
                            pass
                        receiver.dead_letter_message(
                            m, reason='PermanentError', error_description=str(e)
                        )

                    except TransientError as e:
                        LOG.warning('Transient error (abandoning for retry): %s', e)
                        try:
                            mark_item_failed(job_id, item_id, f'Transient: {e}')
                        except Exception:
                            pass
                        receiver.abandon_message(m)

                    except Exception as e:
                        LOG.exception('Unexpected error: %s', e)
                        try:
                            mark_item_failed(job_id, item_id, str(e))
                        except Exception:
                            pass
                        receiver.abandon_message(m)

                    finally:
                        try:
                            renewer.close()
                        except Exception:
                            pass

        except Exception as e:
            LOG.exception('Worker loop error: %s', e)
            time.sleep(5)


if __name__ == '__main__':
    main()
