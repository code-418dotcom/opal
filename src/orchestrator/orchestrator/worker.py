import json
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from azure.servicebus import ServiceBusReceiveMode
from shared.config import settings
from shared.db import SessionLocal
from shared.models import JobItem, ItemStatus
from shared.storage import build_output_blob_path, generate_read_sas, generate_write_sas
from shared.servicebus import get_client
from shared.util import new_id


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=10))
def call_aml_sd(input_image_sas: str, tenant_id: str, job_id: str, item_id: str, correlation_id: str) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.AML_ENDPOINT_KEY}",
        "Content-Type": "application/json",
        "X-Correlation-Id": correlation_id,
    }
    payload = {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "item_id": item_id,
        "input_image_sas": input_image_sas,
        "prompt": "lifestyle placement stub",
    }
    with httpx.Client(timeout=180) as client:
        r = client.post(settings.AML_ENDPOINT_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()


def process_message(msg: str):
    data = json.loads(msg)
    tenant_id = data["tenant_id"]
    job_id = data["job_id"]
    item_id = data["item_id"]
    correlation_id = data.get("correlation_id", "")

    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if not item:
            return
        if item.status in (ItemStatus.processing, ItemStatus.completed):
            # idempotency: ignore duplicates
            return

        item.status = ItemStatus.processing
        s.commit()

        if not item.raw_blob_path:
            item.status = ItemStatus.failed
            item.error_message = "Missing raw_blob_path"
            s.commit()
            return

        # Create READ SAS for raw
        raw_read_sas = generate_read_sas(container="raw", blob_path=item.raw_blob_path)

    # Call AML endpoint (stub now)
    result = call_aml_sd(raw_read_sas, tenant_id, job_id, item_id, correlation_id)

    # AML returns an output "image_bytes_b64" (stub) - we store it to Blob
    image_b64 = result.get("image_bytes_b64")
    if not image_b64:
        with SessionLocal() as s:
            item = s.get(JobItem, item_id)
            item.status = ItemStatus.failed
            item.error_message = "AML returned no image bytes"
            s.commit()
        return

    # Write output to blob using SAS (so orchestrator doesn't need account keys)
    out_name = f"{new_id('out')}.png"
    out_path = build_output_blob_path(tenant_id, job_id, item_id, out_name)
    out_write_sas = generate_write_sas(container="outputs", blob_path=out_path)

    # Upload via HTTP PUT to SAS URL
    import base64
    img_bytes = base64.b64decode(image_b64)

    with httpx.Client(timeout=60) as client:
        put = client.put(out_write_sas, content=img_bytes, headers={"x-ms-blob-type": "BlockBlob"})
        put.raise_for_status()

    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        item.output_blob_path = out_path
        item.status = ItemStatus.completed
        s.commit()


def main():
    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                with receiver:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    for m in messages:
                        try:
                            process_message(str(m))
                            receiver.complete_message(m)
                        except Exception as e:
                            # record error and abandon (will retry; DLQ after maxDeliveryCount)
                            try:
                                data = json.loads(str(m))
                                item_id = data.get("item_id")
                                if item_id:
                                    with SessionLocal() as s:
                                        it = s.get(JobItem, item_id)
                                        if it and it.status != ItemStatus.completed:
                                            it.status = ItemStatus.failed
                                            it.error_message = str(e)[:4000]
                                            s.commit()
                            except Exception:
                                pass
                            receiver.abandon_message(m)
        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    main()
