"""
Shared pipeline message schema and job finalization utilities.
All pipeline workers (bg_removal, scene, upscale) import from here.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

LOG = logging.getLogger(__name__)


@dataclass
class ProcessingOptions:
    remove_background: bool = True
    generate_scene: bool = True
    upscale: bool = False

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProcessingOptions":
        return cls(
            remove_background=d.get("remove_background", True),
            generate_scene=d.get("generate_scene", True),
            upscale=d.get("upscale", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "remove_background": self.remove_background,
            "generate_scene": self.generate_scene,
            "upscale": self.upscale,
        }


@dataclass
class PipelineMessage:
    """
    Carries full pipeline state between workers via Service Bus.
    Workers carry blob PATHS (not SAS URLs) — each worker generates fresh SAS tokens.
    Intermediate blob paths enable idempotent redelivery: if a path is already set,
    the worker skips re-processing and routes to the next step.
    """
    job_id: str
    item_id: str
    tenant_id: str
    correlation_id: str
    raw_blob_path: str
    processing_options: ProcessingOptions = field(default_factory=ProcessingOptions)
    bg_removed_blob_path: Optional[str] = None   # set by bg_removal_worker
    scene_blob_path: Optional[str] = None         # set by scene_worker
    scene_prompt: Optional[str] = None            # set by orchestrator from brand profile

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineMessage":
        return cls(
            job_id=d["job_id"],
            item_id=d["item_id"],
            tenant_id=d["tenant_id"],
            correlation_id=d.get("correlation_id", ""),
            raw_blob_path=d["raw_blob_path"],
            processing_options=ProcessingOptions.from_dict(d.get("processing_options", {})),
            bg_removed_blob_path=d.get("bg_removed_blob_path"),
            scene_blob_path=d.get("scene_blob_path"),
            scene_prompt=d.get("scene_prompt"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "item_id": self.item_id,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "raw_blob_path": self.raw_blob_path,
            "processing_options": self.processing_options.to_dict(),
            "bg_removed_blob_path": self.bg_removed_blob_path,
            "scene_blob_path": self.scene_blob_path,
            "scene_prompt": self.scene_prompt,
        }

    @classmethod
    def from_json(cls, s: str) -> "PipelineMessage":
        return cls.from_dict(json.loads(s))

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def best_available_blob(self) -> tuple[str, str]:
        """
        Returns (container, blob_path) for the best available intermediate result.
        Priority: scene_blob > bg_removed_blob > raw_blob
        """
        if self.scene_blob_path:
            return "outputs", self.scene_blob_path
        if self.bg_removed_blob_path:
            return "outputs", self.bg_removed_blob_path
        return "raw", self.raw_blob_path


def mark_item_failed(job_id: str, item_id: str, error: str) -> None:
    """
    Mark an item as failed and immediately reconcile the parent job status.
    Call this from worker exception handlers so the job never stays stuck in 'processing'.
    """
    from shared.db import SessionLocal
    from shared.models import JobItem, ItemStatus

    if not item_id:
        return
    with SessionLocal() as s:
        item = s.get(JobItem, item_id)
        if item:
            item.status = ItemStatus.failed
            item.error_message = str(error)[:4000]
            s.commit()
    if job_id:
        finalize_job_status(job_id)


def finalize_job_status(job_id: str) -> None:
    """
    Update overall job status based on all item statuses.
    Call after an item reaches completed or failed.
    Moved from orchestrator so all workers can import it.
    Fires webhook callback on terminal states (completed/failed/partial).
    """
    from shared.db import SessionLocal
    from shared.models import Job, JobItem, JobStatus, ItemStatus

    callback_url = None
    new_status = None

    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job:
            return

        items = list(job.items)
        if not items:
            return

        statuses = [item.status for item in items]
        completed = statuses.count(ItemStatus.completed)
        failed = statuses.count(ItemStatus.failed)
        processing = statuses.count(ItemStatus.processing)
        pending = len(items) - completed - failed - processing  # created/uploaded

        if completed == len(items):
            job.status = JobStatus.completed
            new_status = "completed"
            LOG.info("Job COMPLETED: %s", job_id)
        elif pending > 0 or processing > 0:
            job.status = JobStatus.processing
        elif failed == len(items):
            job.status = JobStatus.failed
            new_status = "failed"
        elif failed > 0:
            job.status = JobStatus.partial
            new_status = "partial"

        s.commit()

        if new_status and job.callback_url:
            callback_url = job.callback_url

    if callback_url:
        _fire_webhook(callback_url, job_id, new_status)


def _fire_webhook(url: str, job_id: str, status: str) -> None:
    """Fire-and-forget webhook POST on job completion. No retries (MVP)."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            client.post(url, json={"job_id": job_id, "status": status})
        LOG.info("Webhook fired: job=%s status=%s url=%s", job_id, status, url)
    except Exception as e:
        LOG.warning("Webhook failed: job=%s url=%s error=%s", job_id, url, e)
