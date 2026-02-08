import json
import time
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.servicebus import ServiceBusReceiveMode, AutoLockRenewer
from shared.config import settings
from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus, JobStatus
from shared.storage import build_output_blob_path, generate_read_sas, generate_write_sas
from shared.servicebus import get_client, send_export_message
from shared.util import new_id

LOG = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=10))
def call_aml_sd(input_image_sas: str, tenant_id: str, job_id: str, item_id: str, correlation_id: str) -> dict:
    '''Call Azure ML Stable Diffusion endpoint for product placement.'''
    headers = {
        'Authorization': f'Bearer {settings.AML_ENDPOINT_KEY}',
        'Content-Type': 'application/json',
        'X-Correlation-Id': correlation_id,
    }
    payload = {
        'tenant_id': tenant_id,
        'job_id': job_id,
        'item_id': item_id,
        'input_image_sas': input_image_sas,
        'prompt': 'lifestyle placement stub',
    }
    with httpx.Client(timeout=180) as client:
        r = client.post(settings.AML_ENDPOINT_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def upload_blob_via_sas(sas_url: str, data: bytes) -> None:
    '''Upload blob data to Azure Storage via SAS URL with retry logic.'''
    with httpx.Client(timeout=60) as client:
        r = client.put(sas_url, content=data, headers={'x-ms-blob-type': 'BlockBlob'})
        r.raise_for_status()


def process_message(data: dict):
    '''
    Process a job message from the queue.

    Flow:
    1. Mark item as processing
    2. Call AML endpoint for processing
    3. Upload result to blob storage
    4. Mark item as completed
    5. Send message to exports queue for variant generation
    '''
    tenant_id = data['tenant_id']
    job_id = data['job_id']
    item_id = data['item_id']
    correlation_id = data.get('correlation_id', '')

    LOG.info(
        'Processing job message: tenant_id=%s job_id=%s item_id=%s correlation_id=%s',
        tenant_id, job_id, item_id, correlation_id
    )

    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if not item:
            LOG.warning('Item not found: item_id=%s', item_id)
            return
        if item.status in (ItemStatus.processing, ItemStatus.completed):
            # idempotency: ignore duplicates
            LOG.info('Item already %s, skipping: item_id=%s', item.status, item_id)
            return

        item.status = ItemStatus.processing
        s.commit()

        if not item.raw_blob_path:
            LOG.error('Missing raw_blob_path for item_id=%s', item_id)
            item.status = ItemStatus.failed
            item.error_message = 'Missing raw_blob_path'
            s.commit()
            return

        # Create READ SAS for raw image
        raw_read_sas = generate_read_sas(container='raw', blob_path=item.raw_blob_path)

    # Call AML endpoint (stub now, will be Stable Diffusion in Phase 2)
    LOG.info('Calling AML endpoint for item_id=%s', item_id)
    result = call_aml_sd(raw_read_sas, tenant_id, job_id, item_id, correlation_id)

    # AML returns an output 'image_bytes_b64' (stub) - we store it to Blob
    image_b64 = result.get('image_bytes_b64')
    if not image_b64:
        LOG.error('AML returned no image bytes for item_id=%s', item_id)
        with SessionLocal() as s:
            item = s.get(JobItem, item_id)
            item.status = ItemStatus.failed
            item.error_message = 'AML returned no image bytes'
            s.commit()
        return

    # Write output to blob using SAS (so orchestrator doesn't need account keys)
    out_name = f'{new_id(\"out\")}.png'
    out_path = build_output_blob_path(tenant_id, job_id, item_id, out_name)
    out_write_sas = generate_write_sas(container='outputs', blob_path=out_path)

    # Upload via HTTP PUT to SAS URL with retry logic
    import base64
    img_bytes = base64.b64decode(image_b64)

    LOG.info('Uploading output blob: item_id=%s path=%s', item_id, out_path)
    upload_blob_via_sas(out_write_sas, img_bytes)

    # Update item status and send to exports queue
    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        item.output_blob_path = out_path
        item.status = ItemStatus.completed
        s.commit()
        LOG.info('Item completed: item_id=%s output_path=%s', item_id, out_path)

    # Send message to exports queue for variant generation
    try:
        send_export_message({
            'tenant_id': tenant_id,
            'job_id': job_id,
            'item_id': item_id,
            'correlation_id': correlation_id,
        })
        LOG.info('Sent export message for job_id=%s', job_id)
    except Exception as e:
        # Don't fail the job if export queue send fails - it can be retried
        LOG.error('Failed to send export message: job_id=%s error=%s', job_id, e)


def finalize_job_status(job_id: str):
    '''Check all items in a job and update job status accordingly.'''
    with SessionLocal() as s:
        from shared.models import Job
        job = s.get(Job, job_id)
        if not job:
            return
        
        items = list(job.items)
        if not items:
            return
        
        # Count statuses
        statuses = [item.status for item in items]
        completed_count = statuses.count(ItemStatus.completed)
        failed_count = statuses.count(ItemStatus.failed)
        processing_count = statuses.count(ItemStatus.processing)
        
        # Determine job status
        if completed_count == len(items):
            job.status = JobStatus.completed
            LOG.info('Job completed: job_id=%s', job_id)
        elif processing_count > 0:
            job.status = JobStatus.processing
        elif failed_count == len(items):
            job.status = JobStatus.failed
            LOG.info('Job failed: job_id=%s', job_id)
        elif failed_count > 0:
            job.status = JobStatus.partial
            LOG.info('Job partially completed: job_id=%s completed=%d failed=%d', 
                    job_id, completed_count, failed_count)
        
        s.commit()


def main():
    '''Main worker loop - polls jobs queue and processes messages.'''
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s - %(message)s',
    )
    LOG.info('Orchestrator worker starting (LOG_LEVEL=%s)', settings.LOG_LEVEL)
    LOG.info('Jobs queue: %s', settings.SERVICEBUS_JOBS_QUEUE)
    LOG.info('Exports queue: %s', settings.SERVICEBUS_EXPORTS_QUEUE)
    LOG.info('AML endpoint: %s', settings.AML_ENDPOINT_URL or 'NOT SET')

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                
                # Create auto-lock renewer for long-running operations
                renewer = AutoLockRenewer()
                
                with receiver:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    for m in messages:
                        try:
                            # CRITICAL FIX: Properly extract message body
                            message_body = str(m)
                            data = json.loads(message_body)
                            
                            # Register message for auto-renewal during long AML calls
                            renewer.register(receiver, m, max_lock_renewal_duration=300)
                            
                            # Process the message
                            process_message(data)
                            
                            # Finalize job status after each item
                            finalize_job_status(data['job_id'])
                            
                            # Complete message only on success
                            receiver.complete_message(m)
                            LOG.info('Message completed: job_id=%s item_id=%s', 
                                   data.get('job_id'), data.get('item_id'))
                                   
                        except json.JSONDecodeError as e:
                            LOG.error('Invalid JSON in message: %s', e)
                            # Move to dead-letter - can't parse it
                            receiver.dead_letter_message(m, reason='InvalidJSON', 
                                                       error_description=str(e))
                        except Exception as e:
                            # record error and abandon (will retry; DLQ after maxDeliveryCount)
                            LOG.exception('Failed to process message: %s', e)
                            try:
                                item_id = data.get('item_id')
                                if item_id:
                                    with SessionLocal() as s:
                                        it = s.get(JobItem, item_id)
                                        if it and it.status != ItemStatus.completed:
                                            it.status = ItemStatus.failed
                                            it.error_message = str(e)[:4000]
                                            s.commit()
                            except Exception as db_err:
                                LOG.error('Failed to update item status in DB: %s', db_err)
                            receiver.abandon_message(m)
                        finally:
                            # Unregister from renewer
                            try:
                                renewer.close()
                            except:
                                pass
                            
        except Exception as e:
            LOG.exception('Worker loop error, sleeping 5s: %s', e)
            time.sleep(5)


if __name__ == '__main__':
    main()

