"""Tests for multi-angle product photography generation."""
from unittest.mock import patch
import pytest

from shared.scene_types import ANGLE_PROMPTS, DEFAULT_ANGLE_TYPES


# ---------------------------------------------------------------------------
# Angle prompt lookup
# ---------------------------------------------------------------------------

class TestAnglePrompts:
    def test_all_default_angles_have_prompts(self):
        """Every angle in DEFAULT_ANGLE_TYPES must have a prompt."""
        for angle in DEFAULT_ANGLE_TYPES:
            assert angle in ANGLE_PROMPTS, f"Missing prompt for angle: {angle}"

    def test_prompt_content(self):
        assert "front" in ANGLE_PROMPTS["front"]
        assert "top-down" in ANGLE_PROMPTS["top"] or "above" in ANGLE_PROMPTS["top"]
        assert "three-quarter" in ANGLE_PROMPTS["3/4"] or "45 degrees" in ANGLE_PROMPTS["3/4"]


# ---------------------------------------------------------------------------
# Edit prompt injection
# ---------------------------------------------------------------------------

class TestEditPromptAngle:
    def test_no_angle_no_injection(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("marble slab scene")
        assert "Show a" not in prompt
        assert "marble slab scene" in prompt

    def test_angle_injected_into_prompt(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("marble slab scene", angle_type="front")
        assert "straight-on front view" in prompt
        assert "marble slab scene" in prompt

    def test_top_angle_injected(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt(None, angle_type="top")
        assert "top-down" in prompt or "above" in prompt

    def test_unknown_angle_no_injection(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("scene", angle_type="nonexistent")
        assert "Show a" not in prompt


# ---------------------------------------------------------------------------
# Job creation — angle fan-out via API
# ---------------------------------------------------------------------------

class TestAngleFanOut:
    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_single_angle(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "angle_types": ["front"]}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["angle_type"] == "front"
        assert mock_debit.call_args[1]["amount"] == 1

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_multiple_angles(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 97
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "angle_types": ["front", "back", "left"]}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        angle_types = [i["angle_type"] for i in items]
        assert angle_types == ["front", "back", "left"]
        assert mock_debit.call_args[1]["amount"] == 3

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_scene_times_angle_cross_product(self, mock_debit, mock_job, mock_items, client):
        """2 scenes × 3 angles = 6 items."""
        mock_debit.return_value = 94
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{
                "filename": "test.jpg",
                "scene_count": 2,
                "scene_types": ["studio", "outdoor"],
                "angle_types": ["front", "3/4", "top"],
            }],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 6
        assert mock_debit.call_args[1]["amount"] == 6
        # Verify cross-product: studio×front, studio×3/4, studio×top, outdoor×front, ...
        assert items[0]["scene_type"] == "studio"
        assert items[0]["angle_type"] == "front"
        assert items[2]["scene_type"] == "studio"
        assert items[2]["angle_type"] == "top"
        assert items[3]["scene_type"] == "outdoor"
        assert items[3]["angle_type"] == "front"

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_no_angles_no_angle_type_in_response(self, mock_debit, mock_job, mock_items, client):
        """When no angle_types specified, angle_type should be null."""
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0].get("angle_type") is None

    def test_invalid_angle_type_422(self, client):
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "angle_types": ["invalid_angle"]}],
        })
        assert resp.status_code == 422
        assert "Invalid angle_types" in resp.json()["detail"]

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    @patch("web_api.routes_jobs.get_scene_template")
    def test_template_times_angle(self, mock_tmpl, mock_debit, mock_job, mock_items, client):
        """Templates × angles should cross-product."""
        mock_tmpl.return_value = {"id": "st_1", "prompt": "on marble", "scene_type": "luxury"}
        mock_debit.return_value = 98
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{
                "filename": "test.jpg",
                "scene_template_ids": ["st_1"],
                "angle_types": ["front", "back"],
            }],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert items[0]["angle_type"] == "front"
        assert items[1]["angle_type"] == "back"
        assert mock_debit.call_args[1]["amount"] == 2


# ---------------------------------------------------------------------------
# Job detail includes angle_type
# ---------------------------------------------------------------------------

class TestJobDetailAngle:
    @patch("web_api.routes_jobs.get_job_items")
    @patch("web_api.routes_jobs.get_job_by_id")
    def test_get_job_includes_angle_type(self, mock_job, mock_items, client):
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
                "scene_index": 0, "scene_type": "studio",
                "angle_type": "front",
                "saved_background_path": None,
            }
        ]
        resp = client.get("/v1/jobs/job_1")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["angle_type"] == "front"
