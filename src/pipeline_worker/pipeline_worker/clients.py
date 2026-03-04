"""
Singleton clients for the pipeline worker.

All Azure SDK and HTTP clients are initialized once at startup and reused
across all message processing to eliminate per-call connection overhead.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

from shared.config import settings

LOG = logging.getLogger(__name__)

_credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)

# Singleton HTTP client with connection pooling
http_client = httpx.Client(
    timeout=120,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
)

# Singleton blob service client
_account_url = f"https://{settings.STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
blob_service_client = BlobServiceClient(account_url=_account_url, credential=_credential)

# Singleton Service Bus client
_fqns = settings.SERVICEBUS_NAMESPACE.strip()
if not _fqns.endswith(".servicebus.windows.net"):
    _fqns = f"{_fqns}.servicebus.windows.net"
servicebus_client = ServiceBusClient(fully_qualified_namespace=_fqns, credential=_credential)

# Cached user delegation key
_delegation_key = None
_delegation_key_expiry = None


def get_delegation_key():
    """Get cached user delegation key, refreshing when near expiry."""
    global _delegation_key, _delegation_key_expiry
    now = datetime.now(timezone.utc)
    if _delegation_key is None or (_delegation_key_expiry - now) < timedelta(minutes=5):
        start = now - timedelta(minutes=5)
        expiry = now + timedelta(hours=1)
        _delegation_key = blob_service_client.get_user_delegation_key(start, expiry)
        _delegation_key_expiry = expiry
        LOG.debug("Refreshed delegation key (expires %s)", expiry.isoformat())
    return _delegation_key


def generate_read_sas(container: str, blob_path: str, expiry_minutes: int = 30) -> str:
    """Generate a read SAS URL using cached delegation key."""
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    dk = get_delegation_key()
    sas = generate_blob_sas(
        account_name=settings.STORAGE_ACCOUNT_NAME,
        container_name=container,
        blob_name=blob_path,
        user_delegation_key=dk,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
        start=start,
    )
    return f"{_account_url}/{container}/{blob_path}?{sas}"


def generate_write_sas(container: str, blob_path: str, expiry_minutes: int = 30) -> str:
    """Generate a write SAS URL using cached delegation key."""
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    dk = get_delegation_key()
    sas = generate_blob_sas(
        account_name=settings.STORAGE_ACCOUNT_NAME,
        container_name=container,
        blob_name=blob_path,
        user_delegation_key=dk,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expiry,
        start=start,
    )
    return f"{_account_url}/{container}/{blob_path}?{sas}"


def download_blob(sas_url: str) -> bytes:
    """Download blob using the pooled HTTP client."""
    r = http_client.get(sas_url)
    r.raise_for_status()
    return r.content


def upload_blob(sas_url: str, data: bytes) -> None:
    """Upload blob using the pooled HTTP client."""
    r = http_client.put(sas_url, content=data, headers={'x-ms-blob-type': 'BlockBlob'})
    r.raise_for_status()


def send_export_message(payload: dict) -> None:
    """Send export message using the singleton Service Bus client."""
    import json
    sender = servicebus_client.get_queue_sender(queue_name=settings.SERVICEBUS_EXPORTS_QUEUE)
    with sender:
        sender.send_messages(ServiceBusMessage(json.dumps(payload)))
    LOG.info("Sent export message: job_id=%s", payload.get("job_id"))
