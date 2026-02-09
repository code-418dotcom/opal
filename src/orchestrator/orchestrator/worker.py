# Updated: 2026-02-09 08:55
import json
import time
import logging
import httpx
import base64
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.servicebus import ServiceBusReceiveMode, AutoLockRenewer
from shared.config import settings
from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus, JobStatus
from shared.storage import build_output_blob_path, generate_read_sas, generate_write_sas
from shared.servicebus import get_client, send_export_message
from shared.util import new_id

LOG = logging.getLogger(__name__)


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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def remove_background(image_bytes: bytes) -> bytes:
    """Remove background using Azure AI Vision 4.0 Image Segmentation"""
    vision_endpoint = settings.AZURE_VISION_ENDPOINT
    vision_key = settings.AZURE_VISION_KEY
    
    # Azure AI Vision 4.0 API endpoint for image segmentation
    url = f"{vision_endpoint.rstrip('/')}/computervision/imageanalysis:segment?api-version=2023-02-01-preview&mode=backgroundRemoval"
    
    headers = {
        'Ocp-Apim-Subscription-Key': vision_key,
        'Content-Type': 'application/octet-stream'
    }
    
    LOG.info('Calling Azure AI Vision for background removal')
    
    with httpx.Client(timeout=120) as client:
        response = client.post(url, headers=headers, content=image_bytes)
        
        if response.status_code == 200:
            LOG.info('Background removal successful')
            return response.content
        else:
            LOG.error('Background removal failed: %s - %s', response.status_code, response.text)
            raise Exception(f'Azure Vision API error: {response.status_code}')


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
        # Download input image
        LOG.info('Downloading input image: %s', item_id)
        input_bytes = download_blob_via_sas(raw_read_sas)
        
        # Remove background using Azure AI Vision
        LOG.info('Removing background: %s', item_id)
        output_bytes = remove_background(input_bytes)
        
        # Upload processed image
        item_out_id = new_id('out')
        out_name = f'{item_out_id}.png'
        out_path = build_output_blob_path(tenant_id, job_id, item_id, out_name)
        out_write_sas = generate_write_sas(container='outputs', blob_path=out_path)

        LOG.info('Uploading output: %s -> %s', item_id, out_path)
        upload_blob_via_sas(out_write_sas, output_bytes)

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
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s - %(message)s'
    )
    LOG.info('Orchestrator starting with Azure AI Vision')
    LOG.info('Queue: %s', settings.SERVICEBUS_JOBS_QUEUE)
    LOG.info('Vision Endpoint: %s', settings.AZURE_VISION_ENDPOINT)

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
                            except:
                                pass
        except Exception as e:
            LOG.exception('Worker loop error: %s', e)
            time.sleep(5)


if __name__ == '__main__':
    main()

