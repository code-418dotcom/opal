"""
Tests for brand profiles, scene templates, and "use saved background" pipeline mode.
"""
from unittest.mock import MagicMock
from io import BytesIO

from PIL import Image

from shared.scene_types import SCENE_PROMPTS, DEFAULT_SCENE_TYPES
from pipeline_worker.pipeline import execute_pipeline, composite_product_on_scene


# ---------------------------------------------------------------------------
# Helper: minimal valid image bytes
# ---------------------------------------------------------------------------
def _make_rgba_png(w=4, h=4, color=(255, 0, 0, 128)):
    img = Image.new('RGBA', (w, h), color)
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _make_rgb_jpg(w=4, h=4, color=(0, 128, 255)):
    img = Image.new('RGB', (w, h), color)
    buf = BytesIO()
    img.save(buf, format='JPEG')
    return buf.getvalue()


PRODUCT_PNG = _make_rgba_png()
SCENE_BG = _make_rgba_png(64, 64, (200, 200, 200, 255))
SAVED_BG_JPG = _make_rgb_jpg(64, 64)


# ---------------------------------------------------------------------------
# 1. Scene template fan-out (replicates routes_jobs.py template mode)
# ---------------------------------------------------------------------------

def fan_out_from_templates(filename, templates, use_saved_background):
    """Replicate the scene_template_ids fan-out from routes_jobs.py."""
    items = []
    for scene_idx, tmpl in enumerate(templates):
        saved_bg = tmpl.get("preview_blob_path") if use_saved_background else None
        items.append({
            "filename": filename,
            "scene_prompt": tmpl["prompt"],
            "scene_index": scene_idx if len(templates) > 1 else None,
            "scene_type": tmpl.get("scene_type"),
            "saved_background_path": saved_bg,
        })
    return items


class TestSceneTemplateFanOut:
    def test_single_template_no_index(self):
        templates = [{"prompt": "modern kitchen", "scene_type": "studio"}]
        items = fan_out_from_templates("prod.png", templates, use_saved_background=False)
        assert len(items) == 1
        assert items[0]["scene_index"] is None
        assert items[0]["scene_prompt"] == "modern kitchen"
        assert items[0]["saved_background_path"] is None

    def test_multiple_templates_indexed(self):
        templates = [
            {"prompt": "kitchen", "scene_type": "studio"},
            {"prompt": "garden", "scene_type": "outdoor"},
            {"prompt": "office", "scene_type": "lifestyle"},
        ]
        items = fan_out_from_templates("prod.png", templates, use_saved_background=False)
        assert len(items) == 3
        for i, tmpl in enumerate(templates):
            assert items[i]["scene_index"] == i
            assert items[i]["scene_prompt"] == tmpl["prompt"]
            assert items[i]["scene_type"] == tmpl["scene_type"]

    def test_saved_background_path_from_preview(self):
        templates = [
            {"prompt": "kitchen", "preview_blob_path": "previews/abc.png"},
        ]
        items = fan_out_from_templates("prod.png", templates, use_saved_background=True)
        assert items[0]["saved_background_path"] == "previews/abc.png"

    def test_saved_background_disabled(self):
        templates = [
            {"prompt": "kitchen", "preview_blob_path": "previews/abc.png"},
        ]
        items = fan_out_from_templates("prod.png", templates, use_saved_background=False)
        assert items[0]["saved_background_path"] is None

    def test_template_without_preview_path(self):
        templates = [{"prompt": "garden"}]
        items = fan_out_from_templates("prod.png", templates, use_saved_background=True)
        assert items[0]["saved_background_path"] is None


# ---------------------------------------------------------------------------
# 2. Brand profile defaults (replicates routes_jobs.py brand default logic)
# ---------------------------------------------------------------------------

def apply_brand_defaults(scene_count, scene_types, brand_profile):
    """Replicate brand default logic from routes_jobs.py."""
    if brand_profile and scene_count == 1 and not scene_types:
        if brand_profile.get("default_scene_count") and brand_profile["default_scene_count"] > 1:
            scene_count = brand_profile["default_scene_count"]
        if brand_profile.get("default_scene_types"):
            scene_types = brand_profile["default_scene_types"]
    return scene_count, scene_types


