"""Tests for job routes: create, list, get, enqueue."""
from unittest.mock import patch, ANY
import pytest

MOCK_USER = {
    "user_id": "user_test123",
    "tenant_id": "tenant_test",
    "email": "test@example.com",
    "token_balance": 100,
    "is_admin": False,
}


# ── POST /v1/jobs ─────────────────────────────────────────────────

class TestCreateJob:
    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_create_simple_job(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 99  # new balance after debit
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert len(data["items"]) == 1
        mock_debit.assert_called_once()

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_insufficient_tokens_402(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = None  # insufficient balance
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
        })
        assert resp.status_code == 402
        assert "Insufficient" in resp.json()["detail"]

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    def test_apikey_user_skips_token_deduction(self, mock_job, mock_items, apikey_client):
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = apikey_client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
        })
        assert resp.status_code == 200

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_multi_scene_creates_multiple_items(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 97
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "product.jpg", "scene_count": 3}],
        })
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 3
        # Cost should be 3 tokens
        assert mock_debit.call_args[1]["amount"] == 3

    @patch("web_api.routes_jobs.get_brand_profile")
    def test_unknown_brand_profile_404(self, mock_bp, client):
        mock_bp.return_value = None
        resp = client.post("/v1/jobs", json={
            "brand_profile_id": "bp_unknown",
            "items": [{"filename": "test.jpg"}],
        })
        assert resp.status_code == 404

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    @patch("web_api.routes_jobs.get_scene_template")
    def test_scene_template_mode(self, mock_tmpl, mock_debit, mock_job, mock_items, client):
        mock_tmpl.return_value = {"id": "st_1", "prompt": "on marble", "scene_type": "flat_lay"}
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "scene_template_ids": ["st_1"]}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["scene_type"] == "flat_lay"

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    @patch("web_api.routes_jobs.get_scene_template")
    def test_unknown_scene_template_404(self, mock_tmpl, mock_debit, mock_job, mock_items, client):
        mock_tmpl.return_value = None
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "scene_template_ids": ["st_missing"]}],
        })
        assert resp.status_code == 404

    def test_empty_items_422(self, client):
        resp = client.post("/v1/jobs", json={"items": []})
        assert resp.status_code == 422

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_processing_options_passed_through(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
            "processing_options": {
                "remove_background": True,
                "generate_scene": False,
                "upscale": True,
            },
        })
        assert resp.status_code == 200
        opts = resp.json()["processing_options"]
        assert opts["generate_scene"] is False

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_scene_types_length_mismatch_422(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 99
        mock_job.return_value = {}
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "scene_count": 3, "scene_types": ["flat_lay"]}],
        })
        assert resp.status_code == 422


# ── GET /v1/jobs ──────────────────────────────────────────────────

class TestListJobs:
    @patch("web_api.routes_jobs.list_jobs")
    def test_list_jobs(self, mock_list, client):
        mock_list.return_value = [{"id": "job_1", "status": "completed"}]
        resp = client.get("/v1/jobs")
        assert resp.status_code == 200
        assert len(resp.json()["jobs"]) == 1

    @patch("web_api.routes_jobs.list_jobs")
    def test_list_jobs_with_filter(self, mock_list, client):
        mock_list.return_value = []
        resp = client.get("/v1/jobs?status=processing&limit=5&offset=10")
        assert resp.status_code == 200
        mock_list.assert_called_once_with(
            MOCK_USER["tenant_id"], status="processing", limit=5, offset=10,
        )


# ── GET /v1/jobs/{job_id} ─────────────────────────────────────────

class TestGetJob:
    @patch("web_api.routes_jobs.get_job_items")
    @patch("web_api.routes_jobs.get_job_by_id")
    def test_get_existing_job(self, mock_job, mock_items, client):
        mock_job.return_value = {
            "id": "job_1", "tenant_id": "tenant_test",
            "brand_profile_id": "default", "status": "completed",
            "correlation_id": "corr_1", "export_blob_path": None,
        }
        mock_items.return_value = [
            {
                "id": "item_1", "filename": "test.jpg", "status": "completed",
                "raw_blob_path": "path/raw", "output_blob_path": "path/out",
                "error_message": None, "scene_prompt": None,
                "scene_index": None, "scene_type": None,
                "saved_background_path": None,
            }
        ]
        resp = client.get("/v1/jobs/job_1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "job_1"
        assert len(data["items"]) == 1

    @patch("web_api.routes_jobs.get_job_by_id")
    def test_get_unknown_job_404(self, mock_job, client):
        mock_job.return_value = None
        resp = client.get("/v1/jobs/job_missing")
        assert resp.status_code == 404


# ── POST /v1/jobs/{job_id}/enqueue ────────────────────────────────

class TestEnqueueJob:
    @patch("web_api.routes_jobs.update_job_status")
    @patch("web_api.routes_jobs.send_job_message")
    @patch("web_api.routes_jobs.get_job_items")
    @patch("web_api.routes_jobs.get_job_by_id")
    def test_enqueue_sends_messages(self, mock_job, mock_items, mock_send, mock_update, client):
        mock_job.return_value = {
            "id": "job_1", "correlation_id": "corr_1",
            "processing_options": {"remove_background": True},
        }
        mock_items.return_value = [
            {"id": "item_1", "status": "uploaded"},
            {"id": "item_2", "status": "completed"},  # skip - already done
        ]
        resp = client.post("/v1/jobs/job_1/enqueue")
        assert resp.status_code == 200
        assert mock_send.call_count == 1  # only the uploaded item
        mock_update.assert_called_once_with("job_1", "processing")

    @patch("web_api.routes_jobs.get_job_by_id")
    def test_enqueue_unknown_job_404(self, mock_job, client):
        mock_job.return_value = None
        resp = client.post("/v1/jobs/job_missing/enqueue")
        assert resp.status_code == 404
