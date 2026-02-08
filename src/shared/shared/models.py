from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
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
    partial = 'partial'  # Some items completed, some failed


class Job(Base):
    __tablename__ = 'jobs'

    job_id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    brand_profile_id = Column(String, nullable=False)
    correlation_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.created, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship('JobItem', back_populates='job', lazy='select')

    def __repr__(self):
        return f'<Job {self.job_id} status={self.status}>'


class JobItem(Base):
    __tablename__ = 'job_items'

    item_id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey('jobs.job_id'), nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    status = Column(SQLEnum(ItemStatus), nullable=False, default=ItemStatus.created, index=True)
    raw_blob_path = Column(String, nullable=True)
    output_blob_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship('Job', back_populates='items')

    def __repr__(self):
        return f'<JobItem {self.item_id} status={self.status}>'
