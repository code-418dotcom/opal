from datetime import datetime, timedelta, timezone
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from .config import settings


def _account_url() -> str:
    return f"https://{settings.STORAGE_ACCOUNT_NAME}.blob.core.windows.net"


def get_blob_service_client() -> BlobServiceClient:
    cred = DefaultAzureCredential()
    return BlobServiceClient(account_url=_account_url(), credential=cred)


def build_raw_blob_path(tenant_id: str, job_id: str, item_id: str, filename: str) -> str:
    safe = filename.replace("\\", "/").split("/")[-1]
    return f"{tenant_id}/jobs/{job_id}/items/{item_id}/raw/{safe}"


def build_output_blob_path(tenant_id: str, job_id: str, item_id: str, filename: str) -> str:
    safe = filename.replace("\\", "/").split("/")[-1]
    return f"{tenant_id}/jobs/{job_id}/items/{item_id}/outputs/{safe}"


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
