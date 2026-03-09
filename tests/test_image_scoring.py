"""Tests for image quality scoring."""
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from shared.image_scoring import (
    score_image,
    _score_resolution,
    _score_lighting,
    _score_composition,
    _score_image_count,
    _score_background_heuristic,
    _score_text_penalty,
    _generate_suggestions,
)


def _make_image(width=1024, height=1024, color=(128, 128, 128)):
    """Create a test image as bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), img


class TestScoreResolution:
    def test_high_res(self):
        _, img = _make_image(2048, 2048)
        assert _score_resolution(img) == 100

    def test_medium_res(self):
        _, img = _make_image(1200, 1200)
        assert 65 <= _score_resolution(img) <= 75

    def test_low_res(self):
        _, img = _make_image(400, 400)
        assert _score_resolution(img) < 30

    def test_above_best(self):
        _, img = _make_image(4096, 4096)
        assert _score_resolution(img) == 100

    def test_rectangular(self):
        _, img = _make_image(2048, 800)
        # Min dimension is 800, scores in lower-mid range
        score = _score_resolution(img)
        assert 30 <= score <= 70


class TestScoreLighting:
    def test_well_lit(self):
        _, img = _make_image(500, 500, (130, 130, 130))
        score = _score_lighting(img)
        assert score >= 60

    def test_too_dark(self):
        _, img = _make_image(500, 500, (30, 30, 30))
        score = _score_lighting(img)
        assert score < 60

    def test_too_bright(self):
        _, img = _make_image(500, 500, (250, 250, 250))
        score = _score_lighting(img)
        assert score < 70


class TestScoreComposition:
    def test_square(self):
        _, img = _make_image(1000, 1000)
        score = _score_composition(img)
        assert score >= 60

    def test_very_wide(self):
        _, img = _make_image(3000, 500)
        score = _score_composition(img)
        assert score < 70


class TestScoreImageCount:
    def test_many_images(self):
        assert _score_image_count(7) == 100

    def test_few_images(self):
        assert _score_image_count(1) == 25

    def test_medium_images(self):
        assert 60 <= _score_image_count(4) <= 70


class TestScoreBackgroundHeuristic:
    def test_white_background(self):
        _, img = _make_image(500, 500, (255, 255, 255))
        score = _score_background_heuristic(img)
        assert score >= 90

    def test_solid_color(self):
        _, img = _make_image(500, 500, (100, 100, 200))
        score = _score_background_heuristic(img)
        assert score >= 80


class TestScoreTextPenalty:
    def test_no_text(self):
        assert _score_text_penalty("A red shoe on a white background") == 100

    def test_watermark(self):
        assert _score_text_penalty("A shoe with watermark text overlay") < 80

    def test_multiple_text_elements(self):
        assert _score_text_penalty("Image with text, watermark, and logo") < 60


class TestGenerateSuggestions:
    def test_low_resolution_suggestion(self):
        scores = {"resolution": 40, "background": 90, "lighting": 80, "composition": 70, "text_penalty": 90, "image_count": 80}
        suggestions = _generate_suggestions(scores, "general")
        actions = [s["action"] for s in suggestions]
        assert "upscale" in actions

    def test_bad_background_suggestion(self):
        scores = {"resolution": 90, "background": 30, "lighting": 80, "composition": 70, "text_penalty": 90, "image_count": 80}
        suggestions = _generate_suggestions(scores, "general")
        actions = [s["action"] for s in suggestions]
        assert "remove_bg" in actions

    def test_low_image_count_suggestion(self):
        scores = {"resolution": 90, "background": 90, "lighting": 80, "composition": 70, "text_penalty": 90, "image_count": 25}
        suggestions = _generate_suggestions(scores, "general")
        actions = [s["action"] for s in suggestions]
        assert "multi_angle" in actions

    def test_all_good_no_suggestions(self):
        scores = {"resolution": 90, "background": 90, "lighting": 80, "composition": 70, "text_penalty": 90, "image_count": 80}
        suggestions = _generate_suggestions(scores, "general")
        assert len(suggestions) == 0


class TestScoreImage:
    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_returns_all_metrics(self, _mock):
        image_bytes, _ = _make_image(1024, 1024)
        result = score_image(image_bytes, image_count=3, category="general")

        assert "scores" in result
        assert "overall_score" in result
        assert "suggestions" in result
        assert 0 <= result["overall_score"] <= 100

        expected_metrics = {"resolution", "lighting", "composition", "background", "text_penalty", "image_count"}
        assert set(result["scores"].keys()) == expected_metrics

    @patch("shared.image_scoring.get_setting", return_value=None)
    def test_no_fal_key_uses_heuristic(self, _mock):
        image_bytes, _ = _make_image(500, 500)
        result = score_image(image_bytes)
        # Without FAL key, should still produce all scores
        assert result["caption"] is None
        assert "background" in result["scores"]

    @patch("shared.image_scoring.get_setting", return_value="fake-key")
    @patch("shared.image_scoring._get_caption", return_value="A red shoe on a white background")
    def test_with_fal_key_uses_caption(self, _mock_caption, _mock_setting):
        image_bytes, _ = _make_image(1024, 1024)
        result = score_image(image_bytes)
        assert result["caption"] == "A red shoe on a white background"
