import json
import logging
import time
from azure.servicebus import ServiceBusReceiveMode

from shared.config import settings
from shared.servicebus import get_client

log = logging.getLogger("export_worker")


def _extract_payload(m) -> dict:
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
    return {"job_id": text}


def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    log.info("Starting export_worker. exports_queue=%s namespace=%s",
             settings.SERVICEBUS_EXPORTS_QUEUE, settings.SERVICEBUS_NAMESPACE)

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_EXPORTS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                with receiver:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    for m in messages:
                        try:
                            payload = _extract_payload(m)
                            job_id = payload.get("job_id")
                            tenant_id = payload.get("tenant_id")

                            if not job_id:
                                log.warning("Export message without job_id; completing to avoid poison loop.")
                                receiver.complete_message(m)
                                continue

                            # TODO: Option A “truth”: load job from DB and do real work here
                            log.info("Processing export for job_id=%s tenant_id=%s", job_id, tenant_id)

                            # Stub: complete
                            receiver.complete_message(m)
                            log.info("Completed export message for job_id=%s", job_id)

                        except Exception:
                            log.exception("Export processing failed; abandoning message.")
                            receiver.abandon_message(m)

        except Exception:
            log.exception("Top-level loop error. Sleeping 5s.")
            time.sleep(5)


if __name__ == "__main__":
    main()
