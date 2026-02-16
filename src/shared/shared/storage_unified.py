"""
Unified storage interface that supports both Supabase and Azure backends
"""
import logging
from typing import Optional
from .config import settings

LOG = logging.getLogger(__name__)


def get_storage_backend():
    """Get the configured storage backend"""
    if settings.STORAGE_BACKEND == 'supabase':
        from . import storage_supabase as backend
        LOG.info("Using Supabase Storage backend")
    elif settings.STORAGE_BACKEND == 'azure':
        from . import storage as backend
        LOG.info("Using Azure Storage backend")
    else:
        # Default to Supabase
        from . import storage_supabase as backend
        LOG.info("Using Supabase Storage backend (default)")

    return backend


# Initialize backend
_backend = get_storage_backend()

# Export all functions from the selected backend
build_raw_blob_path = _backend.build_raw_blob_path
build_output_blob_path = _backend.build_output_blob_path


# Unified interface functions
def generate_upload_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """Generate signed URL for uploading"""
    if settings.STORAGE_BACKEND == 'supabase':
        return _backend.generate_upload_url(bucket, path, expires_in)
    else:
        # Azure uses generate_write_sas
        return _backend.generate_write_sas(container=bucket, blob_path=path, expiry_minutes=expires_in // 60)


def generate_download_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """Generate signed URL for downloading"""
    if settings.STORAGE_BACKEND == 'supabase':
        return _backend.generate_download_url(bucket, path, expires_in)
    else:
        # Azure uses generate_read_sas
        return _backend.generate_read_sas(container=bucket, blob_path=path, expiry_minutes=expires_in // 60)


def upload_file(bucket: str, path: str, data: bytes, content_type: str = 'application/octet-stream') -> dict:
    """Upload file directly"""
    if settings.STORAGE_BACKEND == 'supabase':
        return _backend.upload_file(bucket, path, data, content_type)
    else:
        # Azure doesn't have a direct upload method in the original implementation
        raise NotImplementedError("Direct upload not implemented for Azure backend")


def download_file(bucket: str, path: str) -> bytes:
    """Download file directly"""
    if settings.STORAGE_BACKEND == 'supabase':
        return _backend.download_file(bucket, path)
    else:
        # Azure doesn't have a direct download method in the original implementation
        raise NotImplementedError("Direct download not implemented for Azure backend")
