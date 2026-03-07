"""Tests for marketplace export presets and image resizing."""
import io
from unittest.mock import patch

import pytest
from PIL import Image

from shared.export_presets import get_preset, list_presets, PRESETS
from shared.image_resize import resize_image


def _make_test_image(width: int, height: int, mode: str = "RGB") -> bytes:
    """Create a simple test image and return as bytes."""
    img = Image.new(mode, (width, height), color=(100, 150, 200))
    buf = io.BytesIO()
    fmt = "PNG" if mode == "RGBA" else "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestPresets:
    def test_all_presets_have_required_fields(self):
        for key, preset in PRESETS.items():
            assert preset.key == key
            assert preset.name
            assert preset.width > 0
            assert preset.height > 0
            assert preset.bg_color in ("white", "transparent") or preset.bg_color.startswith("#")
            assert preset.fit in ("contain", "cover")
            assert 1 <= preset.quality <= 100

    def test_get_preset_valid(self):
        preset = get_preset("amazon_main")
        assert preset is not None
        assert preset.width == 1600
        assert preset.height == 1600

    def test_get_preset_invalid(self):
        assert get_preset("nonexistent") is None

    def test_list_presets_returns_dicts(self):
        result = list_presets()
        assert len(result) == len(PRESETS)
        for item in result:
            assert "key" in item
            assert "name" in item
            assert "width" in item
            assert "height" in item

    def test_key_platforms_exist(self):
        """Ensure the most important marketplace presets are defined."""
        for key in ["amazon_main", "shopify", "instagram_feed", "instagram_story", "etsy", "ebay"]:
            assert key in PRESETS, f"Missing preset: {key}"


class TestImageResize:
    def test_contain_square_to_square(self):
        """Square image to square preset should maintain aspect ratio."""
        img_bytes = _make_test_image(800, 800)
        preset = get_preset("amazon_main")  # 1600x1600
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (1600, 1600)

    def test_contain_landscape_to_square(self):
        """Landscape image should be padded vertically in a square preset."""
        img_bytes = _make_test_image(1600, 800)
        preset = get_preset("instagram_feed")  # 1080x1080
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (1080, 1080)

    def test_contain_portrait_to_square(self):
        """Portrait image should be padded horizontally in a square preset."""
        img_bytes = _make_test_image(800, 1600)
        preset = get_preset("shopify")  # 2048x2048
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (2048, 2048)

    def test_contain_to_portrait(self):
        """Image resized to Instagram Story (9:16)."""
        img_bytes = _make_test_image(1000, 1000)
        preset = get_preset("instagram_story")  # 1080x1920
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (1080, 1920)

    def test_contain_to_landscape(self):
        """Image resized to Facebook Ad (1.91:1)."""
        img_bytes = _make_test_image(1000, 1000)
        preset = get_preset("facebook_ad")  # 1200x630
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (1200, 630)

    def test_transparent_output_is_png(self):
        """Transparent background preset should produce PNG."""
        img_bytes = _make_test_image(800, 800)
        preset = get_preset("web_large")  # transparent bg
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.format == "PNG"
        assert img.mode == "RGBA"

    def test_white_bg_output_is_jpeg(self):
        """White background preset should produce JPEG."""
        img_bytes = _make_test_image(800, 800)
        preset = get_preset("amazon_main")  # white bg
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"

    def test_small_image_scales_up(self):
        """Small image should scale up to fill target."""
        img_bytes = _make_test_image(200, 200)
        preset = get_preset("web_thumb")  # 400x400
        result = resize_image(img_bytes, preset)
        img = Image.open(io.BytesIO(result))
        assert img.size == (400, 400)


class TestExportPresetsEndpoint:
    """Test the GET /v1/export-presets API endpoint."""

    def test_list_presets_endpoint(self):
        from fastapi.testclient import TestClient
        from web_api.main import app

        with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
            client = TestClient(app)
            resp = client.get("/v1/export-presets", headers={"X-API-Key": "test_key_123"})
            assert resp.status_code == 200
            data = resp.json()
            assert "presets" in data
            assert len(data["presets"]) > 0
            assert data["presets"][0]["key"]


class TestFormatExportEndpoint:
    """Test the POST /v1/downloads/jobs/{job_id}/export-formats endpoint."""

    @patch("shared.queue_database.send_export_message")
    @patch("web_api.routes_downloads.get_job_by_id")
    def test_format_export_queues_message(self, mock_job, mock_send):
        from fastapi.testclient import TestClient
        from web_api.main import app

        mock_job.return_value = {"id": "job_123", "tenant_id": "default"}
        with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
            client = TestClient(app)
            resp = client.post(
                "/v1/downloads/jobs/job_123/export-formats",
                headers={"X-API-Key": "test_key_123"},
                json={"format_keys": ["amazon_main", "shopify"]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "queued"
            assert data["format_keys"] == ["amazon_main", "shopify"]
            mock_send.assert_called_once()

    @patch("web_api.routes_downloads.get_job_by_id")
    def test_format_export_invalid_keys(self, mock_job):
        from fastapi.testclient import TestClient
        from web_api.main import app

        mock_job.return_value = {"id": "job_123", "tenant_id": "default"}
        with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
            client = TestClient(app)
            resp = client.post(
                "/v1/downloads/jobs/job_123/export-formats",
                headers={"X-API-Key": "test_key_123"},
                json={"format_keys": ["nonexistent_platform"]},
            )
            assert resp.status_code == 400

    @patch("web_api.routes_downloads.get_job_by_id")
    def test_format_export_job_not_found(self, mock_job):
        from fastapi.testclient import TestClient
        from web_api.main import app

        mock_job.return_value = None
        with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
            client = TestClient(app)
            resp = client.post(
                "/v1/downloads/jobs/job_999/export-formats",
                headers={"X-API-Key": "test_key_123"},
                json={"format_keys": ["amazon_main"]},
            )
            assert resp.status_code == 404

    def test_format_export_empty_keys(self):
        from fastapi.testclient import TestClient
        from web_api.main import app

        with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
            client = TestClient(app)
            resp = client.post(
                "/v1/downloads/jobs/job_123/export-formats",
                headers={"X-API-Key": "test_key_123"},
                json={"format_keys": []},
            )
            assert resp.status_code == 422  # Pydantic validation (min_length=1)
