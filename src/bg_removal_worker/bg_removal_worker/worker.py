import json
import time
import logging
import httpx
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.servicebus import ServiceBusReceiveMode, AutoLockRenewer

from shared.config import settings
from shared.db import SessionLocal
from shared.models import JobItem, ItemStatus
from shared.storage import generate_read_sas, generate_write_sas, build_output_blob_path
from shared.servicebus import (get_client, send_scene_gen_message,
                                send_upscale_message, send_export_message)
from shared.pipeline import PipelineMessage, finalize_job_status, mark_item_failed
from shared.background_removal import get_provider
from shared.util import new_id

LOG = logging.getLogger(__name__)
bg_provider = None


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


def _mark_failed(item_id: str, error: str) -> None:
    if not item_id:
        return
    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if item:
            item.status = ItemStatus.failed
            item.error_message = str(error)[:4000]
            s.commit()


def _finalize_as_complete(msg: PipelineMessage, final_bytes: bytes) -> None:
    """Called when bg removal is the last enabled step."""
    item_out_id = new_id('out')
    out_path = build_output_blob_path(msg.tenant_id, msg.job_id, msg.item_id,
                                      f'{item_out_id}.png')
    out_write_sas = generate_write_sas(container='outputs', blob_path=out_path)
    upload_blob_via_sas(out_write_sas, final_bytes)

    with SessionLocal() as s:
        item = s.get(JobItem, msg.item_id)
        if item:
            item.output_blob_path = out_path
            item.status = ItemStatus.completed
            s.commit()
            LOG.info('Item completed (bg removal was last step): %s', msg.item_id)

    finalize_job_status(msg.job_id)

    send_export_message({
        'tenant_id': msg.tenant_id,
        'job_id': msg.job_id,
        'item_id': msg.item_id,
        'correlation_id': msg.correlation_id,
    })


def process_message(data: dict) -> None:
    msg = PipelineMessage.from_dict(data)
    opts = msg.processing_options

    LOG.info('bg_removal_worker: job_id=%s item_id=%s', msg.job_id, msg.item_id)

    # Guard: skip if already processing or completed (duplicate delivery)
    with SessionLocal() as s:
        item = s.get(JobItem, msg.item_id)
        if not item:
            LOG.warning('Item not found: %s', msg.item_id)
            return
        if item.status == ItemStatus.completed:
            LOG.info('Item already completed, skipping: %s', msg.item_id)
            return

    # Idempotency: if bg_removed_blob_path already set, skip re-processing
    if msg.bg_removed_blob_path:
        LOG.info('bg_removed_blob_path already set, skipping re-processing: %s', msg.item_id)
        product_bytes = None  # not needed for routing
    else:
        # Download raw image
        raw_sas = generate_read_sas(container='raw', blob_path=msg.raw_blob_path)
        input_bytes = download_blob_via_sas(raw_sas)

        if opts.remove_background and bg_provider:
            LOG.info('Removing background with %s: %s', bg_provider.name, msg.item_id)
            product_bytes = bg_provider.remove_background(input_bytes)

            # Store intermediate blob
            bg_id = new_id('bg')
            bg_blob_path = (f'{msg.tenant_id}/jobs/{msg.job_id}'
                            f'/items/{msg.item_id}/bg/{bg_id}.png')
            bg_write_sas = generate_write_sas(container='outputs', blob_path=bg_blob_path)
            upload_blob_via_sas(bg_write_sas, product_bytes)
            msg.bg_removed_blob_path = bg_blob_path
            LOG.info('BG removed blob stored: %s', bg_blob_path)
        else:
            LOG.info('BG removal skipped: %s', msg.item_id)
            product_bytes = input_bytes

    # Route to next enabled step
    if opts.generate_scene:
        LOG.info('Routing to scene-gen: %s', msg.item_id)
        send_scene_gen_message(msg.to_dict())
    elif opts.upscale:
        LOG.info('Scene disabled; routing to upscale: %s', msg.item_id)
        send_upscale_message(msg.to_dict())
    else:
        # bg removal was the last step
        if product_bytes is None:
            # idempotent re-delivery: fetch from stored blob
            container, blob_path = msg.best_available_blob()
            sas = generate_read_sas(container=container, blob_path=blob_path)
            product_bytes = download_blob_via_sas(sas)
        _finalize_as_complete(msg, product_bytes)


def main():
    global bg_provider

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )
    LOG.info('=' * 50)
    LOG.info('BG REMOVAL WORKER STARTING')
    LOG.info('=' * 50)
    LOG.info('Queue: %s', settings.SERVICEBUS_BG_REMOVAL_QUEUE)

    start_health_server(8080)

    try:
        bg_kwargs = {}
        if settings.BACKGROUND_REMOVAL_PROVIDER == 'remove.bg':
            bg_kwargs['api_key'] = settings.REMOVEBG_API_KEY
        elif settings.BACKGROUND_REMOVAL_PROVIDER == 'azure-vision':
            bg_kwargs['endpoint'] = settings.AZURE_VISION_ENDPOINT
            bg_kwargs['key'] = settings.AZURE_VISION_KEY
        bg_provider = get_provider(settings.BACKGROUND_REMOVAL_PROVIDER, **bg_kwargs)
        LOG.info('Background removal provider: %s', bg_provider.name)
    except Exception as e:
        LOG.error('Failed to init bg provider: %s', e)
        bg_provider = None

    LOG.info('Starting message processing loop...')

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_BG_REMOVAL_QUEUE,
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
                            renewer.register(receiver, m, max_lock_renewal_duration=600)
                            process_message(data)
                            receiver.complete_message(m)
                            LOG.info('Message completed: %s', item_id)
                        except json.JSONDecodeError as e:
                            LOG.error('Invalid JSON: %s', e)
                            receiver.dead_letter_message(m, reason='InvalidJSON',
                                                          error_description=str(e))
                        except Exception as e:
                            LOG.exception('Processing failed: %s', e)
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
