"""Tests for SEO metadata generation."""
import io
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from shared.seo_metadata import (
    generate_seo_metadata,
    _generate_fallback,
    _caption_to_filename,
    _build_alt_text,
)


def _make_test_image() -> bytes:
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestFallbackGeneration:
    def test_basic_filename(self):
        result = _generate_fallback("blue-mug.jpg", None, None)
        assert "blue" in result["alt_text"].lower()
        assert "mug" in result["alt_text"].lower()
        assert result["seo_filename"].endswith(".jpg")

    def test_with_brand_name(self):
        result = _generate_fallback("product.jpg", "Opal Studio", None)
        assert "Opal Studio" in result["alt_text"]

    def test_with_category(self):
        result = _generate_fallback("item.jpg", None, "Jewelry & Accessories")
        assert "Jewelry" in result["alt_text"]

    def test_with_brand_and_category(self):
        result = _generate_fallback("ring.jpg", "Luna", "Jewelry & Accessories")
        assert "Luna" in result["alt_text"]
        assert "Jewelry" in result["alt_text"]

    def test_strips_common_prefixes(self):
        result = _generate_fallback("shopify_12345_67890.jpg", None, None)
        assert "shopify" not in result["alt_text"].lower()

    def test_alt_text_max_length(self):
        result = _generate_fallback("a" * 200 + ".jpg", None, None)
        assert len(result["alt_text"]) <= 125

    def test_default_brand_ignored(self):
        result = _generate_fallback("mug.jpg", "default", None)
        assert "default" not in result["alt_text"]


class TestCaptionToFilename:
    def test_basic(self):
        result = _caption_to_filename("A blue ceramic mug on a marble surface")
        assert result == "a-blue-ceramic-mug-on-a-marble-surface.jpg"

    def test_strips_special_chars(self):
        result = _caption_to_filename("A beautiful, hand-crafted item!")
        assert "," not in result
        assert "!" not in result

    def test_max_words(self):
        long_caption = " ".join(["word"] * 20)
        result = _caption_to_filename(long_caption)
        # Should only have 8 words
        assert result.count("-") <= 7

    def test_empty_caption(self):
        result = _caption_to_filename("")
        assert result == "product-image.jpg"


class TestBuildAltText:
    def test_basic(self):
        result = _build_alt_text("A modern ceramic mug.", None, None)
        assert "ceramic mug" in result

    def test_with_brand(self):
        result = _build_alt_text("A blue mug.", "ArtCo", None)
        assert "ArtCo" in result

    def test_max_length(self):
        long_caption = "word " * 100
        result = _build_alt_text(long_caption, "BrandName", "Category")
        assert len(result) <= 125


class TestGenerateSeoMetadata:
    @patch("shared.seo_metadata.get_setting", return_value="")
    def test_uses_fallback_when_no_api_key(self, mock_setting):
        img = _make_test_image()
        result = generate_seo_metadata(img, "blue-mug.jpg")
        assert "alt_text" in result
        assert "seo_filename" in result
        assert result["seo_filename"].endswith(".jpg")

    @patch("shared.seo_metadata.get_setting", return_value="fake_key")
    @patch("shared.seo_metadata._generate_with_fal")
    def test_uses_fal_when_key_present(self, mock_fal, mock_setting):
        mock_fal.return_value = {"alt_text": "AI generated alt", "seo_filename": "ai-image.jpg"}
        img = _make_test_image()
        result = generate_seo_metadata(img, "test.jpg")
        assert result["alt_text"] == "AI generated alt"
        mock_fal.assert_called_once()

    @patch("shared.seo_metadata.get_setting", return_value="fake_key")
    @patch("shared.seo_metadata._generate_with_fal", side_effect=Exception("API error"))
    def test_falls_back_on_api_error(self, mock_fal, mock_setting):
        img = _make_test_image()
        result = generate_seo_metadata(img, "test-product.jpg")
        # Should fall back to rule-based generation
        assert "alt_text" in result
        assert result["seo_filename"].endswith(".jpg")
