import json
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from .config import settings


def _fqdn() -> str:
    return f"{settings.SERVICEBUS_NAMESPACE}.servicebus.windows.net"


def get_client() -> ServiceBusClient:
    cred = DefaultAzureCredential()
    return ServiceBusClient(fully_qualified_namespace=_fqdn(), credential=cred)


def send_job_message(payload: dict) -> None:
    body = json.dumps(payload)
    with get_client() as client:
        sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_JOBS_QUEUE)
        with sender:
            sender.send_messages(ServiceBusMessage(body))


def send_export_message(payload: dict) -> None:
    body = json.dumps(payload)
    with get_client() as client:
        sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_EXPORTS_QUEUE)
        with sender:
            sender.send_messages(ServiceBusMessage(body))
