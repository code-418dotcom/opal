from __future__ import annotations

import json
import logging
from typing import Any, Dict

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from shared.config import settings

LOG = logging.getLogger(__name__)


def get_fully_qualified_namespace() -> str:
    """Convert namespace to fully qualified domain name."""
    # settings.SERVICEBUS_NAMESPACE is like: "opal-xxx-bus"
    # Service Bus client needs: "<namespace>.servicebus.windows.net"
    ns = settings.SERVICEBUS_NAMESPACE.strip()
    if ns.endswith(".servicebus.windows.net"):
        return ns
    return f"{ns}.servicebus.windows.net"


def get_client() -> ServiceBusClient:
    """Create Service Bus client with managed identity authentication."""
    fqns = get_fully_qualified_namespace()
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return ServiceBusClient(fully_qualified_namespace=fqns, credential=credential)


def send_job_message(payload: Dict[str, Any]) -> None:
    """
    Send a message to the jobs queue.
    
    Args:
        payload: Dictionary containing job message data (tenant_id, job_id, item_id, correlation_id)
    
    Raises:
        Exception: If message sending fails
    """
    try:
        with get_client() as client:
            sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_JOBS_QUEUE)
            with sender:
                message_body = json.dumps(payload)
                message = ServiceBusMessage(message_body)
                sender.send_messages(message)
                LOG.info(
                    "Sent job message to queue=%s job_id=%s item_id=%s",
                    settings.SERVICEBUS_JOBS_QUEUE,
                    payload.get("job_id"),
                    payload.get("item_id"),
                )
    except Exception as e:
        LOG.error(
            "Failed to send job message: job_id=%s item_id=%s error=%s",
            payload.get("job_id"),
            payload.get("item_id"),
            e,
        )
        raise


def send_export_message(payload: Dict[str, Any]) -> None:
    """
    Send a message to the exports queue.
    
    Args:
        payload: Dictionary containing export message data (tenant_id, job_id, correlation_id)
    
    Raises:
        Exception: If message sending fails
    """
    try:
        with get_client() as client:
            sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_EXPORTS_QUEUE)
            with sender:
                message_body = json.dumps(payload)
                message = ServiceBusMessage(message_body)
                sender.send_messages(message)
                LOG.info(
                    "Sent export message to queue=%s job_id=%s",
                    settings.SERVICEBUS_EXPORTS_QUEUE,
                    payload.get("job_id"),
                )
    except Exception as e:
        LOG.error(
            "Failed to send export message: job_id=%s error=%s",
            payload.get("job_id"),
            e,
        )
        raise
