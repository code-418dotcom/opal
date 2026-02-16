"""
Unified queue interface that supports both database and Azure Service Bus backends
"""
import logging
from typing import Dict, Any, List
from .config import settings

LOG = logging.getLogger(__name__)


def get_queue_backend():
    """Get the configured queue backend"""
    if settings.QUEUE_BACKEND == 'database':
        from . import queue_supabase as backend
        LOG.info("Using database queue backend")
    elif settings.QUEUE_BACKEND == 'azure':
        from . import servicebus as backend
        LOG.info("Using Azure Service Bus backend")
    else:
        # Default to database
        from . import queue_supabase as backend
        LOG.info("Using database queue backend (default)")

    return backend


# Initialize backend
_backend = get_queue_backend()


# Unified interface
def send_job_message(payload: Dict[str, Any]) -> Any:
    """Send a message to the jobs queue"""
    return _backend.send_job_message(payload)


def send_export_message(payload: Dict[str, Any]) -> Any:
    """Send a message to the exports queue"""
    return _backend.send_export_message(payload)


def receive_messages(queue_name: str, max_count: int = 10, visibility_timeout: int = 300) -> List[Any]:
    """Receive messages from a queue"""
    if settings.QUEUE_BACKEND == 'database':
        return _backend.receive_messages(queue_name, max_count, visibility_timeout)
    else:
        # Azure Service Bus has different implementation
        # This would need to be adapted for Azure if needed
        raise NotImplementedError("receive_messages not unified for Azure backend yet")
