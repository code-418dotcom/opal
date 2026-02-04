import enum
from sqlalchemy import String, DateTime, Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base


class ItemStatus(str, enum.Enum):
    created = "created"
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobStatus(str, enum.Enum):
    created = "created"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    brand_profile_id: Mapped[str] = mapped_column(String(128), default="default")
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.created)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["JobItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobItem(Base):
    __tablename__ = "job_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), ForeignKey("jobs.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.created)

    raw_blob_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_blob_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job: Mapped["Job"] = relationship(back_populates="items")


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    delta: Mapped[int] = mapped_column(Integer)  # + credits granted, - credits used
    reason: Mapped[str] = mapped_column(String(256))
    ref: Mapped[str | None] = mapped_column(String(256), nullable=True)  # payment id, job id, etc.
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
