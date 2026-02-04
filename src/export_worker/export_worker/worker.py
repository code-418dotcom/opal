import time
from azure.servicebus import ServiceBusReceiveMode
from shared.config import settings
from shared.servicebus import get_client

def main():
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
                        # Stub: just complete
                        receiver.complete_message(m)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    main()
