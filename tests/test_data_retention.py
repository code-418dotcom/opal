"""Tests for data retention cleanup endpoint."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends

from web_api.routes_admin import router as admin_router, require_admin


def _admin_override():
    return {"user_id": "apikey", "tenant_id": "test", "is_admin": True}


def _make_client():
    app = FastAPI()
    app.include_router(admin_router, dependencies=[Depends(require_admin)])
    app.dependency_overrides[require_admin] = _admin_override
    return TestClient(app)


@patch("web_api.routes_admin.get_jobs_older_than")
def test_cleanup_dry_run(mock_get_jobs):
    mock_get_jobs.return_value = [
        {"id": "job-1", "tenant_id": "t1", "status": "completed", "created_at": "2025-01-01T00:00:00"},
        {"id": "job-2", "tenant_id": "t1", "status": "failed", "created_at": "2025-01-02T00:00:00"},
    ]

    client = _make_client()
    resp = client.post("/v1/admin/cleanup", json={"retention_days": 90, "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["jobs_found"] == 2
    mock_get_jobs.assert_called_once_with(90, limit=50)


@patch("web_api.routes_admin.delete_job_cascade")
@patch("web_api.routes_admin.get_jobs_older_than")
def test_cleanup_execute(mock_get_jobs, mock_delete):
    mock_get_jobs.return_value = [
        {"id": "job-1", "tenant_id": "t1", "status": "completed", "created_at": "2025-01-01T00:00:00"},
    ]
    mock_delete.return_value = {
        "job_id": "job-1",
        "items_deleted": 3,
        "job_deleted": True,
        "blob_paths": [("raw", "t1/jobs/job-1/item-1/raw/photo.jpg")],
    }

    client = _make_client()
    with patch("shared.storage.delete_blob", return_value=True):
        resp = client.post("/v1/admin/cleanup", json={"retention_days": 30, "dry_run": False})

    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is False
    assert data["jobs_deleted"] == 1
    assert data["blobs_deleted"] == 1


def test_cleanup_validation():
    client = _make_client()
    # retention_days < 7 should fail validation
    resp = client.post("/v1/admin/cleanup", json={"retention_days": 3, "dry_run": True})
    assert resp.status_code == 422


@patch("web_api.routes_admin.get_jobs_older_than")
def test_cleanup_default_is_dry_run(mock_get_jobs):
    mock_get_jobs.return_value = []
    client = _make_client()
    resp = client.post("/v1/admin/cleanup", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["retention_days"] == 90
