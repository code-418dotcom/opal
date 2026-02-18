"""
Direct PostgreSQL database functions using SQLAlchemy.
For Azure deployment - replaces db_supabase.py functionality.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Job, JobItem, JobStatus, ItemStatus
from datetime import datetime
import logging

log = logging.getLogger("opal")


def create_job_record(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a job record in the database."""
    with SessionLocal() as session:
        job = Job(
            id=job_data["id"],
            tenant_id=job_data["tenant_id"],
            brand_profile_id=job_data["brand_profile_id"],
            correlation_id=job_data["correlation_id"],
            status=JobStatus(job_data.get("status", "created")),
            created_at=job_data.get("created_at", datetime.utcnow()),
            updated_at=job_data.get("updated_at", datetime.utcnow()),
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        return {
            "id": job.id,
            "job_id": job.id,
            "tenant_id": job.tenant_id,
            "brand_profile_id": job.brand_profile_id,
            "correlation_id": job.correlation_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


def create_job_item_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create multiple job item records."""
    with SessionLocal() as session:
        job_items = []
        for item_data in items:
            item = JobItem(
                id=item_data["id"],
                job_id=item_data["job_id"],
                tenant_id=item_data["tenant_id"],
                filename=item_data["filename"],
                status=ItemStatus(item_data.get("status", "created")),
                raw_blob_path=item_data.get("raw_blob_path"),
                output_blob_path=item_data.get("output_blob_path"),
                created_at=item_data.get("created_at", datetime.utcnow()),
                updated_at=item_data.get("updated_at", datetime.utcnow()),
            )
            session.add(item)
            job_items.append(item)

        session.commit()

        return [
            {
                "id": item.id,
                "item_id": item.id,
                "job_id": item.job_id,
                "tenant_id": item.tenant_id,
                "filename": item.filename,
                "status": item.status.value,
                "raw_blob_path": item.raw_blob_path,
                "output_blob_path": item.output_blob_path,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in job_items
        ]


def get_job_by_id(job_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a job by ID."""
    with SessionLocal() as session:
        job = session.query(Job).filter(
            Job.id == job_id,
            Job.tenant_id == tenant_id
        ).first()

        if not job:
            return None

        return {
            "id": job.id,
            "job_id": job.id,
            "tenant_id": job.tenant_id,
            "brand_profile_id": job.brand_profile_id,
            "correlation_id": job.correlation_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }


def get_job_item(item_id: str) -> Optional[Dict[str, Any]]:
    """Get a job item by ID."""
    with SessionLocal() as session:
        item = session.get(JobItem, item_id)

        if not item:
            return None

        return {
            "id": item.id,
            "item_id": item.id,
            "job_id": item.job_id,
            "tenant_id": item.tenant_id,
            "filename": item.filename,
            "status": item.status.value,
            "raw_blob_path": item.raw_blob_path,
            "output_blob_path": item.output_blob_path,
            "error_message": item.error_message,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }


def get_job_items(job_id: str) -> List[Dict[str, Any]]:
    """Get all items for a job."""
    with SessionLocal() as session:
        items = session.query(JobItem).filter(JobItem.job_id == job_id).all()

        return [
            {
                "id": item.id,
                "item_id": item.id,
                "job_id": item.job_id,
                "tenant_id": item.tenant_id,
                "filename": item.filename,
                "status": item.status.value,
                "raw_blob_path": item.raw_blob_path,
                "output_blob_path": item.output_blob_path,
                "error_message": item.error_message,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in items
        ]


def update_job_status(job_id: str, status: str) -> None:
    """Update job status."""
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job:
            job.status = JobStatus(status)
            job.updated_at = datetime.utcnow()
            session.commit()


def update_job_item(item_id: str, updates: Dict[str, Any]) -> None:
    """Update a job item."""
    with SessionLocal() as session:
        item = session.get(JobItem, item_id)
        if item:
            if "status" in updates:
                item.status = ItemStatus(updates["status"])
            if "raw_blob_path" in updates:
                item.raw_blob_path = updates["raw_blob_path"]
            if "output_blob_path" in updates:
                item.output_blob_path = updates["output_blob_path"]
            if "error_message" in updates:
                item.error_message = updates["error_message"]

            item.updated_at = datetime.utcnow()
            session.commit()
