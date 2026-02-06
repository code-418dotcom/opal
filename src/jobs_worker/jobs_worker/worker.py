import json
import logging
import time
from azure.servicebus import ServiceBusMessage, ServiceBusReceiveMode

from shared.config import settings
from shared.servicebus import get_client


log = logging.getLogger("jobs_worker")


def _extract_payload(m) -> dict:
    """
    Supports:
    - JSON body like {"job_id":"...", "tenant_id":"demo"}
    - plain text body containing job_id only
    """
    body = b"".join([b for b in m.body]) if hasattr(m.body, "__iter__") else bytes(m.body)
    text = body.decode("utf-8", errors="ignore").strip()

    if not text:
        return {}

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # fallback: treat as job_id only
    return {"job_id": text}


def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    log.info("Starting jobs_worker. jobs_queue=%s exports_queue=%s namespace=%s",
             settings.SERVICEBUS_JOBS_QUEUE, settings.SERVICEBUS_EXPORTS_QUEUE, settings.SERVICEBUS_NAMESPACE)

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                    max_wait_time=20,
                )
                sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_EXPORTS_QUEUE)

                with receiver, sender:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    if not messages:
                        continue

                    for m in messages:
                        try:
                            payload = _extract_payload(m)

                            job_id = payload.get("job_id")
                            tenant_id = payload.get("tenant_id")

                            if not job_id:
                                log.warning("Received job message without job_id; completing to avoid poison loop.")
                                receiver.complete_message(m)
                                continue

                            out = {"job_id": job_id}
                            if tenant_id:
                                out["tenant_id"] = tenant_id

                            sender.send_messages(ServiceBusMessage(json.dumps(out)))
                            receiver.complete_message(m)

                            log.info("Forwarded job_id=%s tenant_id=%s to exports queue", job_id, tenant_id)
                        except Exception:
                            log.exception("Failed processing message. Abandoning.")
                            receiver.abandon_message(m)

        except Exception:
            log.exception("Top-level loop error. Sleeping 5s.")
            time.sleep(5)


if __name__ == "__main__":
    main()
