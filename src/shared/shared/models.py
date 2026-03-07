from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .db import Base


class ItemStatus(str, enum.Enum):
    created = 'created'
    uploaded = 'uploaded'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'


class JobStatus(str, enum.Enum):
    created = 'created'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    partial = 'partial'


class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    entra_subject_id = Column(String, unique=True, nullable=True)
    email = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    token_balance = Column(Integer, nullable=False, default=0)
    is_admin = Column(Boolean, nullable=False, default=False)
    mollie_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.id} email={self.email}>'


class AdminSetting(Base):
    __tablename__ = 'admin_settings'

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False, default='')
    category = Column(String, nullable=False, default='general')
    is_secret = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=True)
    updated_by = Column(String, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class TokenTxType(str, enum.Enum):
    purchase = 'purchase'
    usage = 'usage'
    refund = 'refund'
    bonus = 'bonus'


class PaymentStatus(str, enum.Enum):
    pending = 'pending'
    paid = 'paid'
    failed = 'failed'
    expired = 'expired'
    refunded = 'refunded'


class TokenTransaction(Base):
    __tablename__ = 'token_transactions'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(SQLEnum(TokenTxType), nullable=False)
    description = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TokenPackage(Base):
    __tablename__ = 'token_packages'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tokens = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default='EUR')
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    package_id = Column(String, ForeignKey('token_packages.id'), nullable=False)
    mollie_payment_id = Column(String, unique=True, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default='EUR')
    status = Column(SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrandProfile(Base):
    __tablename__ = 'brand_profiles'

    id = Column(String, primary_key=True, name='id')
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    default_scene_prompt = Column(String, nullable=True)
    style_keywords = Column(ARRAY(String), nullable=True)
    color_palette = Column(ARRAY(String), nullable=True)
    mood = Column(String, nullable=True)
    product_category = Column(String(100), nullable=True)
    default_scene_count = Column(Integer, nullable=True, default=1)
    default_scene_types = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BrandProfile {self.id} name={self.name}>'


class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tokens_per_month = Column(Integer, nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, default='EUR')
    interval = Column(String, nullable=False, default='1 month')
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserSubscription(Base):
    __tablename__ = 'user_subscriptions'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    plan_id = Column(String, ForeignKey('subscription_plans.id'), nullable=False)
    mollie_customer_id = Column(String, nullable=True)
    mollie_subscription_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrandReferenceImage(Base):
    __tablename__ = 'brand_reference_images'

    id = Column(String, primary_key=True)
    brand_profile_id = Column(String, ForeignKey('brand_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(String, nullable=False)
    blob_path = Column(String, nullable=False)
    extracted_style = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SceneTemplate(Base):
    __tablename__ = 'scene_templates'

    id = Column(String, primary_key=True, name='id')
    tenant_id = Column(String, nullable=False, index=True)
    brand_profile_id = Column(String, ForeignKey('brand_profiles.id', ondelete='SET NULL'), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    prompt = Column(String, nullable=False)
    preview_blob_path = Column(String, nullable=True)
    scene_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SceneTemplate {self.id} name={self.name}>'


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(String, primary_key=True, name='id')
    tenant_id = Column(String, nullable=False, index=True)
    brand_profile_id = Column(String, nullable=False)
    correlation_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.created, index=True)
    processing_options = Column(JSON, nullable=True)
    callback_url = Column(String, nullable=True)
    export_blob_path = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship('JobItem', back_populates='job', lazy='select')
    
    @property
    def job_id(self):
        return self.id

    def __repr__(self):
        return f'<Job {self.id} status={self.status}>'


class IntegrationProvider(str, enum.Enum):
    shopify = 'shopify'
    woocommerce = 'woocommerce'
    etsy = 'etsy'


class IntegrationStatus(str, enum.Enum):
    active = 'active'
    disconnected = 'disconnected'
    expired = 'expired'


class Integration(Base):
    __tablename__ = 'integrations'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    provider = Column(SQLEnum(IntegrationProvider), nullable=False)
    store_url = Column(String, nullable=False)
    access_token_encrypted = Column(String, nullable=False)
    scopes = Column(String, nullable=True)
    status = Column(SQLEnum(IntegrationStatus), nullable=False, default=IntegrationStatus.active)
    provider_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Integration {self.id} provider={self.provider} store={self.store_url}>'


class IntegrationCost(Base):
    __tablename__ = 'integration_costs'

    id = Column(String, primary_key=True)
    provider = Column(SQLEnum(IntegrationProvider), nullable=False)
    action = Column(String, nullable=False)
    token_cost = Column(Integer, nullable=False, default=1)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class JobItem(Base):
    __tablename__ = 'job_items'

    id = Column(String, primary_key=True, name='id')
    job_id = Column(String, ForeignKey('jobs.id'), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    status = Column(SQLEnum(ItemStatus), nullable=False, default=ItemStatus.created, index=True)
    raw_blob_path = Column(String, nullable=True)
    output_blob_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    scene_prompt = Column(String, nullable=True)
    scene_index = Column(Integer, nullable=True)
    scene_type = Column(String(50), nullable=True)
    saved_background_path = Column(String, nullable=True)
    seo_alt_text = Column(String(200), nullable=True)
    seo_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship('Job', back_populates='items')
    
    @property
    def item_id(self):
        return self.id

    def __repr__(self):
        return f'<JobItem {self.id} status={self.status}>'
