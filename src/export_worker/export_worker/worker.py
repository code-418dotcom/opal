import io
import json
import logging
import time
import zipfile
from pathlib import PurePosixPath
from azure.servicebus import ServiceBusReceiveMode

from shared.config import settings
from shared.db import SessionLocal
from shared.models import Job, JobItem, ItemStatus, JobStatus
from shared.servicebus import get_client
from shared.storage import download_blob, upload_blob
from shared.export_presets import get_preset, ExportPreset
from shared.image_resize import resize_image

log = logging.getLogger("export_worker")


def _extract_payload(m) -> dict:
    body = b"".join([b for b in m.body]) if hasattr(m.body, "__iter__") else bytes(m.body)
    text = body.decode("utf-8", errors="ignore").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"job_id": text}


def _build_zip_filename(item: JobItem) -> str:
    """Build a descriptive filename for the ZIP entry."""
    stem = PurePosixPath(item.filename).stem
    suffix = PurePosixPath(item.filename).suffix or ".png"

    if item.scene_index is not None:
        label = item.scene_type or f"scene{item.scene_index}"
        return f"{stem}_{label}{suffix}"
    return f"{stem}{suffix}"


def process_export(job_id: str, tenant_id: str) -> None:
    """Build a ZIP of all completed items for a job."""
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job:
            log.warning("Job not found: %s", job_id)
            return

        # Idempotent: already exported
        if job.export_blob_path:
            log.info("Export already exists for job=%s at %s", job_id, job.export_blob_path)
            return

        items = list(job.items)
        terminal = [it for it in items if it.status in (ItemStatus.completed, ItemStatus.failed)]

        if len(terminal) < len(items):
            log.info("Job %s not fully done (%d/%d terminal), skipping export",
                     job_id, len(terminal), len(items))
            return

        completed = [it for it in items if it.status == ItemStatus.completed and it.output_blob_path]
        if not completed:
            log.warning("Job %s has no completed items with output paths", job_id)
            return

        # Build ZIP in memory
        buf = io.BytesIO()
        used_names: dict[str, int] = {}

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in completed:
                try:
                    data = download_blob("outputs", item.output_blob_path)
                except Exception as e:
                    log.error("Failed to download blob for item=%s: %s", item.id, e)
                    continue

                name = _build_zip_filename(item)
                # Deduplicate filenames
                if name in used_names:
                    used_names[name] += 1
                    stem = PurePosixPath(name).stem
                    suffix = PurePosixPath(name).suffix
                    name = f"{stem}_{used_names[name]}{suffix}"
                else:
                    used_names[name] = 0

                zf.writestr(name, data)
                log.info("Added to ZIP: %s (%d bytes)", name, len(data))

        zip_bytes = buf.getvalue()
        export_path = f"{tenant_id}/jobs/{job_id}/export.zip"

        upload_blob("exports", export_path, zip_bytes, content_type="application/zip")
        log.info("Uploaded export ZIP for job=%s: %s (%d bytes)", job_id, export_path, len(zip_bytes))

        # Update job record
        job.export_blob_path = export_path
        s.commit()
        log.info("Job %s export_blob_path set to %s", job_id, export_path)


def process_format_export(job_id: str, tenant_id: str, format_keys: list[str]) -> str | None:
    """Build a ZIP with platform-specific resized images in subfolders.

    Returns the blob path of the uploaded ZIP, or None on failure.
    """
    presets = []
    for key in format_keys:
        preset = get_preset(key)
        if preset:
            presets.append(preset)
    if not presets:
        log.warning("No valid format keys for job=%s: %s", job_id, format_keys)
        return None

    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job:
            log.warning("Job not found: %s", job_id)
            return None

        completed = [
            it for it in job.items
            if it.status == ItemStatus.completed and it.output_blob_path
        ]
        if not completed:
            log.warning("Job %s has no completed items", job_id)
            return None

        # Download all output images once
        image_cache: dict[str, bytes] = {}
        for item in completed:
            try:
                image_cache[item.id] = download_blob("outputs", item.output_blob_path)
            except Exception as e:
                log.error("Failed to download blob for item=%s: %s", item.id, e)

        if not image_cache:
            log.warning("No images downloaded for job=%s", job_id)
            return None

        # Build ZIP with platform subfolders
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for preset in presets:
                ext = ".png" if preset.bg_color == "transparent" else ".jpg"
                for item in completed:
                    if item.id not in image_cache:
                        continue
                    try:
                        resized = resize_image(image_cache[item.id], preset)
                    except Exception as e:
                        log.error("Resize failed item=%s preset=%s: %s", item.id, preset.key, e)
                        continue

                    zip_name = _build_zip_filename(item)
                    stem = PurePosixPath(zip_name).stem
                    entry_path = f"{preset.key}/{stem}{ext}"
                    zf.writestr(entry_path, resized)

        zip_bytes = buf.getvalue()
        suffix = "_".join(format_keys[:3])
        if len(format_keys) > 3:
            suffix += f"_+{len(format_keys) - 3}"
        export_path = f"{tenant_id}/jobs/{job_id}/export_{suffix}.zip"

        upload_blob("exports", export_path, zip_bytes, content_type="application/zip")
        log.info("Format export for job=%s: %s (%d bytes, %d formats)",
                 job_id, export_path, len(zip_bytes), len(presets))
        return export_path


def main():
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    log.info("Starting export_worker. exports_queue=%s namespace=%s",
             settings.SERVICEBUS_EXPORTS_QUEUE, settings.SERVICEBUS_NAMESPACE)

    while True:
        try:
            with get_client() as client:
                receiver = client.get_queue_receiver(
                    queue_name=settings.SERVICEBUS_EXPORTS_QUEUE,
                    max_wait_time=20,
                    receive_mode=ServiceBusReceiveMode.PEEK_LOCK,
                )
                with receiver:
                    messages = receiver.receive_messages(max_message_count=10, max_wait_time=20)
                    for m in messages:
                        try:
                            payload = _extract_payload(m)
                            job_id = payload.get("job_id")
                            tenant_id = payload.get("tenant_id")

                            if not job_id:
                                log.warning("Export message without job_id; completing to avoid poison loop.")
                                receiver.complete_message(m)
                                continue

                            format_keys = payload.get("format_keys")
                            log.info("Processing export for job_id=%s tenant_id=%s formats=%s",
                                     job_id, tenant_id, format_keys)

                            if format_keys:
                                process_format_export(job_id, tenant_id or "default", format_keys)
                            else:
                                process_export(job_id, tenant_id or "default")

                            receiver.complete_message(m)
                            log.info("Completed export message for job_id=%s", job_id)

                        except Exception:
                            log.exception("Export processing failed; abandoning message.")
                            receiver.abandon_message(m)

        except Exception:
            log.exception("Top-level loop error. Sleeping 5s.")
            time.sleep(5)


if __name__ == "__main__":
    main()
