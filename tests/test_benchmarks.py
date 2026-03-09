"""Tests for benchmark routes."""
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from shared.image_scoring import score_image


def _make_png(w=800, h=800, color=(200, 200, 200)):
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestBenchmarkScoring:
    """Test scoring integration with different image qualities."""

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_high_quality_image_scores_well(self, _):
        image = _make_png(2048, 2048, (130, 130, 130))
        result = score_image(image, image_count=5, category="general")
        assert result["overall_score"] >= 70

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_low_quality_image_gets_suggestions(self, _):
        image = _make_png(300, 300, (30, 30, 30))
        result = score_image(image, image_count=1, category="general")
        assert result["overall_score"] < 60
        assert len(result["suggestions"]) > 0

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_image_count_affects_score(self, _):
        image = _make_png(1024, 1024)
        result_few = score_image(image, image_count=1)
        result_many = score_image(image, image_count=7)
        assert result_many["overall_score"] > result_few["overall_score"]

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_all_scores_between_0_and_100(self, _):
        image = _make_png(600, 900, (50, 200, 100))
        result = score_image(image, image_count=2)
        for metric, val in result["scores"].items():
            assert 0 <= val <= 100, f"{metric} = {val} out of range"

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_suggestion_priorities(self, _):
        image = _make_png(200, 200, (10, 10, 10))
        result = score_image(image, image_count=1)
        priorities = [s["priority"] for s in result["suggestions"]]
        # Should have at least one high-priority suggestion for this bad image
        assert "high" in priorities

    @patch("shared.image_scoring.get_setting", return_value="fake-key")
    @patch("shared.image_scoring._get_caption", return_value="product with watermark text logo")
    def test_text_penalty_with_caption(self, _caption, _setting):
        image = _make_png(1024, 1024)
        result = score_image(image)
        assert result["scores"]["text_penalty"] < 60

    @patch("shared.image_scoring.get_setting", return_value="fake-key")
    @patch("shared.image_scoring._get_caption", return_value="clean white background studio shot")
    def test_good_background_with_caption(self, _caption, _setting):
        image = _make_png(1024, 1024, (255, 255, 255))
        result = score_image(image)
        assert result["scores"]["background"] >= 80

    @patch("shared.image_scoring.get_setting", return_value="fake-key")
    @patch("shared.image_scoring._get_caption", side_effect=Exception("API error"))
    def test_fal_failure_falls_back(self, _caption, _setting):
        image = _make_png(1024, 1024)
        result = score_image(image)
        # Should still produce all scores even when API fails
        assert "background" in result["scores"]
        assert "text_penalty" in result["scores"]
        assert result["caption"] is None