class TestBrandProfileDefaults:
    def test_no_brand_keeps_original(self):
        count, types = apply_brand_defaults(1, None, None)
        assert count == 1
        assert types is None

    def test_brand_sets_scene_count(self):
        bp = {"default_scene_count": 3}
        count, types = apply_brand_defaults(1, None, bp)
        assert count == 3

    def test_brand_sets_scene_types(self):
        bp = {"default_scene_count": 2, "default_scene_types": ["studio", "outdoor"]}
        count, types = apply_brand_defaults(1, None, bp)
        assert count == 2
        assert types == ["studio", "outdoor"]

    def test_explicit_scene_count_overrides_brand(self):
        """If user explicitly sets scene_count > 1, brand defaults don't apply."""
        bp = {"default_scene_count": 5, "default_scene_types": ["studio"] * 5}
        count, types = apply_brand_defaults(3, None, bp)
        # scene_count != 1 so brand defaults not applied
        assert count == 3
        assert types is None

    def test_explicit_scene_types_overrides_brand(self):
        bp = {"default_scene_count": 2, "default_scene_types": ["studio", "outdoor"]}
        count, types = apply_brand_defaults(1, ["lifestyle"], bp)
        # scene_types already set so brand defaults not applied
        assert count == 1
        assert types == ["lifestyle"]

    def test_brand_without_defaults_keeps_original(self):
        bp = {"name": "Test Brand"}
        count, types = apply_brand_defaults(1, None, bp)
        assert count == 1
        assert types is None


# ---------------------------------------------------------------------------
# 3. Pipeline: saved background compositing
# ---------------------------------------------------------------------------

class TestSavedBackgroundPipeline:
    def _make_providers(self):
        bg = MagicMock()
        bg.name = "mock-bg"
        bg.remove_background.return_value = PRODUCT_PNG

        scene = MagicMock()
        scene.name = "mock-scene"
        scene.generate.return_value = SCENE_BG

        upscale = MagicMock()
        upscale.name = "mock-upscale"
        upscale.upscale.return_value = b"upscaled"

        return bg, scene, upscale

    def test_saved_background_skips_generation(self):
        """When saved_background_bytes is provided, scene generation is skipped."""
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=PRODUCT_PNG,
            remove_background=True, generate_scene=True, upscale=False,
            scene_prompt="should not be used",
            bg_provider=bg, img_gen_provider=scene, upscale_provider=None,
            saved_background_bytes=SCENE_BG,
        )
        # Scene generate should NOT be called since saved background is provided
        scene.generate.assert_not_called()
        # Result should be composited bytes (not raw)
        assert len(result.output_bytes) > 0
        assert result.output_bytes != PRODUCT_PNG

    def test_saved_background_composites_correctly(self):
        """Saved background produces valid PNG output."""
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=PRODUCT_PNG,
            remove_background=True, generate_scene=True, upscale=False,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=None,
            saved_background_bytes=SCENE_BG,
        )
        img = Image.open(BytesIO(result.output_bytes))
        assert img.format == 'PNG'
        assert img.size[0] > 0

    def test_no_saved_background_uses_generation(self):
        """Without saved background, normal scene generation occurs."""
        bg, scene, upscale = self._make_providers()
        execute_pipeline(
            raw_bytes=PRODUCT_PNG,
            remove_background=True, generate_scene=True, upscale=False,
            scene_prompt="test prompt",
            bg_provider=bg, img_gen_provider=scene, upscale_provider=None,
            saved_background_bytes=None,
        )
        scene.generate.assert_called_once_with("test prompt")

    def test_saved_background_with_upscale(self):
        """Saved background composites then upscales."""
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=PRODUCT_PNG,
            remove_background=True, generate_scene=True, upscale=True,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
            saved_background_bytes=SCENE_BG,
        )
        scene.generate.assert_not_called()
        upscale.upscale.assert_called_once()
        assert result.output_bytes == b"upscaled"

    def test_generate_scene_false_ignores_saved_background(self):
        """If generate_scene=False, saved_background_bytes is ignored."""
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=PRODUCT_PNG,
            remove_background=False, generate_scene=False, upscale=False,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=None,
            saved_background_bytes=SCENE_BG,
        )
        scene.generate.assert_not_called()
        # No compositing, raw bytes pass through
        assert result.output_bytes == PRODUCT_PNG

    def test_compositing_product_on_saved_background(self):
        """Direct test of composite_product_on_scene with saved background."""
        result = composite_product_on_scene(PRODUCT_PNG, SCENE_BG)
        img = Image.open(BytesIO(result))
        assert img.format == 'PNG'
        assert img.mode == 'RGB'
        assert img.size == (64, 64)  # scene dimensions preserved
