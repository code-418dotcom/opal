#!/usr/bin/env python3
"""
Opal API Smoke Test
===================
End-to-end test: upload image → create job → enqueue → poll until done → download export ZIP.

Usage:
    python scripts/smoke_test.py                          # uses defaults
    python scripts/smoke_test.py --image photo.png        # custom image
    python scripts/smoke_test.py --scene-count 2          # multi-scene
    python scripts/smoke_test.py --no-scene --no-upscale  # bg-removal only

Environment:
    OPAL_API_URL   – API base URL (default: deployed dev)
    OPAL_API_KEY   – API key     (default: "anonymous")
"""

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

DEFAULT_API_URL = (
    "https://opal-web-api-dev.victoriousmoss-91bcd75e"
    ".westeurope.azurecontainerapps.io/v1"
)

POLL_INTERVAL = 5  # seconds
POLL_TIMEOUT = 300  # seconds


def log(msg: str):
    print(f"[smoke] {msg}", flush=True)


def fail(msg: str):
    print(f"[smoke] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def make_client(base_url: str, api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers={"X-API-Key": api_key},
        timeout=60,
    )


def ensure_test_image(path: Path) -> Path:
    """Create a tiny valid PNG if no image is provided."""
    if path.exists():
        return path
    log(f"Creating minimal test image at {path}")
    # Minimal 1x1 red PNG (67 bytes)
    import struct
    import zlib

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw_pixel = b"\x00\xff\x00\x00"  # filter=none, R, G, B
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw_pixel))
        + png_chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def step_health(client: httpx.Client):
    log("Checking API health...")
    # healthz is mounted at root, not under /v1
    base = str(client.base_url).replace("/v1", "")
    r = httpx.get(f"{base}/healthz", timeout=10)
    if r.status_code != 200:
        fail(f"Health check returned {r.status_code}: {r.text}")
    log(f"  OK – {r.json()}")


def step_create_job(
    client: httpx.Client,
    filename: str,
    scene_count: int,
    scene_types: list[str] | None,
    scene_prompt: str | None,
    opts: dict,
) -> dict:
    log(f"Creating job (scene_count={scene_count}, opts={opts})...")
    item = {"filename": filename, "scene_count": scene_count}
    if scene_types:
        item["scene_types"] = scene_types
    if scene_prompt:
        item["scene_prompt"] = scene_prompt

    body = {"items": [item], "processing_options": opts}
    r = client.post("/jobs", json=body)
    if r.status_code != 200:
        fail(f"Create job returned {r.status_code}: {r.text}")
    data = r.json()
    log(f"  job_id={data['job_id']}, items={len(data['items'])}")
    for it in data["items"]:
        log(f"    item_id={it['item_id']} scene_index={it.get('scene_index')} scene_type={it.get('scene_type')}")
    return data


def step_upload(client: httpx.Client, job_id: str, item_id: str, image_path: Path) -> str:
    log(f"Uploading {image_path.name} for item {item_id}...")
    with open(image_path, "rb") as f:
        r = client.post(
            "/uploads/direct",
            data={"job_id": job_id, "item_id": item_id},
            files={"file": (image_path.name, f, "image/png")},
        )
    if r.status_code != 200:
        fail(f"Upload returned {r.status_code}: {r.text}")
    data = r.json()
    log(f"  raw_blob_path={data['raw_blob_path']}")
    return data["raw_blob_path"]


def step_enqueue(client: httpx.Client, job_id: str):
    log(f"Enqueuing job {job_id}...")
    r = client.post(f"/jobs/{job_id}/enqueue")
    if r.status_code != 200:
        fail(f"Enqueue returned {r.status_code}: {r.text}")
    log("  Enqueued OK")


def step_poll(client: httpx.Client, job_id: str) -> dict:
    log(f"Polling job status (timeout={POLL_TIMEOUT}s, interval={POLL_INTERVAL}s)...")
    terminal = {"completed", "failed", "partial"}
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            fail(f"Timed out after {POLL_TIMEOUT}s")

        r = client.get(f"/jobs/{job_id}")
        if r.status_code != 200:
            fail(f"Get job returned {r.status_code}: {r.text}")

        data = r.json()
        status = data["status"]
        item_statuses = [it["status"] for it in data["items"]]
        log(f"  [{elapsed:5.0f}s] job={status}  items={item_statuses}")

        if status in terminal:
            return data

        time.sleep(POLL_INTERVAL)


