"""Tests for upload and download routes."""
from unittest.mock import patch, ANY
import pytest


# ── POST /v1/uploads/sas ──────────────────────────────────────────

class TestUploadSas:
    @patch("web_api.routes_uploads.update_job_item")
    @patch("web_api.routes_uploads.get_job_items_by_filename")
    @patch("web_api.routes_uploads.generate_upload_url")
    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_generate_sas_url(self, mock_job, mock_item, mock_sas, mock_siblings, mock_update, client):
        mock_job.return_value = {"id": "job_1", "tenant_id": "tenant_test"}
        mock_item.return_value = {"id": "item_1", "tenant_id": "tenant_test", "job_id": "job_1"}
        mock_sas.return_value = "https://storage.blob.core.windows.net/raw/path?sig=abc"
        mock_siblings.return_value = [
            {"id": "item_1"}, {"id": "item_2"},  # multi-scene siblings
        ]

        resp = client.post("/v1/uploads/sas", json={
            "job_id": "job_1", "item_id": "item_1", "filename": "test.jpg",
        })
        assert resp.status_code == 200
        assert "upload_url" in resp.json()
        # Both siblings should have raw_blob_path set
        assert mock_update.call_count == 2

    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_sas_unknown_job_404(self, mock_job, mock_item, client):
        mock_job.return_value = None
        mock_item.return_value = None
        resp = client.post("/v1/uploads/sas", json={
            "job_id": "job_missing", "item_id": "item_1", "filename": "test.jpg",
        })
        assert resp.status_code == 404

    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_sas_wrong_tenant_404(self, mock_job, mock_item, client):
        mock_job.return_value = {"id": "job_1"}
        mock_item.return_value = {"id": "item_1", "tenant_id": "other_tenant", "job_id": "job_1"}
        resp = client.post("/v1/uploads/sas", json={
            "job_id": "job_1", "item_id": "item_1", "filename": "test.jpg",
        })
        assert resp.status_code == 404


# ── POST /v1/uploads/complete ─────────────────────────────────────

class TestUploadComplete:
    @patch("web_api.routes_uploads.send_job_messages_batch")
    @patch("web_api.routes_uploads.update_job_item")
    @patch("web_api.routes_uploads.get_job_items_by_filename")
    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_complete_enqueues_siblings(self, mock_job, mock_item, mock_siblings, mock_update, mock_batch, client):
        mock_job.return_value = {
            "id": "job_1", "tenant_id": "tenant_test", "correlation_id": "corr_1",
        }
        mock_item.return_value = {"id": "item_1", "tenant_id": "tenant_test", "job_id": "job_1"}
        mock_siblings.return_value = [{"id": "item_1"}, {"id": "item_2"}]

        resp = client.post("/v1/uploads/complete", json={
            "job_id": "job_1", "item_id": "item_1", "filename": "test.jpg",
        })
        assert resp.status_code == 200
        assert mock_update.call_count == 2
        mock_batch.assert_called_once()
        assert len(mock_batch.call_args[0][0]) == 2


# ── GET /v1/downloads/{item_id} ───────────────────────────────────

class TestDownloads:
    @patch("web_api.routes_downloads.generate_download_url")
    @patch("web_api.routes_downloads.get_job_item")
    def test_download_output(self, mock_item, mock_sas, client):
        mock_item.return_value = {
            "id": "item_1", "tenant_id": "tenant_test",
            "output_blob_path": "tenant_test/jobs/j1/items/i1/outputs/out.png",
        }
        mock_sas.return_value = "https://storage.blob.core.windows.net/outputs/path?sig=abc"

        resp = client.get("/v1/downloads/item_1")
        assert resp.status_code == 200
        assert "download_url" in resp.json()

    @patch("web_api.routes_downloads.get_job_item")
    def test_download_not_found(self, mock_item, client):
        mock_item.return_value = None
        resp = client.get("/v1/downloads/item_missing")
        assert resp.status_code == 404

    @patch("web_api.routes_downloads.get_job_item")
    def test_download_wrong_tenant_403(self, mock_item, client):
        mock_item.return_value = {"id": "item_1", "tenant_id": "other_tenant"}
        resp = client.get("/v1/downloads/item_1")
        assert resp.status_code == 403

    @patch("web_api.routes_downloads.get_job_item")
    def test_download_output_not_ready_404(self, mock_item, client):
        mock_item.return_value = {
            "id": "item_1", "tenant_id": "tenant_test",
            "output_blob_path": None,
        }
        resp = client.get("/v1/downloads/item_1")
        assert resp.status_code == 404

    @patch("web_api.routes_downloads.generate_download_url")
    @patch("web_api.routes_downloads.get_job_item")
    def test_download_raw_bucket(self, mock_item, mock_sas, client):
        mock_item.return_value = {
            "id": "item_1", "tenant_id": "tenant_test",
            "raw_blob_path": "tenant_test/jobs/j1/items/i1/raw/test.jpg",
        }
        mock_sas.return_value = "https://example.com/raw?sig=abc"
        resp = client.get("/v1/downloads/item_1?bucket=raw")
        assert resp.status_code == 200


# ── GET /v1/downloads/jobs/{job_id}/export ────────────────────────

class TestExportDownload:
    @patch("web_api.routes_downloads.generate_download_url")
    @patch("web_api.routes_downloads.get_job_by_id")
    def test_download_export_zip(self, mock_job, mock_sas, client):
        mock_job.return_value = {
            "id": "job_1", "export_blob_path": "exports/job_1.zip",
        }
        mock_sas.return_value = "https://example.com/exports/job_1.zip?sig=abc"
        resp = client.get("/v1/downloads/jobs/job_1/export")
        assert resp.status_code == 200
        assert "download_url" in resp.json()

    @patch("web_api.routes_downloads.get_job_by_id")
    def test_export_not_ready_404(self, mock_job, client):
        mock_job.return_value = {"id": "job_1", "export_blob_path": None}
        resp = client.get("/v1/downloads/jobs/job_1/export")
        assert resp.status_code == 404

    @patch("web_api.routes_downloads.get_job_by_id")
    def test_export_job_not_found_404(self, mock_job, client):
        mock_job.return_value = None
        resp = client.get("/v1/downloads/jobs/job_missing/export")
        assert resp.status_code == 404
