from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from shared.config import settings

LOG = logging.getLogger(__name__)

# Module-level singleton — reused across all send calls
_client: ServiceBusClient | None = None
_credential: DefaultAzureCredential | None = None


def get_fully_qualified_namespace() -> str:
    """Convert namespace to fully qualified domain name."""
    ns = settings.SERVICEBUS_NAMESPACE.strip()
    if ns.endswith(".servicebus.windows.net"):
        return ns
    return f"{ns}.servicebus.windows.net"


def get_client() -> ServiceBusClient:
    """Return a shared Service Bus client (creates on first call)."""
    global _client, _credential
    if _client is None:
        fqns = get_fully_qualified_namespace()
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        _client = ServiceBusClient(fully_qualified_namespace=fqns, credential=_credential)
        LOG.info("Created shared ServiceBusClient for %s", fqns)
    return _client


def _send_to_queue(queue_name: str, payload: Dict[str, Any]) -> None:
    """Send a single message to a named queue."""
    client = get_client()
    sender = client.get_queue_sender(queue_name=queue_name)
    with sender:
        sender.send_messages(ServiceBusMessage(json.dumps(payload)))


def send_job_message(payload: Dict[str, Any]) -> None:
    """Send a message to the jobs queue."""
    try:
        _send_to_queue(settings.SERVICEBUS_JOBS_QUEUE, payload)
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


def send_job_messages_batch(payloads: List[Dict[str, Any]]) -> None:
    """Send multiple messages to the jobs queue in a single batch."""
    if not payloads:
        return
    try:
        client = get_client()
        sender = client.get_queue_sender(queue_name=settings.SERVICEBUS_JOBS_QUEUE)
        with sender:
            messages = [ServiceBusMessage(json.dumps(p)) for p in payloads]
            sender.send_messages(messages)
            LOG.info(
                "Sent %d job messages to queue=%s job_id=%s",
                len(payloads),
                settings.SERVICEBUS_JOBS_QUEUE,
                payloads[0].get("job_id"),
            )
    except Exception as e:
        LOG.error(
            "Failed to send batch job messages: job_id=%s count=%d error=%s",
            payloads[0].get("job_id") if payloads else "?",
            len(payloads),
            e,
        )
        raise


def send_bg_removal_message(payload: Dict[str, Any]) -> None:
    """Send pipeline message to bg-removal queue."""
    try:
        _send_to_queue(settings.SERVICEBUS_BG_REMOVAL_QUEUE, payload)
        LOG.info("Sent bg-removal message: job_id=%s item_id=%s",
                 payload.get("job_id"), payload.get("item_id"))
    except Exception as e:
        LOG.error("Failed to send bg-removal message: job_id=%s error=%s",
                  payload.get("job_id"), e)
        raise


def send_scene_gen_message(payload: Dict[str, Any]) -> None:
    """Send pipeline message to scene-gen queue."""
    try:
        _send_to_queue(settings.SERVICEBUS_SCENE_GEN_QUEUE, payload)
        LOG.info("Sent scene-gen message: job_id=%s item_id=%s",
                 payload.get("job_id"), payload.get("item_id"))
    except Exception as e:
        LOG.error("Failed to send scene-gen message: job_id=%s error=%s",
                  payload.get("job_id"), e)
        raise


def send_upscale_message(payload: Dict[str, Any]) -> None:
    """Send pipeline message to upscale queue."""
    try:
        _send_to_queue(settings.SERVICEBUS_UPSCALE_QUEUE, payload)
        LOG.info("Sent upscale message: job_id=%s item_id=%s",
                 payload.get("job_id"), payload.get("item_id"))
    except Exception as e:
        LOG.error("Failed to send upscale message: job_id=%s error=%s",
                  payload.get("job_id"), e)
        raise


def send_export_message(payload: Dict[str, Any]) -> None:
    """Send a message to the exports queue."""
    try:
        _send_to_queue(settings.SERVICEBUS_EXPORTS_QUEUE, payload)
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
