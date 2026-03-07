"""
Direct PostgreSQL database functions using SQLAlchemy.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import (
    Job, JobItem, JobStatus, ItemStatus, BrandProfile, BrandReferenceImage,
    SceneTemplate, User,
    TokenTransaction, TokenTxType, TokenPackage, Payment, PaymentStatus,
    Integration, IntegrationProvider, IntegrationStatus, IntegrationCost,
    AdminSetting,
)
from datetime import datetime, timedelta
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
            "seo_alt_text": item.seo_alt_text,
            "seo_filename": item.seo_filename,
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


# ── User CRUD ─────────────────────────────────────────────────────────

def _user_to_dict(u: User) -> Dict[str, Any]:
    return {
        "id": u.id,
        "entra_subject_id": u.entra_subject_id,
        "email": u.email,
        "tenant_id": u.tenant_id,
        "display_name": u.display_name,
        "token_balance": u.token_balance,
        "is_admin": u.is_admin,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


def get_user_by_entra_subject(subject_id: str) -> Optional[Dict[str, Any]]:
    """Find user by Entra subject ID (from JWT 'sub' claim)."""
    with SessionLocal() as session:
        u = session.query(User).filter(User.entra_subject_id == subject_id).first()
        return _user_to_dict(u) if u else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by primary key."""
    with SessionLocal() as session:
        u = session.get(User, user_id)
        return _user_to_dict(u) if u else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find user by email address."""
    with SessionLocal() as session:
        u = session.query(User).filter(User.email == email).first()
        return _user_to_dict(u) if u else None


def link_entra_subject(user_id: str, entra_subject_id: str) -> Optional[Dict[str, Any]]:
    """Set the entra_subject_id on an existing user (links pre-created user to Entra login)."""
    with SessionLocal() as session:
        u = session.get(User, user_id)
        if not u:
            return None
        u.entra_subject_id = entra_subject_id
        u.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(u)
        return _user_to_dict(u)


def user_count() -> int:
    """Return total number of users."""
    with SessionLocal() as session:
        return session.query(func.count(User.id)).scalar() or 0


def admin_exists() -> bool:
    """Check if at least one admin user exists."""
    with SessionLocal() as session:
        return session.query(User).filter(User.is_admin == True).first() is not None


def promote_first_user_to_admin() -> Optional[Dict[str, Any]]:
    """If no admin exists, promote the earliest-created user. Returns promoted user or None."""
    with SessionLocal() as session:
        # Quick check — avoid write path if an admin already exists
        has_admin = session.query(User).filter(User.is_admin == True).first()
        if has_admin:
            return None
        first = session.query(User).order_by(User.created_at.asc()).first()
        if not first:
            return None
        first.is_admin = True
        first.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(first)
        return _user_to_dict(first)


def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create user record. Called on first login (JIT provisioning)."""
    with SessionLocal() as session:
        u = User(
            id=data["id"],
            entra_subject_id=data.get("entra_subject_id"),
            email=data["email"],
            tenant_id=data["tenant_id"],
            display_name=data.get("display_name"),
            token_balance=data.get("token_balance", 0),
            is_admin=data.get("is_admin", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(u)
        session.commit()
        session.refresh(u)
        return _user_to_dict(u)


def update_user_token_balance(user_id: str, delta: int) -> Optional[int]:
    """Atomically adjust token_balance. Returns new balance or None if insufficient."""
    with SessionLocal() as session:
        result = session.execute(
            text(
                "UPDATE users SET token_balance = token_balance + :delta, "
                "updated_at = now() "
                "WHERE id = :user_id AND token_balance + :delta >= 0 "
                "RETURNING token_balance"
            ),
            {"user_id": user_id, "delta": delta},
        )
        row = result.fetchone()
        session.commit()
        return row[0] if row else None


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
        "product_category": bp.product_category,
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
            product_category=data.get("product_category"),
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
        for field in ("name", "default_scene_prompt", "style_keywords", "color_palette", "mood", "product_category", "default_scene_count", "default_scene_types"):
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


# ── Brand Reference Images ─────────────────────────────────────────

def list_brand_reference_images(brand_profile_id: str, tenant_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        images = session.query(BrandReferenceImage).filter(
            BrandReferenceImage.brand_profile_id == brand_profile_id,
            BrandReferenceImage.tenant_id == tenant_id,
        ).order_by(BrandReferenceImage.created_at).all()
        return [
            {
                "id": img.id,
                "brand_profile_id": img.brand_profile_id,
                "blob_path": img.blob_path,
                "extracted_style": img.extracted_style,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ]


def create_brand_reference_image(data: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as session:
        img = BrandReferenceImage(
            id=data["id"],
            brand_profile_id=data["brand_profile_id"],
            tenant_id=data["tenant_id"],
            blob_path=data["blob_path"],
            extracted_style=data.get("extracted_style"),
        )
        session.add(img)
        session.commit()
        session.refresh(img)
        return {
            "id": img.id,
            "brand_profile_id": img.brand_profile_id,
            "blob_path": img.blob_path,
            "extracted_style": img.extracted_style,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        }


def delete_brand_reference_image(image_id: str, tenant_id: str) -> bool:
    with SessionLocal() as session:
        img = session.query(BrandReferenceImage).filter(
            BrandReferenceImage.id == image_id,
            BrandReferenceImage.tenant_id == tenant_id,
        ).first()
        if not img:
            return False
        session.delete(img)
        session.commit()
        return True


def update_reference_image_style(image_id: str, extracted_style: dict) -> bool:
    with SessionLocal() as session:
        img = session.get(BrandReferenceImage, image_id)
        if not img:
            return False
        img.extracted_style = extracted_style
        session.commit()
        return True


def get_brand_style_context(brand_profile_id: str, tenant_id: str) -> Optional[str]:
    """Build a style context string from all reference images for a brand profile.
    Returns a comma-separated string of extracted style cues, or None."""
    images = list_brand_reference_images(brand_profile_id, tenant_id)
    if not images:
        return None

    style_parts = []
    for img in images:
        style = img.get("extracted_style")
        if style:
            if style.get("colors"):
                style_parts.append(f"colors: {', '.join(style['colors'][:5])}")
            if style.get("lighting"):
                style_parts.append(f"lighting: {style['lighting']}")
            if style.get("mood"):
                style_parts.append(f"mood: {style['mood']}")
            if style.get("keywords"):
                style_parts.extend(style["keywords"][:5])

    return ", ".join(style_parts) if style_parts else None


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


# ── Billing CRUD ─────────────────────────────────────────────────────

def list_token_packages(active_only: bool = True) -> List[Dict[str, Any]]:
    """List available token packages."""
    with SessionLocal() as session:
        q = session.query(TokenPackage)
        if active_only:
            q = q.filter(TokenPackage.active == True)
        q = q.order_by(TokenPackage.price_cents.asc())
        return [
            {
                "id": p.id,
                "name": p.name,
                "tokens": p.tokens,
                "price_cents": p.price_cents,
                "currency": p.currency,
                "active": p.active,
            }
            for p in q.all()
        ]


def get_token_package(package_id: str) -> Optional[Dict[str, Any]]:
    """Get a token package by ID."""
    with SessionLocal() as session:
        p = session.query(TokenPackage).filter(TokenPackage.id == package_id).first()
        if not p:
            return None
        return {
            "id": p.id,
            "name": p.name,
            "tokens": p.tokens,
            "price_cents": p.price_cents,
            "currency": p.currency,
            "active": p.active,
        }


def create_payment(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new payment record."""
    with SessionLocal() as session:
        payment = Payment(
            id=data["id"],
            user_id=data["user_id"],
            package_id=data["package_id"],
            mollie_payment_id=data.get("mollie_payment_id"),
            amount_cents=data["amount_cents"],
            currency=data.get("currency", "EUR"),
            status=PaymentStatus.pending,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
        return {
            "id": payment.id,
            "user_id": payment.user_id,
            "package_id": payment.package_id,
            "mollie_payment_id": payment.mollie_payment_id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "status": payment.status.value,
        }


def update_payment_status(payment_id: str, status: str, mollie_payment_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update a payment's status and optionally its Mollie ID."""
    with SessionLocal() as session:
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return None
        payment.status = PaymentStatus(status)
        if mollie_payment_id:
            payment.mollie_payment_id = mollie_payment_id
        payment.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(payment)
        return {
            "id": payment.id,
            "user_id": payment.user_id,
            "status": payment.status.value,
            "mollie_payment_id": payment.mollie_payment_id,
        }


def get_payment_by_id(payment_id: str) -> Optional[Dict[str, Any]]:
    """Look up a payment by its internal ID."""
    with SessionLocal() as session:
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return None
        return {
            "id": payment.id,
            "user_id": payment.user_id,
            "package_id": payment.package_id,
            "mollie_payment_id": payment.mollie_payment_id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "status": payment.status.value,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
        }


def get_payment_by_mollie_id(mollie_id: str) -> Optional[Dict[str, Any]]:
    """Look up a payment by Mollie payment ID."""
    with SessionLocal() as session:
        payment = session.query(Payment).filter(Payment.mollie_payment_id == mollie_id).first()
        if not payment:
            return None
        return {
            "id": payment.id,
            "user_id": payment.user_id,
            "package_id": payment.package_id,
            "mollie_payment_id": payment.mollie_payment_id,
            "amount_cents": payment.amount_cents,
            "currency": payment.currency,
            "status": payment.status.value,
        }


def credit_tokens(user_id: str, amount: int, tx_type: str, description: str, reference_id: Optional[str] = None) -> int:
    """Credit tokens to a user and log the transaction. Returns new balance."""
    with SessionLocal() as session:
        # Update balance
        result = session.execute(
            text(
                "UPDATE users SET token_balance = token_balance + :amount, updated_at = now() "
                "WHERE id = :user_id RETURNING token_balance"
            ),
            {"user_id": user_id, "amount": amount},
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"User {user_id} not found")
        new_balance = row[0]
        # Log transaction
        tx = TokenTransaction(
            id=f"tx_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}",
            user_id=user_id,
            amount=amount,
            type=TokenTxType(tx_type),
            description=description,
            reference_id=reference_id,
            created_at=datetime.utcnow(),
        )
        session.add(tx)
        session.commit()
        return new_balance


def debit_tokens(user_id: str, amount: int, description: str, reference_id: Optional[str] = None) -> Optional[int]:
    """Debit tokens from a user atomically. Returns new balance or None if insufficient."""
    with SessionLocal() as session:
        result = session.execute(
            text(
                "UPDATE users SET token_balance = token_balance - :amount, updated_at = now() "
                "WHERE id = :user_id AND token_balance >= :amount RETURNING token_balance"
            ),
            {"user_id": user_id, "amount": amount},
        )
        row = result.fetchone()
        if not row:
            return None  # insufficient balance or user not found
        new_balance = row[0]
        tx = TokenTransaction(
            id=f"tx_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}",
            user_id=user_id,
            amount=-amount,
            type=TokenTxType.usage,
            description=description,
            reference_id=reference_id,
            created_at=datetime.utcnow(),
        )
        session.add(tx)
        session.commit()
        return new_balance


def list_token_transactions(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List token transactions for a user, newest first."""
    with SessionLocal() as session:
        txs = (
            session.query(TokenTransaction)
            .filter(TokenTransaction.user_id == user_id)
            .order_by(TokenTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.type.value,
                "description": tx.description,
                "reference_id": tx.reference_id,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in txs
        ]


# ── Integration CRUD ─────────────────────────────────────────────────

def _integration_to_dict(i: Integration) -> Dict[str, Any]:
    return {
        "id": i.id,
        "user_id": i.user_id,
        "tenant_id": i.tenant_id,
        "provider": i.provider.value,
        "store_url": i.store_url,
        "scopes": i.scopes,
        "status": i.status.value,
        "provider_metadata": i.provider_metadata,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


def create_integration(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update an integration (upsert by user+provider+store)."""
    with SessionLocal() as session:
        existing = session.query(Integration).filter(
            Integration.user_id == data["user_id"],
            Integration.provider == IntegrationProvider(data["provider"]),
            Integration.store_url == data["store_url"],
        ).first()
        if existing:
            existing.access_token_encrypted = data["access_token_encrypted"]
            existing.scopes = data.get("scopes")
            existing.status = IntegrationStatus.active
            existing.provider_metadata = data.get("provider_metadata")
            existing.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(existing)
            return _integration_to_dict(existing)

        integ = Integration(
            id=data["id"],
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            provider=IntegrationProvider(data["provider"]),
            store_url=data["store_url"],
            access_token_encrypted=data["access_token_encrypted"],
            scopes=data.get("scopes"),
            status=IntegrationStatus.active,
            provider_metadata=data.get("provider_metadata"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(integ)
        session.commit()
        session.refresh(integ)
        return _integration_to_dict(integ)


def get_integration(integration_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get an integration by ID, scoped to user."""
    with SessionLocal() as session:
        i = session.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id,
        ).first()
        return _integration_to_dict(i) if i else None


def get_integration_by_store(user_id: str, provider: str, store_url: str) -> Optional[Dict[str, Any]]:
    """Get integration by user + provider + store URL."""
    with SessionLocal() as session:
        i = session.query(Integration).filter(
            Integration.user_id == user_id,
            Integration.provider == IntegrationProvider(provider),
            Integration.store_url == store_url,
        ).first()
        return _integration_to_dict(i) if i else None


def list_integrations(user_id: str, provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """List integrations for a user, optionally filtered by provider."""
    with SessionLocal() as session:
        q = session.query(Integration).filter(Integration.user_id == user_id)
        if provider:
            q = q.filter(Integration.provider == IntegrationProvider(provider))
        q = q.order_by(Integration.created_at.desc())
        return [_integration_to_dict(i) for i in q.all()]


def update_integration_status(integration_id: str, user_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Update integration status (active/disconnected/expired)."""
    with SessionLocal() as session:
        i = session.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id,
        ).first()
        if not i:
            return None
        i.status = IntegrationStatus(status)
        i.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(i)
        return _integration_to_dict(i)


def delete_integration(integration_id: str, user_id: str) -> bool:
    """Delete an integration. Returns True if deleted."""
    with SessionLocal() as session:
        i = session.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id,
        ).first()
        if not i:
            return False
        session.delete(i)
        session.commit()
        return True


def get_integration_with_token(integration_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get integration including encrypted token (for internal use only)."""
    with SessionLocal() as session:
        i = session.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id,
        ).first()
        if not i:
            return None
        d = _integration_to_dict(i)
        d["access_token_encrypted"] = i.access_token_encrypted
        return d


def get_integration_cost(provider: str, action: str) -> int:
    """Get token cost for a provider action. Returns 0 if not found."""
    with SessionLocal() as session:
        cost = session.query(IntegrationCost).filter(
            IntegrationCost.provider == IntegrationProvider(provider),
            IntegrationCost.action == action,
            IntegrationCost.active == True,
        ).first()
        return cost.token_cost if cost else 0


# ── Admin Settings CRUD ──────────────────────────────────────────────

def _admin_setting_to_dict(s: AdminSetting, unmask: bool = False) -> Dict[str, Any]:
    value = s.value
    if s.is_secret and not unmask and value:
        value = value[:4] + "****" if len(value) > 4 else "****"
    return {
        "key": s.key,
        "value": value,
        "category": s.category,
        "is_secret": s.is_secret,
        "description": s.description,
        "updated_by": s.updated_by,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def list_admin_settings(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all admin settings, masking secret values."""
    with SessionLocal() as session:
        q = session.query(AdminSetting)
        if category:
            q = q.filter(AdminSetting.category == category)
        q = q.order_by(AdminSetting.category, AdminSetting.key)
        return [_admin_setting_to_dict(s) for s in q.all()]


def get_admin_setting(key: str, unmask: bool = False) -> Optional[Dict[str, Any]]:
    """Get a single admin setting."""
    with SessionLocal() as session:
        s = session.get(AdminSetting, key)
        return _admin_setting_to_dict(s, unmask=unmask) if s else None


def get_admin_setting_value(key: str) -> Optional[str]:
    """Get raw unmasked value of an admin setting. For internal use."""
    with SessionLocal() as session:
        s = session.get(AdminSetting, key)
        return s.value if s and s.value else None


def upsert_admin_setting(key: str, value: str, user_id: str, category: Optional[str] = None,
                          is_secret: Optional[bool] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """Create or update an admin setting."""
    with SessionLocal() as session:
        s = session.get(AdminSetting, key)
        if s:
            s.value = value
            s.updated_by = user_id
            if category is not None:
                s.category = category
            if is_secret is not None:
                s.is_secret = is_secret
            if description is not None:
                s.description = description
            s.updated_at = datetime.utcnow()
        else:
            s = AdminSetting(
                key=key,
                value=value,
                category=category or 'general',
                is_secret=is_secret if is_secret is not None else False,
                description=description,
                updated_by=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(s)
        session.commit()
        session.refresh(s)
        return _admin_setting_to_dict(s)


def delete_admin_setting(key: str) -> bool:
    """Delete an admin setting. Returns True if deleted."""
    with SessionLocal() as session:
        s = session.get(AdminSetting, key)
        if not s:
            return False
        session.delete(s)
        session.commit()
        return True


# ── Admin User Management ────────────────────────────────────────────

def list_users(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """List all users (admin only)."""
    with SessionLocal() as session:
        users = (
            session.query(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_user_to_dict(u) for u in users]


def set_user_admin(user_id: str, is_admin: bool) -> Optional[Dict[str, Any]]:
    """Set admin flag on a user."""
    with SessionLocal() as session:
        u = session.get(User, user_id)
        if not u:
            return None
        u.is_admin = is_admin
        u.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(u)
        return _user_to_dict(u)


def set_user_token_balance(user_id: str, balance: int) -> Optional[Dict[str, Any]]:
    """Set absolute token balance for a user (admin only)."""
    with SessionLocal() as session:
        u = session.get(User, user_id)
        if not u:
            return None
        u.token_balance = balance
        u.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(u)
        return _user_to_dict(u)


# ── Admin Panel Queries ──────────────────────────────────────────────

def platform_stats() -> Dict[str, Any]:
    """Aggregate platform statistics for the admin dashboard."""
    with SessionLocal() as session:
        total_users = session.query(func.count(User.id)).scalar() or 0
        total_jobs = session.query(func.count(Job.id)).scalar() or 0
        total_tokens_in_circulation = session.query(func.coalesce(func.sum(User.token_balance), 0)).scalar()
        total_tokens_spent = session.query(
            func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)
        ).filter(TokenTransaction.amount < 0).scalar()
        total_revenue_cents = session.query(
            func.coalesce(func.sum(Payment.amount_cents), 0)
        ).filter(Payment.status == PaymentStatus.paid).scalar()

        # Jobs grouped by status
        status_rows = session.query(
            Job.status, func.count(Job.id)
        ).group_by(Job.status).all()
        jobs_by_status = {row[0].value: row[1] for row in status_rows}

        return {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "total_tokens_in_circulation": total_tokens_in_circulation,
            "total_tokens_spent": total_tokens_spent,
            "total_revenue_cents": total_revenue_cents,
            "jobs_by_status": jobs_by_status,
        }


def list_all_jobs(limit: int = 20, offset: int = 0, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all jobs across tenants with item counts (admin only)."""
    with SessionLocal() as session:
        q = session.query(Job)
        if status_filter:
            q = q.filter(Job.status == JobStatus(status_filter))
        q = q.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        results = []
        for job in q.all():
            item_count = session.query(func.count(JobItem.id)).filter(JobItem.job_id == job.id).scalar() or 0
            results.append({
                "id": job.id,
                "job_id": job.id,
                "tenant_id": job.tenant_id,
                "brand_profile_id": job.brand_profile_id,
                "correlation_id": job.correlation_id,
                "status": job.status.value,
                "processing_options": job.processing_options,
                "callback_url": job.callback_url,
                "export_blob_path": job.export_blob_path,
                "item_count": item_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            })
        return results


def list_all_integrations(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """List all integrations across users (admin only)."""
    with SessionLocal() as session:
        integrations = (
            session.query(Integration)
            .order_by(Integration.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_integration_to_dict(i) for i in integrations]


def list_all_token_packages() -> List[Dict[str, Any]]:
    """List all token packages including inactive ones."""
    with SessionLocal() as session:
        packages = session.query(TokenPackage).order_by(TokenPackage.price_cents.asc()).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "tokens": p.tokens,
                "price_cents": p.price_cents,
                "currency": p.currency,
                "active": p.active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in packages
        ]


def update_token_package(package_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a token package. Returns updated dict or None if not found."""
    with SessionLocal() as session:
        p = session.get(TokenPackage, package_id)
        if not p:
            return None
        for field in ("name", "tokens", "price_cents", "currency", "active"):
            if field in updates:
                setattr(p, field, updates[field])
        session.commit()
        session.refresh(p)
        return {
            "id": p.id,
            "name": p.name,
            "tokens": p.tokens,
            "price_cents": p.price_cents,
            "currency": p.currency,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }


def create_token_package(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new token package."""
    with SessionLocal() as session:
        p = TokenPackage(
            id=data["id"],
            name=data["name"],
            tokens=data["tokens"],
            price_cents=data["price_cents"],
            currency=data.get("currency", "EUR"),
            active=data.get("active", True),
            created_at=datetime.utcnow(),
        )
        session.add(p)
        session.commit()
        session.refresh(p)
        return {
            "id": p.id,
            "name": p.name,
            "tokens": p.tokens,
            "price_cents": p.price_cents,
            "currency": p.currency,
            "active": p.active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }


def delete_token_package(package_id: str) -> bool:
    """Delete a token package. Returns True if deleted."""
    with SessionLocal() as session:
        p = session.get(TokenPackage, package_id)
        if not p:
            return False
        session.delete(p)
        session.commit()
        return True


def list_all_transactions(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List all token transactions across users, newest first (admin only)."""
    with SessionLocal() as session:
        txs = (
            session.query(TokenTransaction)
            .order_by(TokenTransaction.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": tx.id,
                "user_id": tx.user_id,
                "amount": tx.amount,
                "type": tx.type.value,
                "description": tx.description,
                "reference_id": tx.reference_id,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in txs
        ]


def list_all_payments(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List all payments across users, newest first (admin only)."""
    with SessionLocal() as session:
        payments = (
            session.query(Payment)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "id": pay.id,
                "user_id": pay.user_id,
                "package_id": pay.package_id,
                "mollie_payment_id": pay.mollie_payment_id,
                "amount_cents": pay.amount_cents,
                "currency": pay.currency,
                "status": pay.status.value,
                "created_at": pay.created_at.isoformat() if pay.created_at else None,
            }
            for pay in payments
        ]


# ── GDPR / AVG Data Subject Rights ─────────────────────────────────

def export_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Export all personal data for a user (GDPR Art. 15 / AVG)."""
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            return None

        tenant_id = user.tenant_id

        # User profile
        profile = _user_to_dict(user)

        # Jobs and items
        jobs = session.query(Job).filter(Job.tenant_id == tenant_id).all()
        jobs_data = []
        for job in jobs:
            items = session.query(JobItem).filter(JobItem.job_id == job.id).all()
            jobs_data.append({
                "id": job.id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "items": [
                    {
                        "id": item.id,
                        "filename": item.filename,
                        "status": item.status.value,
                        "raw_blob_path": item.raw_blob_path,
                        "output_blob_path": item.output_blob_path,
                    }
                    for item in items
                ],
            })

        # Transactions
        txs = session.query(TokenTransaction).filter(
            TokenTransaction.user_id == user_id
        ).order_by(TokenTransaction.created_at.desc()).all()
        transactions = [
            {
                "id": tx.id,
                "amount": tx.amount,
                "type": tx.type.value,
                "description": tx.description,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in txs
        ]

        # Payments
        pays = session.query(Payment).filter(Payment.user_id == user_id).all()
        payments = [
            {
                "id": pay.id,
                "amount_cents": pay.amount_cents,
                "currency": pay.currency,
                "status": pay.status.value,
                "created_at": pay.created_at.isoformat() if pay.created_at else None,
            }
            for pay in pays
        ]

        # Brand profiles
        bps = session.query(BrandProfile).filter(BrandProfile.tenant_id == tenant_id).all()
        brand_profiles = [_brand_profile_to_dict(bp) for bp in bps]

        # Integrations (without tokens)
        integs = session.query(Integration).filter(Integration.user_id == user_id).all()
        integrations = [
            {
                "id": i.id,
                "provider": i.provider.value,
                "store_url": i.store_url,
                "status": i.status.value,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in integs
        ]

        return {
            "user": profile,
            "jobs": jobs_data,
            "transactions": transactions,
            "payments": payments,
            "brand_profiles": brand_profiles,
            "integrations": integrations,
            "exported_at": datetime.utcnow().isoformat(),
        }


def delete_user_data(user_id: str) -> Dict[str, Any]:
    """Delete all personal data for a user (GDPR Art. 17 / AVG).
    Returns summary of what was deleted. Blob storage cleanup is separate."""
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            return {"deleted": False, "reason": "User not found"}

        tenant_id = user.tenant_id
        summary = {"user_id": user_id, "deleted": True}

        # Collect blob paths for storage cleanup
        blob_paths = []
        jobs = session.query(Job).filter(Job.tenant_id == tenant_id).all()
        for job in jobs:
            items = session.query(JobItem).filter(JobItem.job_id == job.id).all()
            for item in items:
                if item.raw_blob_path:
                    blob_paths.append(("raw", item.raw_blob_path))
                if item.output_blob_path:
                    blob_paths.append(("outputs", item.output_blob_path))
            if job.export_blob_path:
                blob_paths.append(("exports", job.export_blob_path))

        # Delete in dependency order
        # 1. Job items
        item_count = session.query(JobItem).filter(JobItem.tenant_id == tenant_id).delete()
        summary["job_items_deleted"] = item_count

        # 2. Jobs
        job_count = session.query(Job).filter(Job.tenant_id == tenant_id).delete()
        summary["jobs_deleted"] = job_count

        # 3. Token transactions
        tx_count = session.query(TokenTransaction).filter(
            TokenTransaction.user_id == user_id
        ).delete()
        summary["transactions_deleted"] = tx_count

        # 4. Payments
        pay_count = session.query(Payment).filter(Payment.user_id == user_id).delete()
        summary["payments_deleted"] = pay_count

        # 5. Brand profiles + scene templates (cascade via tenant)
        st_count = session.query(SceneTemplate).filter(
            SceneTemplate.tenant_id == tenant_id
        ).delete()
        summary["scene_templates_deleted"] = st_count

        bp_count = session.query(BrandProfile).filter(
            BrandProfile.tenant_id == tenant_id
        ).delete()
        summary["brand_profiles_deleted"] = bp_count

        # 6. Integrations
        integ_count = session.query(Integration).filter(
            Integration.user_id == user_id
        ).delete()
        summary["integrations_deleted"] = integ_count

        # 7. Anonymize admin_settings updated_by references
        session.query(AdminSetting).filter(
            AdminSetting.updated_by == user_id
        ).update({"updated_by": None})

        # 8. Delete user
        session.delete(user)
        session.commit()

        summary["blob_paths"] = blob_paths
        return summary


def delete_integrations_by_store(provider: str, store_url: str) -> int:
    """Delete all integrations for a given store (Shopify GDPR shop/redact)."""
    with SessionLocal() as session:
        count = session.query(Integration).filter(
            Integration.store_url == store_url,
            Integration.provider == provider,
        ).delete()
        session.commit()
        return count


def get_jobs_older_than(days: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get jobs older than N days for retention cleanup."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    with SessionLocal() as session:
        jobs = session.query(Job).filter(
            Job.created_at < cutoff,
        ).limit(limit).all()
        return [
            {
                "id": job.id,
                "tenant_id": job.tenant_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ]


def delete_job_cascade(job_id: str) -> Dict[str, Any]:
    """Delete a job and all its items. Returns blob paths for storage cleanup."""
    with SessionLocal() as session:
        blob_paths = []
        items = session.query(JobItem).filter(JobItem.job_id == job_id).all()
        for item in items:
            if item.raw_blob_path:
                blob_paths.append(("raw", item.raw_blob_path))
            if item.output_blob_path:
                blob_paths.append(("outputs", item.output_blob_path))

        job = session.query(Job).filter(Job.id == job_id).first()
        if job and job.export_blob_path:
            blob_paths.append(("exports", job.export_blob_path))

        item_count = session.query(JobItem).filter(JobItem.job_id == job_id).delete()
        job_deleted = session.query(Job).filter(Job.id == job_id).delete()
        session.commit()

        return {
            "job_id": job_id,
            "items_deleted": item_count,
            "job_deleted": bool(job_deleted),
            "blob_paths": blob_paths,
        }
