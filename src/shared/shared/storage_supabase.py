import re
import logging
from pathlib import Path
from typing import Optional
from supabase import create_client, Client
from .config import settings

LOG = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """Get Supabase client with service role key or anon key as fallback"""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    if not key:
        raise ValueError("Either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY must be set")
    return create_client(settings.SUPABASE_URL, key)


def _sanitize_path_component(component: str, allow_dots: bool = False) -> str:
    if not component:
        raise ValueError("Path component cannot be empty")

    pattern = r'^[a-zA-Z0-9_\-\.]+$' if allow_dots else r'^[a-zA-Z0-9_\-]+$'

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


def generate_upload_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Generate a signed URL for uploading to Supabase Storage

    Args:
        bucket: Bucket name (raw, outputs, exports)
        path: File path within bucket
        expires_in: URL expiration in seconds (default 1 hour)

    Returns:
        Signed upload URL
    """
    client = get_supabase_client()

    # Create signed URL for upload
    response = client.storage.from_(bucket).create_signed_upload_url(path)

    if 'signedURL' in response:
        return response['signedURL']
    elif 'url' in response:
        return response['url']
    else:
        raise Exception(f"Failed to generate upload URL: {response}")


def generate_download_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """
    Generate a signed URL for downloading from Supabase Storage

    Args:
        bucket: Bucket name (raw, outputs, exports)
        path: File path within bucket
        expires_in: URL expiration in seconds (default 1 hour)

    Returns:
        Signed download URL
    """
    client = get_supabase_client()

    # Create signed URL for download
    response = client.storage.from_(bucket).create_signed_url(path, expires_in)

    if isinstance(response, dict) and 'signedURL' in response:
        return response['signedURL']
    elif isinstance(response, dict) and 'url' in response:
        return response['url']
    elif isinstance(response, str):
        return response
    else:
        raise Exception(f"Failed to generate download URL: {response}")


def upload_file(bucket: str, path: str, data: bytes, content_type: str = 'application/octet-stream') -> dict:
    """
    Upload file directly to Supabase Storage

    Args:
        bucket: Bucket name
        path: File path within bucket
        data: File content as bytes
        content_type: MIME type

    Returns:
        Upload response
    """
    client = get_supabase_client()

    response = client.storage.from_(bucket).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type}
    )

    LOG.info(f"Uploaded file to {bucket}/{path}")
    return response


def download_file(bucket: str, path: str) -> bytes:
    """
    Download file from Supabase Storage

    Args:
        bucket: Bucket name
        path: File path within bucket

    Returns:
        File content as bytes
    """
    client = get_supabase_client()

    response = client.storage.from_(bucket).download(path)

    if isinstance(response, bytes):
        LOG.info(f"Downloaded file from {bucket}/{path}")
        return response
    else:
        raise Exception(f"Failed to download file: {response}")


def delete_file(bucket: str, path: str) -> bool:
    """
    Delete file from Supabase Storage

    Args:
        bucket: Bucket name
        path: File path within bucket

    Returns:
        True if successful
    """
    client = get_supabase_client()

    response = client.storage.from_(bucket).remove([path])

    LOG.info(f"Deleted file from {bucket}/{path}")
    return True


def list_files(bucket: str, path: str = '', limit: int = 100) -> list:
    """
    List files in bucket/path

    Args:
        bucket: Bucket name
        path: Directory path (optional)
        limit: Maximum number of files to return

    Returns:
        List of file objects
    """
    client = get_supabase_client()

    response = client.storage.from_(bucket).list(path, {
        'limit': limit,
        'sortBy': { 'column': 'created_at', 'order': 'desc' }
    })

    return response if isinstance(response, list) else []
