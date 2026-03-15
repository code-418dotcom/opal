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
    company_name = Column(String, nullable=True)
    vat_number = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, default=False)
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
    user_id = Column(String, ForeignKey('users.id'), nullable=True, index=True)
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
    pixel_key = Column(String(64), nullable=True)
    monthly_event_limit = Column(Integer, nullable=True, default=1000)
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


class CatalogJobStatus(str, enum.Enum):
    created = 'created'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    canceled = 'canceled'


class CatalogProductStatus(str, enum.Enum):
    pending = 'pending'
    processing = 'processing'
    completed = 'completed'
    failed = 'failed'
    skipped = 'skipped'


class CatalogJob(Base):
    __tablename__ = 'catalog_jobs'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    integration_id = Column(String, ForeignKey('integrations.id', ondelete='CASCADE'), nullable=False)
    status = Column(SQLEnum(CatalogJobStatus), nullable=False, default=CatalogJobStatus.created, index=True)
    total_products = Column(Integer, nullable=False, default=0)
    processed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    skipped_count = Column(Integer, nullable=False, default=0)
    total_images = Column(Integer, nullable=False, default=0)
    tokens_estimated = Column(Integer, nullable=False, default=0)
    tokens_spent = Column(Integer, nullable=False, default=0)
    settings = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = relationship('CatalogJobProduct', back_populates='catalog_job', lazy='select')

    def __repr__(self):
        return f'<CatalogJob {self.id} status={self.status}>'


class CatalogJobProduct(Base):
    __tablename__ = 'catalog_job_products'

    id = Column(String, primary_key=True)
    catalog_job_id = Column(String, ForeignKey('catalog_jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = Column(String, nullable=False)
    product_title = Column(String, nullable=True)
    job_id = Column(String, ForeignKey('jobs.id'), nullable=True)
    image_count = Column(Integer, nullable=False, default=0)
    status = Column(SQLEnum(CatalogProductStatus), nullable=False, default=CatalogProductStatus.pending, index=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    catalog_job = relationship('CatalogJob', back_populates='products')

    def __repr__(self):
        return f'<CatalogJobProduct {self.id} product={self.product_id}>'


class ABTestStatus(str, enum.Enum):
    created = 'created'
    running = 'running'
    concluded = 'concluded'
    canceled = 'canceled'


class ABTest(Base):
    __tablename__ = 'ab_tests'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    integration_id = Column(String, ForeignKey('integrations.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(String, nullable=False)
    product_title = Column(String, nullable=True)
    status = Column(SQLEnum(ABTestStatus), nullable=False, default=ABTestStatus.created, index=True)
    variant_a_job_item_id = Column(String, ForeignKey('job_items.id'), nullable=True)
    variant_b_job_item_id = Column(String, ForeignKey('job_items.id'), nullable=True)
    variant_a_label = Column(String, nullable=False, default='Original')
    variant_b_label = Column(String, nullable=False, default='Variant B')
    active_variant = Column(String, nullable=False, default='a')
    winner = Column(String, nullable=True)
    original_image_id = Column(String, nullable=True)
    variant_a_image_url = Column(String, nullable=True)
    variant_b_image_url = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tracking_mode = Column(String, nullable=False, default='manual')  # 'manual' or 'pixel'
    auto_conclude = Column(Boolean, nullable=False, default=False)

    metrics = relationship('ABTestMetric', back_populates='ab_test', lazy='select')

    def __repr__(self):
        return f'<ABTest {self.id} product={self.product_id} status={self.status}>'


class ABTestMetric(Base):
    __tablename__ = 'ab_test_metrics'

    id = Column(String, primary_key=True)
    ab_test_id = Column(String, ForeignKey('ab_tests.id', ondelete='CASCADE'), nullable=False, index=True)
    variant = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    views = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    add_to_carts = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    revenue_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    ab_test = relationship('ABTest', back_populates='metrics')

    def __repr__(self):
        return f'<ABTestMetric {self.id} test={self.ab_test_id} variant={self.variant}>'


class ABTestVariantLog(Base):
    """Records each variant activation (start or swap) with a timestamp.

    Used to attribute incoming pixel events to the correct variant:
    find the most recent activation before the event timestamp.
    """
    __tablename__ = 'ab_test_variant_log'

    id = Column(String, primary_key=True)
    test_id = Column(String, ForeignKey('ab_tests.id', ondelete='CASCADE'), nullable=False)
    variant = Column(String(1), nullable=False)  # 'a' or 'b'
    activated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ABTestVariantLog test={self.test_id} variant={self.variant} at={self.activated_at}>'


class ImageBenchmark(Base):
    __tablename__ = 'image_benchmarks'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    integration_id = Column(String, ForeignKey('integrations.id', ondelete='SET NULL'), nullable=True, index=True)
    product_id = Column(String, nullable=True)
    product_title = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    job_item_id = Column(String, ForeignKey('job_items.id', ondelete='SET NULL'), nullable=True)
    scores = Column(JSON, nullable=False)
    overall_score = Column(Integer, nullable=False)
    suggestions = Column(JSON, nullable=True)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ImageBenchmark {self.id} score={self.overall_score}>'


class CategoryBenchmark(Base):
    __tablename__ = 'category_benchmarks'

    id = Column(String, primary_key=True)
    category = Column(String(100), nullable=False, unique=True)
    avg_scores = Column(JSON, nullable=False)
    sample_size = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CategoryBenchmark {self.category}>'


class UserPreference(Base):
    __tablename__ = 'user_preferences'

    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    preferences = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserPreference user={self.user_id}>'


class ImportedImage(Base):
    __tablename__ = 'imported_images'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    tenant_id = Column(String, nullable=False)
    integration_id = Column(String, ForeignKey('integrations.id', ondelete='CASCADE'), nullable=False, index=True)
    provider_product_id = Column(String, nullable=False)
    provider_image_id = Column(String, nullable=False)
    blob_path = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    original_url = Column(String, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    content_type = Column(String, nullable=True, default='image/jpeg')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<ImportedImage {self.id} product={self.provider_product_id}>'


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
    angle_type = Column(String(50), nullable=True)
    step_timings = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship('Job', back_populates='items')
    
    @property
    def item_id(self):
        return self.id

    def __repr__(self):
        return f'<JobItem {self.id} status={self.status}>'
