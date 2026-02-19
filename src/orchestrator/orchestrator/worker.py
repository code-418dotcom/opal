# Updated: 2026-02-19 - Refactored to coordinator: routes jobs to step queues
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
from shared.storage import build_output_blob_path, generate_read_sas, generate_write_sas
from shared.servicebus import (
    get_client,
    send_export_message,
    send_bg_removal_message,
    send_scene_gen_message,
    send_upscale_message,
)
from shared.pipeline import PipelineMessage, ProcessingOptions, finalize_job_status
from shared.util import new_id

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
        pass


def start_health_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    LOG.info('Health server started on port %d', port)
    return server


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def _upload_blob(sas_url: str, data: bytes) -> None:
    with httpx.Client(timeout=60) as client:
        r = client.put(sas_url, content=data, headers={'x-ms-blob-type': 'BlockBlob'})
        r.raise_for_status()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def _download_blob(sas_url: str) -> bytes:
    with httpx.Client(timeout=60) as client:
        r = client.get(sas_url)
        r.raise_for_status()
        return r.content


def _passthrough(msg: PipelineMessage) -> None:
    """All steps disabled — copy raw blob straight to output and mark complete."""
    raw_sas = generate_read_sas(container='raw', blob_path=msg.raw_blob_path)
    raw_bytes = _download_blob(raw_sas)

    out_id = new_id('out')
    out_path = build_output_blob_path(msg.tenant_id, msg.job_id, msg.item_id, f'{out_id}.png')
    out_sas = generate_write_sas(container='outputs', blob_path=out_path)
    _upload_blob(out_sas, raw_bytes)

    with SessionLocal() as s:
        item = s.get(JobItem, msg.item_id)
        if item:
            item.output_blob_path = out_path
            item.status = ItemStatus.completed
            s.commit()
            LOG.info('Passthrough complete: %s', msg.item_id)

    finalize_job_status(msg.job_id)

    try:
        send_export_message({
            'tenant_id': msg.tenant_id,
            'job_id': msg.job_id,
            'item_id': msg.item_id,
            'correlation_id': msg.correlation_id,
        })
    except Exception as e:
        LOG.error('Export message failed for passthrough: %s', e)


def process_message(data: dict) -> None:
    tenant_id = data['tenant_id']
    job_id = data['job_id']
    item_id = data['item_id']
    correlation_id = data.get('correlation_id', '')

    opts = ProcessingOptions.from_dict(data.get('processing_options', {}))

    LOG.info(
        'Coordinating: job=%s item=%s (bg:%s scene:%s upscale:%s)',
        job_id, item_id, opts.remove_background, opts.generate_scene, opts.upscale,
    )

    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if not item:
            LOG.warning('Item not found: %s', item_id)
            return
        if item.status in (ItemStatus.processing, ItemStatus.completed):
            LOG.info('Item already %s, skipping: %s', item.status, item_id)
            return
        if not item.raw_blob_path:
            LOG.error('Missing raw_blob_path: %s', item_id)
            item.status = ItemStatus.failed
            item.error_message = 'Missing raw_blob_path'
            s.commit()
            return

        raw_blob_path = item.raw_blob_path
        item.status = ItemStatus.processing
        s.commit()

    msg = PipelineMessage(
        job_id=job_id,
        item_id=item_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        raw_blob_path=raw_blob_path,
        processing_options=opts,
    )

    if opts.remove_background:
        LOG.info('Routing to bg-removal queue: %s', item_id)
        send_bg_removal_message(msg.to_dict())
    elif opts.generate_scene:
        LOG.info('Routing to scene-gen queue: %s', item_id)
        send_scene_gen_message(msg.to_dict())
    elif opts.upscale:
        LOG.info('Routing to upscale queue: %s', item_id)
        send_upscale_message(msg.to_dict())
    else:
        LOG.info('All steps disabled — passthrough: %s', item_id)
        _passthrough(msg)


def main():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )

    LOG.info('=' * 50)
    LOG.info('OPAL COORDINATOR STARTING')
    LOG.info('=' * 50)
    LOG.info('Queue: %s', settings.SERVICEBUS_JOBS_QUEUE)

    start_health_server(port=8080)

    LOG.info('Starting coordination loop...')

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
                            renewer.register(receiver, m, max_lock_renewal_duration=120)

                            process_message(data)

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
                            except Exception as ex:
                                LOG.warning('Lock renewer close failed: %s', ex)
        except Exception as e:
            LOG.exception('Worker loop error: %s', e)
            time.sleep(5)


if __name__ == '__main__':
    main()
