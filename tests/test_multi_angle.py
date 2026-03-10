"""Tests for lighting & perspective style generation."""
from unittest.mock import patch
import pytest

from shared.scene_types import ANGLE_PROMPTS, DEFAULT_ANGLE_TYPES


# ---------------------------------------------------------------------------
# Style prompt lookup
# ---------------------------------------------------------------------------

class TestAnglePrompts:
    def test_all_default_styles_have_prompts(self):
        """Every style in DEFAULT_ANGLE_TYPES must have a prompt."""
        for style in DEFAULT_ANGLE_TYPES:
            assert style in ANGLE_PROMPTS, f"Missing prompt for style: {style}"

    def test_prompt_content(self):
        assert "eye-level" in ANGLE_PROMPTS["eye-level"]
        assert "overhead" in ANGLE_PROMPTS["overhead"] or "above" in ANGLE_PROMPTS["overhead"]
        assert "low-angle" in ANGLE_PROMPTS["low-angle"] or "upward" in ANGLE_PROMPTS["low-angle"]


# ---------------------------------------------------------------------------
# Edit prompt injection
# ---------------------------------------------------------------------------

class TestEditPromptAngle:
    def test_no_angle_no_injection(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("marble slab scene")
        assert "Show a" not in prompt
        assert "marble slab scene" in prompt

    def test_style_injected_into_prompt(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("marble slab scene", angle_type="eye-level")
        assert "eye-level" in prompt
        assert "marble slab scene" in prompt

    def test_overhead_style_injected(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt(None, angle_type="overhead")
        assert "overhead" in prompt or "above" in prompt

    def test_unknown_angle_no_injection(self):
        from pipeline_worker.pipeline import _build_edit_prompt
        prompt = _build_edit_prompt("scene", angle_type="nonexistent")
        assert "Show a" not in prompt


# ---------------------------------------------------------------------------
# Job creation — style fan-out via API
# ---------------------------------------------------------------------------

class TestAngleFanOut:
    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_single_style(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "angle_types": ["eye-level"]}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["angle_type"] == "eye-level"
        assert mock_debit.call_args[1]["amount"] == 1

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_multiple_styles(self, mock_debit, mock_job, mock_items, client):
        mock_debit.return_value = 97
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "angle_types": ["eye-level", "side-lit", "golden"]}],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        angle_types = [i["angle_type"] for i in items]
        assert angle_types == ["eye-level", "side-lit", "golden"]
        assert mock_debit.call_args[1]["amount"] == 3

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_scene_times_style_cross_product(self, mock_debit, mock_job, mock_items, client):
        """2 scenes × 3 styles = 6 items."""
        mock_debit.return_value = 94
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{
                "filename": "test.jpg",
                "scene_count": 2,
                "scene_types": ["studio", "outdoor"],
                "angle_types": ["eye-level", "low-angle", "overhead"],
            }],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 6
        assert mock_debit.call_args[1]["amount"] == 6
        # Verify cross-product: studio×eye-level, studio×low-angle, studio×overhead, outdoor×eye-level, ...
        assert items[0]["scene_type"] == "studio"
        assert items[0]["angle_type"] == "eye-level"
        assert items[2]["scene_type"] == "studio"
        assert items[2]["angle_type"] == "overhead"
        assert items[3]["scene_type"] == "outdoor"
        assert items[3]["angle_type"] == "eye-level"

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_no_styles_no_angle_type_in_response(self, mock_debit, mock_job, mock_items, client):
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
            "items": [{"filename": "test.jpg", "angle_types": ["invalid_style"]}],
        })
        assert resp.status_code == 422
        assert "Invalid angle_types" in resp.json()["detail"]

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    @patch("web_api.routes_jobs.get_scene_template")
    def test_template_times_style(self, mock_tmpl, mock_debit, mock_job, mock_items, client):
        """Templates × styles should cross-product."""
        mock_tmpl.return_value = {"id": "st_1", "prompt": "on marble", "scene_type": "luxury"}
        mock_debit.return_value = 98
        mock_job.return_value = {}
        mock_items.return_value = []

        resp = client.post("/v1/jobs", json={
            "items": [{
                "filename": "test.jpg",
                "scene_template_ids": ["st_1"],
                "angle_types": ["eye-level", "side-lit"],
            }],
        })
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert items[0]["angle_type"] == "eye-level"
        assert items[1]["angle_type"] == "side-lit"
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
            "processing_options": None, "created_at": None,
        }
        mock_items.return_value = [
            {
                "id": "item_1", "filename": "test.jpg", "status": "completed",
                "raw_blob_path": "path/raw", "output_blob_path": "path/out",
                "error_message": None, "scene_prompt": None,
                "scene_index": 0, "scene_type": "studio",
                "angle_type": "eye-level",
                "saved_background_path": None,
            }
        ]
        resp = client.get("/v1/jobs/job_1")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["angle_type"] == "eye-level"
