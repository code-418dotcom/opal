# Updated: 2026-02-09 - Added upscaling (5-step pipeline)
import json
import time
import logging
import httpx
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.servicebus import ServiceBusReceiveMode, AutoLockRenewer
from shared.config import settings
from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus, JobStatus
from shared.storage import build_output_blob_path, generate_read_sas, generate_write_sas
from shared.servicebus import get_client, send_export_message
from shared.util import new_id
from shared.background_removal import get_provider
from shared.image_generation import get_image_gen_provider
from shared.upscaling import get_upscaling_provider

LOG = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check endpoint for Container Apps probes"""
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
        # Suppress health check logs to avoid spam
        pass


def start_health_server(port=8080):
    """Start health check HTTP server in background thread"""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    LOG.info(f'Health server started on port {port}')
    return server

# Providers will be initialized in main() after logging is setup
bg_provider = None
img_gen_provider = None
upscale_provider = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def upload_blob_via_sas(sas_url: str, data: bytes) -> None:
    with httpx.Client(timeout=60) as client:
        r = client.put(sas_url, content=data, headers={'x-ms-blob-type': 'BlockBlob'})
        r.raise_for_status()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def download_blob_via_sas(sas_url: str) -> bytes:
    with httpx.Client(timeout=60) as client:
        r = client.get(sas_url)
        r.raise_for_status()
        return r.content


def composite_product_on_scene(product_png: bytes, scene_jpg: bytes) -> bytes:
    """Composite transparent product onto generated scene"""
    # Load images
    product_img = Image.open(BytesIO(product_png)).convert('RGBA')
    scene_img = Image.open(BytesIO(scene_jpg)).convert('RGBA')
    
    # Resize product to fit scene (max 60% of scene dimensions)
    max_width = int(scene_img.width * 0.6)
    max_height = int(scene_img.height * 0.6)
    
    product_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    
    # Center product on scene
    x = (scene_img.width - product_img.width) // 2
    y = (scene_img.height - product_img.height) // 2
    
    # Composite
    scene_img.paste(product_img, (x, y), product_img)
    
    # Convert to RGB and save as PNG
    output = BytesIO()
    final_img = scene_img.convert('RGB')
    final_img.save(output, format='PNG', optimize=True)
    
    return output.getvalue()


def process_message(data: dict):
    tenant_id = data['tenant_id']
    job_id = data['job_id']
    item_id = data['item_id']
    correlation_id = data.get('correlation_id', '')

    LOG.info('Processing: tenant_id=%s job_id=%s item_id=%s', tenant_id, job_id, item_id)

    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if not item:
            LOG.warning('Item not found: %s', item_id)
            return
        if item.status in (ItemStatus.processing, ItemStatus.completed):
            LOG.info('Item already %s: %s', item.status, item_id)
            return

        item.status = ItemStatus.processing
        s.commit()

        if not item.raw_blob_path:
            LOG.error('Missing raw_blob_path: %s', item_id)
            item.status = ItemStatus.failed
            item.error_message = 'Missing raw_blob_path'
            s.commit()
            return

        raw_read_sas = generate_read_sas(container='raw', blob_path=item.raw_blob_path)

    try:
        # Step 1: Download input
        LOG.info('[1/5] Downloading input: %s', item_id)
        input_bytes = download_blob_via_sas(raw_read_sas)
        
        # Step 2: Remove background
        if bg_provider:
            LOG.info('[2/5] Removing background with %s: %s', bg_provider.name, item_id)
            product_png = bg_provider.remove_background(input_bytes)
        else:
            LOG.warning('[2/5] No background removal - using input')
            product_png = input_bytes
        
        # Step 3: Generate lifestyle scene
        if img_gen_provider:
            LOG.info('[3/5] Generating lifestyle scene with %s: %s', img_gen_provider.name, item_id)
            
            # TODO: Get prompt from brand profile (for now, use default)
            prompt = "modern minimalist living room, bright natural lighting, wooden floor, white walls, plants, photorealistic, high quality"
            
            scene_bytes = img_gen_provider.generate(prompt)
            
            # Step 4: Composite product onto scene
            LOG.info('[4/5] Compositing product onto scene: %s', item_id)
            composited_bytes = composite_product_on_scene(product_png, scene_bytes)
        else:
            LOG.warning('[3/5] No image generation - using background-removed product')
            composited_bytes = product_png
        
        # Step 5: Upscale final image
        if upscale_provider and settings.UPSCALE_ENABLED:
            LOG.info('[5/5] Upscaling with %s: %s', upscale_provider.name, item_id)
            final_bytes = upscale_provider.upscale(composited_bytes)
        else:
            LOG.warning('[5/5] Upscaling disabled - using composited image')
            final_bytes = composited_bytes
        
        # Upload final result
        item_out_id = new_id('out')
        out_name = f'{item_out_id}.png'
        out_path = build_output_blob_path(tenant_id, job_id, item_id, out_name)
        out_write_sas = generate_write_sas(container='outputs', blob_path=out_path)

        LOG.info('Uploading final output: %s -> %s', item_id, out_path)
        upload_blob_via_sas(out_write_sas, final_bytes)

        # Mark as completed
        with SessionLocal() as s:
            item = s.get(JobItem, item_id)
            item.output_blob_path = out_path
            item.status = ItemStatus.completed
            s.commit()
            LOG.info('Item completed: %s', item_id)

        # Send to exports queue
        try:
            send_export_message({
                'tenant_id': tenant_id,
                'job_id': job_id,
                'item_id': item_id,
                'correlation_id': correlation_id
            })
            LOG.info('Export message sent: %s', job_id)
        except Exception as e:
            LOG.error('Export message failed: %s - %s', job_id, e)
            
    except Exception as e:
        LOG.exception('Processing failed: %s', e)
        with SessionLocal() as s:
            item = s.get(JobItem, item_id)
            if item:
                item.status = ItemStatus.failed
                item.error_message = str(e)[:4000]
                s.commit()
        raise


def finalize_job_status(job_id: str):
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job:
            return
        
        items = list(job.items)
        if not items:
            return
        
        statuses = [item.status for item in items]
        completed = statuses.count(ItemStatus.completed)
        failed = statuses.count(ItemStatus.failed)
        processing = statuses.count(ItemStatus.processing)
        
        if completed == len(items):
            job.status = JobStatus.completed
            LOG.info('Job COMPLETED: %s', job_id)
        elif processing > 0:
            job.status = JobStatus.processing
        elif failed == len(items):
            job.status = JobStatus.failed
        elif failed > 0:
            job.status = JobStatus.partial
        
        s.commit()


def main():
    global bg_provider, img_gen_provider, upscale_provider
    
    # Configure logging FIRST
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )
    
    LOG.info('=' * 50)
    LOG.info('OPAL ORCHESTRATOR STARTING')
    LOG.info('=' * 50)
    LOG.info('Queue: %s', settings.SERVICEBUS_JOBS_QUEUE)

    # Start health check server for Container Apps probes
    start_health_server(port=8080)

    # NOW initialize providers AFTER logging is configured
    try:
        # Provider-specific kwargs
        bg_kwargs = {}
        if settings.BACKGROUND_REMOVAL_PROVIDER == 'remove.bg':
            bg_kwargs['api_key'] = settings.REMOVEBG_API_KEY
        elif settings.BACKGROUND_REMOVAL_PROVIDER == 'azure-vision':
            bg_kwargs['endpoint'] = settings.AZURE_VISION_ENDPOINT
            bg_kwargs['key'] = settings.AZURE_VISION_KEY
        
        bg_provider = get_provider(
            provider_name=settings.BACKGROUND_REMOVAL_PROVIDER,
            **bg_kwargs
        )
        LOG.info('Background removal: %s', bg_provider.name)
    except Exception as e:
        LOG.error('Failed to init background removal: %s', e, exc_info=True)
        bg_provider = None
    
    try:
        img_gen_provider = get_image_gen_provider(
            provider_name=settings.IMAGE_GEN_PROVIDER,
            api_key=getattr(settings, f'{settings.IMAGE_GEN_PROVIDER.upper().replace(".", "_")}_API_KEY', '')
        )
        LOG.info('Image generation: %s', img_gen_provider.name)
    except Exception as e:
        LOG.error('Failed to init image generation: %s', e, exc_info=True)
        img_gen_provider = None
    
    try:
        if settings.UPSCALE_ENABLED:
            upscale_provider = get_upscaling_provider(
                provider_name=settings.UPSCALE_PROVIDER
            )
            LOG.info('Upscaling: %s', upscale_provider.name)
        else:
            LOG.info('Upscaling: DISABLED')
    except Exception as e:
        LOG.error('Failed to init upscaling: %s', e, exc_info=True)
        upscale_provider = None
    
    if not bg_provider and not img_gen_provider:
        LOG.warning('No AI providers configured - will pass through images')

    LOG.info('Starting message processing loop...')
    
    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK
                )
                renewer = AutoLockRenewer()
                
                with receiver:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    for m in messages:
                        try:
                            data = json.loads(str(m))
                            renewer.register(receiver, m, max_lock_renewal_duration=300)
                            
                            process_message(data)
                            finalize_job_status(data['job_id'])
                            
                            receiver.complete_message(m)
                            LOG.info('Message completed: %s', data.get('job_id'))
                        except json.JSONDecodeError as e:
                            LOG.error('Invalid JSON: %s', e)
                            receiver.dead_letter_message(m, reason='InvalidJSON', error_description=str(e))
                        except Exception as e:
                            LOG.exception('Message processing failed: %s', e)
                            receiver.abandon_message(m)
                        finally:
                            try:
                                renewer.close()
                            except Exception as e:
                                LOG.warning("Lock renewer close failed: %s", e)
        except Exception as e:
            LOG.exception('Worker loop error: %s', e)
            time.sleep(5)


if __name__ == '__main__':
    main()