import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from .config import settings


def _account_url() -> str:
    return f"https://{settings.STORAGE_ACCOUNT_NAME}.blob.core.windows.net"


def get_blob_service_client() -> BlobServiceClient:
    cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return BlobServiceClient(account_url=_account_url(), credential=cred)


def _sanitize_path_component(component: str, allow_dots: bool = False) -> str:
    if not component:
        raise ValueError("Path component cannot be empty")

    if allow_dots:
        pattern = r'^[a-zA-Z0-9_\-\.]+$'
    else:
        pattern = r'^[a-zA-Z0-9_\-]+$'

    if not re.match(pattern, component):
        raise ValueError(f"Invalid path component: {component}")

    if '..' in component:
        raise ValueError(f"Path traversal attempt detected: {component}")

    return component


def _sanitize_filename(filename: str) -> str:
    safe = Path(filename).name

    if not safe or safe in ('.', '..'):
        raise ValueError(f"Invalid filename: {filename}")

    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', safe):
        raise ValueError(f"Filename contains invalid characters: {filename}")

    return safe


def build_raw_blob_path(tenant_id: str, job_id: str, item_id: str, filename: str) -> str:
    tenant = _sanitize_path_component(tenant_id)
    job = _sanitize_path_component(job_id)
    item = _sanitize_path_component(item_id)
    safe_filename = _sanitize_filename(filename)

    return f"{tenant}/jobs/{job}/items/{item}/raw/{safe_filename}"


def build_output_blob_path(tenant_id: str, job_id: str, item_id: str, filename: str) -> str:
    tenant = _sanitize_path_component(tenant_id)
    job = _sanitize_path_component(job_id)
    item = _sanitize_path_component(item_id)
    safe_filename = _sanitize_filename(filename)

    return f"{tenant}/jobs/{job}/items/{item}/outputs/{safe_filename}"


def generate_write_sas(container: str, blob_path: str, expiry_minutes: int = 30) -> str:
    # Uses user delegation key with AAD auth
    client = get_blob_service_client()
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    delegation_key = client.get_user_delegation_key(key_start_time=start, key_expiry_time=expiry)
    sas = generate_blob_sas(
        account_name=settings.STORAGE_ACCOUNT_NAME,
        container_name=container,
        blob_name=blob_path,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expiry,
        start=start,
    )
    return f"{_account_url()}/{container}/{blob_path}?{sas}"


def generate_read_sas(container: str, blob_path: str, expiry_minutes: int = 30) -> str:
    client = get_blob_service_client()
    start = datetime.now(timezone.utc) - timedelta(minutes=5)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    delegation_key = client.get_user_delegation_key(key_start_time=start, key_expiry_time=expiry)
    sas = generate_blob_sas(
        account_name=settings.STORAGE_ACCOUNT_NAME,
        container_name=container,
        blob_name=blob_path,
        user_delegation_key=delegation_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
        start=start,
    )
    return f"{_account_url()}/{container}/{blob_path}?{sas}"
