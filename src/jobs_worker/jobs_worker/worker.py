import json
import logging
import os
import time
from typing import Any, Dict

from azure.servicebus import ServiceBusMessage, ServiceBusReceiveMode
from shared.config import settings
from shared.servicebus import get_client

LOG = logging.getLogger("jobs_worker")


def _setup_logging() -> None:
    level = (os.getenv("LOG_LEVEL") or settings.LOG_LEVEL or "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    LOG.info("jobs_worker starting (LOG_LEVEL=%s)", level)
    LOG.info(
        "Queues: jobs=%s exports=%s",
        settings.SERVICEBUS_JOBS_QUEUE,
        settings.SERVICEBUS_EXPORTS_QUEUE,
    )


def _parse_message_body(m) -> Dict[str, Any]:
    # Service Bus SDK may return body as generator of bytes chunks
    try:
        raw = b"".join([b for b in m.body])
        return json.loads(raw.decode("utf-8"))
    except Exception:
        # fallback: try string
        return {"raw": str(m)}


def main() -> None:
    _setup_logging()

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_JOBS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_EXPORTS_QUEUE)

                with receiver, sender:
                    messages = receiver.receive_messages(
                        max_message_count=10,
                        max_wait_time=20,
                    )

                    if not messages:
                        continue

                    for m in messages:
                        try:
                            payload = _parse_message_body(m)
                            LOG.info("Received job message: %s", payload)

                            # Forward as-is (Option A foundation)
                            out = ServiceBusMessage(json.dumps(payload))
                            sender.send_messages(out)

                            receiver.complete_message(m)
                            LOG.info("Forwarded to exports and completed job msg.")
                        except Exception as e:
                            # Don't lose message; release lock so it can retry
                            LOG.exception("Failed processing message; abandoning. error=%s", e)
                            try:
                                receiver.abandon_message(m)
                            except Exception:
                                # If abandon fails, lock will eventually expire
                                pass

        except Exception as e:
            LOG.exception("Worker loop error, sleeping. error=%s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
