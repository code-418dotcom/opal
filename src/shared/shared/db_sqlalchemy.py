"""
Direct PostgreSQL database functions using SQLAlchemy.
For Azure deployment - replaces db_supabase.py functionality.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Job, JobItem, JobStatus, ItemStatus, BrandProfile
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
            processing_options=job_data.get("processing_options"),
            callback_url=job_data.get("callback_url"),
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
            "processing_options": job.processing_options,
            "callback_url": job.callback_url,
            "export_blob_path": job.export_blob_path,
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
                scene_prompt=item_data.get("scene_prompt"),
                scene_index=item_data.get("scene_index"),
                scene_type=item_data.get("scene_type"),
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
                "scene_prompt": item.scene_prompt,
                "scene_index": item.scene_index,
                "scene_type": item.scene_type,
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
            "processing_options": job.processing_options,
            "callback_url": job.callback_url,
            "export_blob_path": job.export_blob_path,
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
            "scene_prompt": item.scene_prompt,
            "scene_index": item.scene_index,
            "scene_type": item.scene_type,
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
                "scene_prompt": item.scene_prompt,
                "scene_index": item.scene_index,
                "scene_type": item.scene_type,
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
            if "scene_prompt" in updates:
                item.scene_prompt = updates["scene_prompt"]
            if "scene_index" in updates:
                item.scene_index = updates["scene_index"]
            if "scene_type" in updates:
                item.scene_type = updates["scene_type"]

            item.updated_at = datetime.utcnow()
            session.commit()


def update_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Update a job record."""
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job:
            if "export_blob_path" in updates:
                job.export_blob_path = updates["export_blob_path"]
            if "status" in updates:
                job.status = JobStatus(updates["status"])
            job.updated_at = datetime.utcnow()
            session.commit()


def get_job_items_by_filename(job_id: str, filename: str) -> List[Dict[str, Any]]:
    """Get all items for a job with a given filename (for multi-scene siblings)."""
    with SessionLocal() as session:
        items = session.query(JobItem).filter(
            JobItem.job_id == job_id,
            JobItem.filename == filename,
        ).all()

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
                "scene_prompt": item.scene_prompt,
                "scene_index": item.scene_index,
                "scene_type": item.scene_type,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            }
            for item in items
        ]


# ── Brand Profile CRUD ──────────────────────────────────────────────

def _brand_profile_to_dict(bp: BrandProfile) -> Dict[str, Any]:
    return {
        "id": bp.id,
        "tenant_id": bp.tenant_id,
        "name": bp.name,
        "default_scene_prompt": bp.default_scene_prompt,
        "style_keywords": bp.style_keywords or [],
        "color_palette": bp.color_palette or [],
        "mood": bp.mood,
        "created_at": bp.created_at.isoformat() if bp.created_at else None,
        "updated_at": bp.updated_at.isoformat() if bp.updated_at else None,
    }


def get_brand_profile(profile_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a brand profile by ID, scoped to tenant."""
    with SessionLocal() as session:
        bp = session.query(BrandProfile).filter(
            BrandProfile.id == profile_id,
            BrandProfile.tenant_id == tenant_id,
        ).first()
        return _brand_profile_to_dict(bp) if bp else None


def list_brand_profiles(tenant_id: str) -> List[Dict[str, Any]]:
    """List all brand profiles for a tenant."""
    with SessionLocal() as session:
        profiles = session.query(BrandProfile).filter(
            BrandProfile.tenant_id == tenant_id
        ).order_by(BrandProfile.created_at.desc()).all()
        return [_brand_profile_to_dict(bp) for bp in profiles]


def create_brand_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new brand profile."""
    with SessionLocal() as session:
        bp = BrandProfile(
            id=data["id"],
            tenant_id=data["tenant_id"],
            name=data["name"],
            default_scene_prompt=data.get("default_scene_prompt"),
            style_keywords=data.get("style_keywords"),
            color_palette=data.get("color_palette"),
            mood=data.get("mood"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(bp)
        session.commit()
        session.refresh(bp)
        return _brand_profile_to_dict(bp)


def update_brand_profile(profile_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a brand profile. Returns updated dict or None if not found."""
    with SessionLocal() as session:
        bp = session.query(BrandProfile).filter(
            BrandProfile.id == profile_id,
            BrandProfile.tenant_id == tenant_id,
        ).first()
        if not bp:
            return None
        for field in ("name", "default_scene_prompt", "style_keywords", "color_palette", "mood"):
            if field in updates:
                setattr(bp, field, updates[field])
        bp.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(bp)
        return _brand_profile_to_dict(bp)


def delete_brand_profile(profile_id: str, tenant_id: str) -> bool:
    """Delete a brand profile. Returns True if deleted."""
    with SessionLocal() as session:
        bp = session.query(BrandProfile).filter(
            BrandProfile.id == profile_id,
            BrandProfile.tenant_id == tenant_id,
        ).first()
        if not bp:
            return False
        session.delete(bp)
        session.commit()
        return True


# ── Job listing ──────────────────────────────────────────────────────

def list_jobs(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List jobs for a tenant with optional status filter and pagination."""
    with SessionLocal() as session:
        q = session.query(Job).filter(Job.tenant_id == tenant_id)
        if status:
            q = q.filter(Job.status == JobStatus(status))
        q = q.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        return [
            {
                "id": job.id,
                "job_id": job.id,
                "tenant_id": job.tenant_id,
                "brand_profile_id": job.brand_profile_id,
                "correlation_id": job.correlation_id,
                "status": job.status.value,
                "processing_options": job.processing_options,
                "callback_url": job.callback_url,
                "export_blob_path": job.export_blob_path,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
            for job in q.all()
        ]
