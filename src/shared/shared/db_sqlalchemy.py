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
    AdminSetting, SubscriptionPlan, UserSubscription,
    CatalogJob, CatalogJobStatus, CatalogJobProduct, CatalogProductStatus,
    ABTest, ABTestStatus, ABTestMetric, ABTestVariantLog,
    ImportedImage,
)
from datetime import datetime, timedelta
import logging
import secrets

log = logging.getLogger("opal")


def create_job_record(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a job record in the database."""
    with SessionLocal() as session:
        job = Job(
            id=job_data["id"],
            tenant_id=job_data["tenant_id"],
            user_id=job_data.get("user_id"),
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
                angle_type=item_data.get("angle_type"),
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
            "user_id": job.user_id,
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
            "step_timings": item.step_timings,
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
                "angle_type": item.angle_type,
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


# ── Subscription CRUD ──────────────────────────────────────────────

def list_subscription_plans(active_only: bool = True) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = session.query(SubscriptionPlan)
        if active_only:
            q = q.filter(SubscriptionPlan.active == True)
        plans = q.order_by(SubscriptionPlan.price_cents).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "tokens_per_month": p.tokens_per_month,
                "price_cents": p.price_cents,
                "currency": p.currency,
                "interval": p.interval,
                "active": p.active,
            }
            for p in plans
        ]


def get_subscription_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        p = session.get(SubscriptionPlan, plan_id)
        if not p:
            return None
        return {
            "id": p.id,
            "name": p.name,
            "tokens_per_month": p.tokens_per_month,
            "price_cents": p.price_cents,
            "currency": p.currency,
            "interval": p.interval,
            "active": p.active,
        }


def create_user_subscription(data: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as session:
        sub = UserSubscription(
            id=data["id"],
            user_id=data["user_id"],
            plan_id=data["plan_id"],
            mollie_customer_id=data.get("mollie_customer_id"),
            mollie_subscription_id=data.get("mollie_subscription_id"),
            status=data.get("status", "pending"),
            current_period_start=data.get("current_period_start"),
            current_period_end=data.get("current_period_end"),
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)
        return _subscription_to_dict(sub)


def get_user_subscription(user_id: str) -> Optional[Dict[str, Any]]:
    """Get active subscription for a user (only one active at a time)."""
    with SessionLocal() as session:
        sub = session.query(UserSubscription).filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status.in_(["active", "pending"]),
        ).order_by(UserSubscription.created_at.desc()).first()
        return _subscription_to_dict(sub) if sub else None


def get_subscription_by_mollie_id(mollie_subscription_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        sub = session.query(UserSubscription).filter(
            UserSubscription.mollie_subscription_id == mollie_subscription_id,
        ).first()
        return _subscription_to_dict(sub) if sub else None


def update_subscription(sub_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        sub = session.get(UserSubscription, sub_id)
        if not sub:
            return None
        for key, value in updates.items():
            if hasattr(sub, key):
                setattr(sub, key, value)
        sub.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(sub)
        return _subscription_to_dict(sub)


def set_user_mollie_customer_id(user_id: str, customer_id: str) -> None:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            user.mollie_customer_id = customer_id
            session.commit()


def get_user_mollie_customer_id(user_id: str) -> Optional[str]:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        return user.mollie_customer_id if user else None


def _subscription_to_dict(sub: UserSubscription) -> Dict[str, Any]:
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "plan_id": sub.plan_id,
        "mollie_customer_id": sub.mollie_customer_id,
        "mollie_subscription_id": sub.mollie_subscription_id,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
        "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
    }


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
                "user_id": job.user_id,
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


def get_pipeline_performance(limit: int = 100, days: int = 30) -> Dict[str, Any]:
    """Get pipeline performance data: recent items with timings + aggregated averages."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    with SessionLocal() as session:
        # Recent completed items with step_timings
        items_q = (
            session.query(JobItem, Job.tenant_id)
            .join(Job, JobItem.job_id == Job.id)
            .filter(
                JobItem.status == ItemStatus.completed,
                JobItem.step_timings.isnot(None),
                JobItem.updated_at >= cutoff,
            )
            .order_by(JobItem.updated_at.desc())
            .limit(limit)
        )
        recent_items = []
        for item, tenant_id in items_q.all():
            recent_items.append({
                "item_id": item.id,
                "job_id": item.job_id,
                "tenant_id": tenant_id,
                "filename": item.filename,
                "scene_type": item.scene_type,
                "angle_type": item.angle_type,
                "step_timings": item.step_timings,
                "completed_at": item.updated_at.isoformat() if item.updated_at else None,
            })

        # Aggregate averages across all steps
        all_items = (
            session.query(JobItem.step_timings)
            .filter(
                JobItem.status == ItemStatus.completed,
                JobItem.step_timings.isnot(None),
                JobItem.updated_at >= cutoff,
            )
            .all()
        )
        step_sums: Dict[str, float] = {}
        step_counts: Dict[str, int] = {}
        for (timings,) in all_items:
            if not isinstance(timings, dict):
                continue
            for step, secs in timings.items():
                if isinstance(secs, (int, float)):
                    step_sums[step] = step_sums.get(step, 0.0) + secs
                    step_counts[step] = step_counts.get(step, 0) + 1

        averages = {
            step: round(step_sums[step] / step_counts[step], 2)
            for step in step_sums
        }

        # Daily aggregates for trend chart (avg total per day)
        daily: Dict[str, list] = {}
        for (timings,) in all_items:
            if not isinstance(timings, dict):
                continue
        # Re-query with dates for daily breakdown
        daily_items = (
            session.query(JobItem.step_timings, JobItem.updated_at)
            .filter(
                JobItem.status == ItemStatus.completed,
                JobItem.step_timings.isnot(None),
                JobItem.updated_at >= cutoff,
            )
            .all()
        )
        daily_data: Dict[str, Dict[str, list]] = {}
        for timings, updated_at in daily_items:
            if not isinstance(timings, dict) or not updated_at:
                continue
            day = updated_at.strftime("%Y-%m-%d")
            if day not in daily_data:
                daily_data[day] = {}
            for step, secs in timings.items():
                if isinstance(secs, (int, float)):
                    if step not in daily_data[day]:
                        daily_data[day][step] = []
                    daily_data[day][step].append(secs)

        daily_averages = []
        for day in sorted(daily_data.keys()):
            entry: Dict[str, Any] = {"date": day}
            for step, values in daily_data[day].items():
                entry[step] = round(sum(values) / len(values), 2)
            entry["count"] = max(len(v) for v in daily_data[day].values()) if daily_data[day] else 0
            daily_averages.append(entry)

        return {
            "recent_items": recent_items,
            "averages": averages,
            "total_items": len(all_items),
            "daily_averages": daily_averages,
        }


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


# ── Catalog Jobs ──────────────────────────────────────────────────────

def _catalog_job_to_dict(cj: CatalogJob) -> Dict[str, Any]:
    return {
        "id": cj.id,
        "user_id": cj.user_id,
        "integration_id": cj.integration_id,
        "status": cj.status.value if isinstance(cj.status, CatalogJobStatus) else cj.status,
        "total_products": cj.total_products,
        "processed_count": cj.processed_count,
        "failed_count": cj.failed_count,
        "skipped_count": cj.skipped_count,
        "total_images": cj.total_images,
        "tokens_estimated": cj.tokens_estimated,
        "tokens_spent": cj.tokens_spent,
        "settings": cj.settings or {},
        "error_message": cj.error_message,
        "created_at": cj.created_at.isoformat() if cj.created_at else None,
        "updated_at": cj.updated_at.isoformat() if cj.updated_at else None,
    }


def _catalog_product_to_dict(cp: CatalogJobProduct) -> Dict[str, Any]:
    return {
        "id": cp.id,
        "catalog_job_id": cp.catalog_job_id,
        "product_id": cp.product_id,
        "product_title": cp.product_title,
        "job_id": cp.job_id,
        "image_count": cp.image_count,
        "status": cp.status.value if isinstance(cp.status, CatalogProductStatus) else cp.status,
        "error_message": cp.error_message,
        "created_at": cp.created_at.isoformat() if cp.created_at else None,
        "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
    }


def create_catalog_job(data: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as session:
        cj = CatalogJob(**data)
        session.add(cj)
        session.commit()
        session.refresh(cj)
        return _catalog_job_to_dict(cj)


def get_catalog_job(catalog_job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        cj = session.query(CatalogJob).filter(
            CatalogJob.id == catalog_job_id,
            CatalogJob.user_id == user_id,
        ).first()
        return _catalog_job_to_dict(cj) if cj else None


def list_catalog_jobs(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        cjs = (
            session.query(CatalogJob)
            .filter(CatalogJob.user_id == user_id)
            .order_by(CatalogJob.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_catalog_job_to_dict(cj) for cj in cjs]


def update_catalog_job(catalog_job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        cj = session.query(CatalogJob).filter(CatalogJob.id == catalog_job_id).first()
        if not cj:
            return None
        for k, v in updates.items():
            setattr(cj, k, v)
        cj.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(cj)
        return _catalog_job_to_dict(cj)


def increment_catalog_job_counts(catalog_job_id: str, processed: int = 0, failed: int = 0, skipped: int = 0, tokens: int = 0) -> None:
    with SessionLocal() as session:
        session.execute(
            text(
                "UPDATE catalog_jobs SET "
                "processed_count = processed_count + :processed, "
                "failed_count = failed_count + :failed, "
                "skipped_count = skipped_count + :skipped, "
                "tokens_spent = tokens_spent + :tokens, "
                "updated_at = now() "
                "WHERE id = :id"
            ),
            {"id": catalog_job_id, "processed": processed, "failed": failed, "skipped": skipped, "tokens": tokens},
        )
        session.commit()


def create_catalog_job_products(items: List[Dict[str, Any]]) -> None:
    with SessionLocal() as session:
        for item in items:
            session.add(CatalogJobProduct(**item))
        session.commit()


def get_catalog_job_products(catalog_job_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        products = (
            session.query(CatalogJobProduct)
            .filter(CatalogJobProduct.catalog_job_id == catalog_job_id)
            .order_by(CatalogJobProduct.created_at.asc())
            .all()
        )
        return [_catalog_product_to_dict(p) for p in products]


def update_catalog_job_product(product_id: str, updates: Dict[str, Any]) -> None:
    with SessionLocal() as session:
        p = session.query(CatalogJobProduct).filter(CatalogJobProduct.id == product_id).first()
        if p:
            for k, v in updates.items():
                setattr(p, k, v)
            p.updated_at = datetime.utcnow()
            session.commit()


def get_pending_catalog_products(catalog_job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get next batch of pending products to process."""
    with SessionLocal() as session:
        products = (
            session.query(CatalogJobProduct)
            .filter(
                CatalogJobProduct.catalog_job_id == catalog_job_id,
                CatalogJobProduct.status == CatalogProductStatus.pending,
            )
            .order_by(CatalogJobProduct.created_at.asc())
            .limit(limit)
            .all()
        )
        return [_catalog_product_to_dict(p) for p in products]


# ── Imported Images ────────────────────────────────────────────────────

def _imported_image_to_dict(img: ImportedImage) -> Dict[str, Any]:
    return {
        "id": img.id,
        "user_id": img.user_id,
        "tenant_id": img.tenant_id,
        "integration_id": img.integration_id,
        "provider_product_id": img.provider_product_id,
        "provider_image_id": img.provider_image_id,
        "blob_path": img.blob_path,
        "filename": img.filename,
        "original_url": img.original_url,
        "width": img.width,
        "height": img.height,
        "file_size": img.file_size,
        "content_type": img.content_type,
        "created_at": img.created_at.isoformat() if img.created_at else None,
    }


def create_imported_image(data: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as session:
        img = ImportedImage(**data)
        session.add(img)
        session.commit()
        session.refresh(img)
        return _imported_image_to_dict(img)


def get_imported_images_for_product(
    integration_id: str, provider_product_id: str
) -> List[Dict[str, Any]]:
    """Get all imported images for a specific product."""
    with SessionLocal() as session:
        images = (
            session.query(ImportedImage)
            .filter(
                ImportedImage.integration_id == integration_id,
                ImportedImage.provider_product_id == provider_product_id,
            )
            .order_by(ImportedImage.created_at.asc())
            .all()
        )
        return [_imported_image_to_dict(img) for img in images]


def get_imported_image(
    integration_id: str, provider_product_id: str, provider_image_id: str
) -> Optional[Dict[str, Any]]:
    """Get a single imported image by provider IDs."""
    with SessionLocal() as session:
        img = session.query(ImportedImage).filter(
            ImportedImage.integration_id == integration_id,
            ImportedImage.provider_product_id == provider_product_id,
            ImportedImage.provider_image_id == provider_image_id,
        ).first()
        return _imported_image_to_dict(img) if img else None


def get_imported_image_by_id(image_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a single imported image by its ID, scoped to user."""
    with SessionLocal() as session:
        img = session.query(ImportedImage).filter(
            ImportedImage.id == image_id,
            ImportedImage.user_id == user_id,
        ).first()
        return _imported_image_to_dict(img) if img else None


def list_imported_products(user_id: str, integration_id: str) -> List[Dict[str, Any]]:
    """List distinct products that have imported images."""
    with SessionLocal() as session:
        from sqlalchemy import func, distinct
        rows = (
            session.query(
                ImportedImage.provider_product_id,
                func.count(ImportedImage.id).label("image_count"),
                func.min(ImportedImage.created_at).label("first_imported"),
            )
            .filter(
                ImportedImage.user_id == user_id,
                ImportedImage.integration_id == integration_id,
            )
            .group_by(ImportedImage.provider_product_id)
            .all()
        )
        return [
            {
                "provider_product_id": row[0],
                "image_count": row[1],
                "first_imported": row[2].isoformat() if row[2] else None,
            }
            for row in rows
        ]


# ── A/B Tests ─────────────────────────────────────────────────────────

def _ab_test_to_dict(t: ABTest) -> Dict[str, Any]:
    return {
        "id": t.id,
        "user_id": t.user_id,
        "integration_id": t.integration_id,
        "product_id": t.product_id,
        "product_title": t.product_title,
        "status": t.status.value if isinstance(t.status, ABTestStatus) else t.status,
        "variant_a_job_item_id": t.variant_a_job_item_id,
        "variant_b_job_item_id": t.variant_b_job_item_id,
        "variant_a_label": t.variant_a_label,
        "variant_b_label": t.variant_b_label,
        "active_variant": t.active_variant,
        "winner": t.winner,
        "original_image_id": t.original_image_id,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "ended_at": t.ended_at.isoformat() if t.ended_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _ab_metric_to_dict(m: ABTestMetric) -> Dict[str, Any]:
    return {
        "id": m.id,
        "ab_test_id": m.ab_test_id,
        "variant": m.variant,
        "date": m.date.isoformat() if m.date else None,
        "views": m.views,
        "clicks": m.clicks,
        "add_to_carts": m.add_to_carts,
        "conversions": m.conversions,
        "revenue_cents": m.revenue_cents,
    }


def create_ab_test(data: Dict[str, Any]) -> Dict[str, Any]:
    with SessionLocal() as session:
        t = ABTest(**data)
        session.add(t)
        session.commit()
        session.refresh(t)
        return _ab_test_to_dict(t)


def get_ab_test(test_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        t = session.query(ABTest).filter(
            ABTest.id == test_id,
            ABTest.user_id == user_id,
        ).first()
        return _ab_test_to_dict(t) if t else None


def list_ab_tests(user_id: str, integration_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = session.query(ABTest).filter(ABTest.user_id == user_id)
        if integration_id:
            q = q.filter(ABTest.integration_id == integration_id)
        if status:
            q = q.filter(ABTest.status == status)
        tests = q.order_by(ABTest.created_at.desc()).limit(limit).all()
        return [_ab_test_to_dict(t) for t in tests]


def update_ab_test(test_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        t = session.query(ABTest).filter(ABTest.id == test_id).first()
        if not t:
            return None
        for k, v in updates.items():
            setattr(t, k, v)
        t.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(t)
        return _ab_test_to_dict(t)


def get_ab_test_metrics(test_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        metrics = (
            session.query(ABTestMetric)
            .filter(ABTestMetric.ab_test_id == test_id)
            .order_by(ABTestMetric.date.asc(), ABTestMetric.variant.asc())
            .all()
        )
        return [_ab_metric_to_dict(m) for m in metrics]


def upsert_ab_test_metric(data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a metric row (unique on test_id + variant + date)."""
    with SessionLocal() as session:
        existing = session.query(ABTestMetric).filter(
            ABTestMetric.ab_test_id == data["ab_test_id"],
            ABTestMetric.variant == data["variant"],
            ABTestMetric.date == data["date"],
        ).first()
        if existing:
            for k, v in data.items():
                if k not in ("id", "ab_test_id", "variant", "date"):
                    setattr(existing, k, v)
            existing.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(existing)
            return _ab_metric_to_dict(existing)
        else:
            m = ABTestMetric(**data)
            session.add(m)
            session.commit()
            session.refresh(m)
            return _ab_metric_to_dict(m)


def get_ab_test_aggregated_metrics(test_id: str) -> Dict[str, Dict[str, int]]:
    """Get totals per variant across all dates."""
    with SessionLocal() as session:
        metrics = (
            session.query(ABTestMetric)
            .filter(ABTestMetric.ab_test_id == test_id)
            .all()
        )
        result: Dict[str, Dict[str, int]] = {}
        for m in metrics:
            if m.variant not in result:
                result[m.variant] = {"views": 0, "clicks": 0, "add_to_carts": 0, "conversions": 0, "revenue_cents": 0}
            result[m.variant]["views"] += m.views
            result[m.variant]["clicks"] += m.clicks
            result[m.variant]["add_to_carts"] += m.add_to_carts
            result[m.variant]["conversions"] += m.conversions
            result[m.variant]["revenue_cents"] += m.revenue_cents
        return result


# ── Image Benchmarks ──────────────────────────────────────────────────

def create_image_benchmark(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an image benchmark record."""
    from .models import ImageBenchmark
    with SessionLocal() as session:
        bm = ImageBenchmark(**data)
        session.add(bm)
        session.commit()
        session.refresh(bm)
        return _serialize_benchmark(bm)


def get_image_benchmark(benchmark_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Get a single benchmark by ID, scoped to user."""
    from .models import ImageBenchmark
    with SessionLocal() as session:
        bm = session.query(ImageBenchmark).filter(
            ImageBenchmark.id == benchmark_id,
            ImageBenchmark.user_id == user_id,
        ).first()
        return _serialize_benchmark(bm) if bm else None


def list_image_benchmarks(
    user_id: str,
    integration_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """List benchmarks for a user with optional filters."""
    from .models import ImageBenchmark
    with SessionLocal() as session:
        query = session.query(ImageBenchmark).filter(ImageBenchmark.user_id == user_id)
        if integration_id:
            query = query.filter(ImageBenchmark.integration_id == integration_id)
        if category:
            query = query.filter(ImageBenchmark.category == category)
        benchmarks = query.order_by(ImageBenchmark.created_at.desc()).offset(offset).limit(limit).all()
        return [_serialize_benchmark(b) for b in benchmarks]


def get_category_benchmarks() -> list:
    """Get all category benchmark averages."""
    from .models import CategoryBenchmark
    with SessionLocal() as session:
        cats = session.query(CategoryBenchmark).order_by(CategoryBenchmark.category).all()
        return [_serialize_category_benchmark(c) for c in cats]


def get_category_benchmark(category: str) -> Optional[Dict[str, Any]]:
    """Get benchmark averages for a specific category."""
    from .models import CategoryBenchmark
    with SessionLocal() as session:
        cb = session.query(CategoryBenchmark).filter(CategoryBenchmark.category == category).first()
        return _serialize_category_benchmark(cb) if cb else None


def _serialize_benchmark(bm) -> Dict[str, Any]:
    return {
        "id": bm.id,
        "user_id": bm.user_id,
        "integration_id": bm.integration_id,
        "product_id": bm.product_id,
        "product_title": bm.product_title,
        "image_url": bm.image_url,
        "job_item_id": bm.job_item_id,
        "scores": bm.scores,
        "overall_score": bm.overall_score,
        "suggestions": bm.suggestions,
        "category": bm.category,
        "created_at": bm.created_at.isoformat(),
    }


def _serialize_category_benchmark(cb) -> Dict[str, Any]:
    return {
        "id": cb.id,
        "category": cb.category,
        "avg_scores": cb.avg_scores,
        "sample_size": cb.sample_size,
        "updated_at": cb.updated_at.isoformat(),
    }


# ── Pixel Tracking ───────────────────────────────────────────────────


def generate_pixel_key(integration_id: str) -> str:
    """Generate and store a pixel key for an integration."""
    key = secrets.token_urlsafe(32)
    with SessionLocal() as session:
        session.execute(
            text("UPDATE integrations SET pixel_key = :key WHERE id = :iid"),
            {"key": key, "iid": integration_id},
        )
        session.commit()
    return key


def get_integration_by_pixel_key(pixel_key: str) -> Optional[Dict[str, Any]]:
    """Look up an integration by its pixel key."""
    with SessionLocal() as session:
        row = session.execute(
            text("""
                SELECT id, user_id, provider, store_url, status, pixel_key
                FROM integrations
                WHERE pixel_key = :pk AND status = 'active'
            """),
            {"pk": pixel_key},
        ).mappings().first()
        return dict(row) if row else None


def ensure_pixel_key(integration_id: str) -> str:
    """Get or create pixel key for an integration."""
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT pixel_key FROM integrations WHERE id = :iid"),
            {"iid": integration_id},
        ).mappings().first()
        if row and row["pixel_key"]:
            return row["pixel_key"]
    return generate_pixel_key(integration_id)


def create_variant_log_entry(test_id: str, variant: str, activated_at: Optional[datetime] = None) -> Dict[str, Any]:
    """Record a variant activation (test start or swap)."""
    from .util import new_id
    with SessionLocal() as session:
        entry = ABTestVariantLog(
            id=new_id("vtlog"),
            test_id=test_id,
            variant=variant,
            activated_at=activated_at or datetime.utcnow(),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return {
            "id": entry.id,
            "test_id": entry.test_id,
            "variant": entry.variant,
            "activated_at": entry.activated_at.isoformat() if entry.activated_at else None,
        }


def get_active_variant_at(test_id: str, event_time: datetime) -> Optional[str]:
    """Determine which variant was active for a test at a given timestamp."""
    with SessionLocal() as session:
        row = session.execute(
            text("""
                SELECT variant FROM ab_test_variant_log
                WHERE test_id = :tid AND activated_at <= :ts
                ORDER BY activated_at DESC
                LIMIT 1
            """),
            {"tid": test_id, "ts": event_time},
        ).mappings().first()
        return row["variant"] if row else None


def find_running_test(integration_id: str, product_id: str) -> Optional[Dict[str, Any]]:
    """Find a running A/B test for a specific product+integration."""
    with SessionLocal() as session:
        row = session.execute(
            text("""
                SELECT id, user_id, integration_id, product_id, active_variant,
                       status, tracking_mode
                FROM ab_tests
                WHERE integration_id = :iid
                  AND product_id = :pid
                  AND status = 'running'
                LIMIT 1
            """),
            {"iid": integration_id, "pid": product_id},
        ).mappings().first()
        return dict(row) if row else None


def increment_ab_test_metric(
    test_id: str,
    variant: str,
    date_str: str,
    views: int = 0,
    add_to_carts: int = 0,
    conversions: int = 0,
    revenue_cents: int = 0,
) -> None:
    """Atomically increment metric counters for a variant on a date."""
    from .util import new_id
    with SessionLocal() as session:
        result = session.execute(
            text("""
                UPDATE ab_test_metrics
                SET views = views + :v,
                    add_to_carts = add_to_carts + :atc,
                    conversions = conversions + :c,
                    revenue_cents = revenue_cents + :rc,
                    updated_at = NOW()
                WHERE ab_test_id = :tid AND variant = :var AND date = :d
            """),
            {"tid": test_id, "var": variant, "d": date_str,
             "v": views, "atc": add_to_carts, "c": conversions, "rc": revenue_cents},
        )
        if result.rowcount == 0:
            session.execute(
                text("""
                    INSERT INTO ab_test_metrics (id, ab_test_id, variant, date, views, clicks, add_to_carts, conversions, revenue_cents)
                    VALUES (:id, :tid, :var, :d, :v, 0, :atc, :c, :rc)
                """),
                {"id": new_id("abm"), "tid": test_id, "var": variant, "d": date_str,
                 "v": views, "atc": add_to_carts, "c": conversions, "rc": revenue_cents},
            )
        session.commit()
