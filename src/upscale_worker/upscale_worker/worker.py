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
from shared.servicebus import get_client, send_export_message
from shared.pipeline import PipelineMessage, finalize_job_status
from shared.upscaling import get_upscaling_provider
from shared.util import new_id

LOG = logging.getLogger(__name__)
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


def process_message(data: dict) -> None:
    msg = PipelineMessage.from_dict(data)
    opts = msg.processing_options

    LOG.info('upscale_worker: job_id=%s item_id=%s', msg.job_id, msg.item_id)

    # Fetch best available input (scene > bg_removed > raw)
    container, blob_path = msg.best_available_blob()
    input_sas = generate_read_sas(container=container, blob_path=blob_path)
    input_bytes = download_blob_via_sas(input_sas)

    if opts.upscale and upscale_provider and settings.UPSCALE_ENABLED:
        LOG.info('Upscaling with %s: %s', upscale_provider.name, msg.item_id)
        final_bytes = upscale_provider.upscale(input_bytes)
    else:
        LOG.info('Upscaling skipped: %s', msg.item_id)
        final_bytes = input_bytes

    # Write final output — only upscale_worker sets output_blob_path
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
            LOG.info('Item completed: %s', msg.item_id)

    finalize_job_status(msg.job_id)

    send_export_message({
        'tenant_id': msg.tenant_id,
        'job_id': msg.job_id,
        'item_id': msg.item_id,
        'correlation_id': msg.correlation_id,
    })


def main():
    global upscale_provider

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )
    LOG.info('=' * 50)
    LOG.info('UPSCALE WORKER STARTING')
    LOG.info('=' * 50)
    LOG.info('Queue: %s', settings.SERVICEBUS_UPSCALE_QUEUE)

    start_health_server(8080)

    try:
        if settings.UPSCALE_ENABLED:
            upscale_provider = get_upscaling_provider(settings.UPSCALE_PROVIDER)
            LOG.info('Upscaling provider: %s', upscale_provider.name)
        else:
            LOG.info('Upscaling: DISABLED')
    except Exception as e:
        LOG.error('Failed to init upscale provider: %s', e)
        upscale_provider = None

    LOG.info('Starting message processing loop...')

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_UPSCALE_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                renewer = AutoLockRenewer()
                with receiver:
                    messages = receiver.receive_messages(max_message_count=5, max_wait_time=20)
                    for m in messages:
                        item_id = None
                        try:
                            data = json.loads(str(m))
                            item_id = data.get('item_id')
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
                                _mark_failed(item_id, str(e))
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