def step_download_export(client: httpx.Client, job_id: str, output_dir: Path):
    log("Fetching export ZIP download URL...")
    r = client.get(f"/downloads/jobs/{job_id}/export")
    if r.status_code != 200:
        log(f"  Export not available ({r.status_code}): {r.text}")
        return

    url = r.json()["download_url"]
    log("  Downloading ZIP...")
    zr = httpx.get(url, timeout=60)
    if zr.status_code != 200:
        fail(f"ZIP download returned {zr.status_code}")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"smoke_export_{job_id}.zip"
    zip_path.write_bytes(zr.content)
    log(f"  Saved to {zip_path} ({len(zr.content)} bytes)")


def step_download_items(client: httpx.Client, items: list[dict], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        if item["status"] != "completed":
            log(f"  Skipping item {item['item_id']} (status={item['status']})")
            continue
        r = client.get(f"/downloads/{item['item_id']}")
        if r.status_code != 200:
            log(f"  Download URL failed for {item['item_id']}: {r.status_code}")
            continue
        url = r.json()["download_url"]
        dr = httpx.get(url, timeout=60)
        if dr.status_code != 200:
            log(f"  Download failed for {item['item_id']}: {dr.status_code}")
            continue
        scene_tag = f"_s{item.get('scene_index', 0)}" if item.get("scene_index") is not None else ""
        out_path = output_dir / f"{item['item_id']}{scene_tag}.png"
        out_path.write_bytes(dr.content)
        log(f"  Saved {out_path.name} ({len(dr.content)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Opal API smoke test")
    parser.add_argument("--image", type=Path, default=Path("scripts/test_image.png"),
                        help="Image file to upload (auto-created if missing)")
    parser.add_argument("--scene-count", type=int, default=2,
                        help="Number of scenes to generate (default: 2)")
    parser.add_argument("--scene-types", nargs="*", default=None,
                        help="Scene types (e.g. studio lifestyle)")
    parser.add_argument("--scene-prompt", type=str, default=None,
                        help="Custom scene prompt")
    parser.add_argument("--no-bg-removal", action="store_true")
    parser.add_argument("--no-scene", action="store_true")
    parser.add_argument("--no-upscale", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/smoke_output"),
                        help="Directory for downloaded results")
    parser.add_argument("--api-url", default=os.environ.get("OPAL_API_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key", default=os.environ.get("OPAL_API_KEY", "anonymous"))
    args = parser.parse_args()

    log(f"API: {args.api_url}")
    log(f"Key: {args.api_key[:8]}...")

    image_path = ensure_test_image(args.image)
    client = make_client(args.api_url, args.api_key)

    opts = {
        "remove_background": not args.no_bg_removal,
        "generate_scene": not args.no_scene,
        "upscale": not args.no_upscale,
    }

    # 1. Health check
    step_health(client)

    # 2. Create job
    job = step_create_job(
        client,
        filename=image_path.name,
        scene_count=args.scene_count,
        scene_types=args.scene_types,
        scene_prompt=args.scene_prompt,
        opts=opts,
    )
    job_id = job["job_id"]

    # 3. Upload image (only to first item — siblings share the upload)
    first_item = job["items"][0]
    step_upload(client, job_id, first_item["item_id"], image_path)

    # 4. Enqueue
    step_enqueue(client, job_id)

    # 5. Poll until terminal
    result = step_poll(client, job_id)

    # 6. Report
    status = result["status"]
    completed = sum(1 for it in result["items"] if it["status"] == "completed")
    failed = sum(1 for it in result["items"] if it["status"] == "failed")
    total = len(result["items"])

    log(f"RESULT: job={status}, items={completed}/{total} completed, {failed} failed")

    for it in result["items"]:
        if it.get("error_message"):
            log(f"  ERROR on {it['item_id']}: {it['error_message']}")

    # 7. Download outputs
    if completed > 0:
        step_download_items(client, result["items"], args.output_dir)

    # 8. Download export ZIP
    if result.get("export_blob_path"):
        step_download_export(client, job_id, args.output_dir)

    # Final verdict
    if status == "completed":
        log("PASS — all items completed successfully")
    elif status == "partial":
        log(f"WARN — partial completion ({completed}/{total})")
        sys.exit(1)
    else:
        log(f"FAIL — job status: {status}")
        sys.exit(2)


if __name__ == "__main__":
    main()
