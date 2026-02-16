"""
Supabase database client for Bolt environment.
Uses Supabase REST API instead of direct PostgreSQL connection.
"""
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from .config import settings
import logging

log = logging.getLogger("opal")

# Initialize Supabase client
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client instance."""
    global _supabase_client

    if _supabase_client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise RuntimeError("Supabase credentials not configured")

        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        log.info("Supabase client initialized")

    return _supabase_client


def create_job_record(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a job record in the database."""
    client = get_supabase_client()
    result = client.table("jobs").insert(job_data).execute()
    return result.data[0] if result.data else {}


def create_job_item_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create multiple job item records."""
    client = get_supabase_client()
    result = client.table("job_items").insert(items).execute()
    return result.data if result.data else []


def get_job_by_id(job_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID and tenant."""
    client = get_supabase_client()
    result = client.table("jobs").select("*").eq("id", job_id).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else None


def get_job_items(job_id: str) -> List[Dict[str, Any]]:
    """Get all items for a job."""
    client = get_supabase_client()
    result = client.table("job_items").select("*").eq("job_id", job_id).execute()
    return result.data if result.data else []


def update_job_status(job_id: str, status: str) -> None:
    """Update job status."""
    client = get_supabase_client()
    client.table("jobs").update({"status": status}).eq("id", job_id).execute()


def update_job_item(item_id: str, updates: Dict[str, Any]) -> None:
    """Update a job item."""
    client = get_supabase_client()
    client.table("job_items").update(updates).eq("id", item_id).execute()


def get_job_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Get a job item by ID."""
    client = get_supabase_client()
    result = client.table("job_items").select("*").eq("id", item_id).execute()
    return result.data[0] if result.data else None
