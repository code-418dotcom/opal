"""
Direct PostgreSQL database functions using SQLAlchemy.
For Azure deployment - replaces db_supabase.py functionality.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Job, JobItem, JobStatus, ItemStatus, BrandProfile, SceneTemplate
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
                saved_background_path=item_data.get("saved_background_path"),
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
                "saved_background_path": item.saved_background_path,
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
            "saved_background_path": item.saved_background_path,
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
                "saved_background_path": item.saved_background_path,
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
            if "saved_background_path" in updates:
                item.saved_background_path = updates["saved_background_path"]

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
                "saved_background_path": item.saved_background_path,
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
        "default_scene_count": bp.default_scene_count or 1,
        "default_scene_types": bp.default_scene_types or [],
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
            default_scene_count=data.get("default_scene_count", 1),
            default_scene_types=data.get("default_scene_types"),
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
        for field in ("name", "default_scene_prompt", "style_keywords", "color_palette", "mood", "default_scene_count", "default_scene_types"):
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


# ── Scene Template CRUD ────────────────────────────────────────────

def _scene_template_to_dict(st: SceneTemplate) -> Dict[str, Any]:
    return {
        "id": st.id,
        "tenant_id": st.tenant_id,
        "brand_profile_id": st.brand_profile_id,
        "name": st.name,
        "prompt": st.prompt,
        "preview_blob_path": st.preview_blob_path,
        "scene_type": st.scene_type,
        "created_at": st.created_at.isoformat() if st.created_at else None,
        "updated_at": st.updated_at.isoformat() if st.updated_at else None,
    }


def list_scene_templates(tenant_id: str, brand_profile_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List scene templates for a tenant, optionally filtered by brand profile."""
    with SessionLocal() as session:
        q = session.query(SceneTemplate).filter(SceneTemplate.tenant_id == tenant_id)
        if brand_profile_id:
            q = q.filter(SceneTemplate.brand_profile_id == brand_profile_id)
        q = q.order_by(SceneTemplate.created_at.desc())
        return [_scene_template_to_dict(st) for st in q.all()]


def get_scene_template(template_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get a scene template by ID, scoped to tenant."""
    with SessionLocal() as session:
        st = session.query(SceneTemplate).filter(
            SceneTemplate.id == template_id,
            SceneTemplate.tenant_id == tenant_id,
        ).first()
        return _scene_template_to_dict(st) if st else None


def create_scene_template(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new scene template."""
    with SessionLocal() as session:
        st = SceneTemplate(
            id=data["id"],
            tenant_id=data["tenant_id"],
            brand_profile_id=data.get("brand_profile_id"),
            name=data["name"],
            prompt=data["prompt"],
            preview_blob_path=data.get("preview_blob_path"),
            scene_type=data.get("scene_type"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(st)
        session.commit()
        session.refresh(st)
        return _scene_template_to_dict(st)


def update_scene_template(template_id: str, tenant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a scene template. Returns updated dict or None if not found."""
    with SessionLocal() as session:
        st = session.query(SceneTemplate).filter(
            SceneTemplate.id == template_id,
            SceneTemplate.tenant_id == tenant_id,
        ).first()
        if not st:
            return None
        for field in ("name", "prompt", "preview_blob_path", "scene_type", "brand_profile_id"):
            if field in updates:
                setattr(st, field, updates[field])
        st.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(st)
        return _scene_template_to_dict(st)


def delete_scene_template(template_id: str, tenant_id: str) -> bool:
    """Delete a scene template. Returns True if deleted."""
    with SessionLocal() as session:
        st = session.query(SceneTemplate).filter(
            SceneTemplate.id == template_id,
            SceneTemplate.tenant_id == tenant_id,
        ).first()
        if not st:
            return False
        session.delete(st)
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
