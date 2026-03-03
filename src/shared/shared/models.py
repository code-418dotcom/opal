from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, JSON, ARRAY
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


class BrandProfile(Base):
    __tablename__ = 'brand_profiles'

    id = Column(String, primary_key=True, name='id')
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    default_scene_prompt = Column(String, nullable=True)
    style_keywords = Column(ARRAY(String), nullable=True)
    color_palette = Column(ARRAY(String), nullable=True)
    mood = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BrandProfile {self.id} name={self.name}>'


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(String, primary_key=True, name='id')
    tenant_id = Column(String, nullable=False, index=True)
    brand_profile_id = Column(String, nullable=False)
    correlation_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.created, index=True)
    processing_options = Column(JSON, nullable=True)
    callback_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship('JobItem', back_populates='job', lazy='select')
    
    @property
    def job_id(self):
        return self.id

    def __repr__(self):
        return f'<Job {self.id} status={self.status}>'


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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship('Job', back_populates='items')
    
    @property
    def item_id(self):
        return self.id

    def __repr__(self):
        return f'<JobItem {self.id} status={self.status}>'
