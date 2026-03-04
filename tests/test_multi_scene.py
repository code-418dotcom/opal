"""
Tests for multi-scene generation, orchestrator prompt priority, and export ZIP logic.
"""
from pathlib import PurePosixPath

from shared.scene_types import SCENE_PROMPTS, DEFAULT_SCENE_TYPES


# ---------------------------------------------------------------------------
# Orchestrator prompt priority (replicates logic from orchestrator/worker.py)
# ---------------------------------------------------------------------------

def resolve_orchestrator_prompt(
    item_scene_prompt: str | None,
    item_scene_type: str | None,
    brand_profile: dict | None,
) -> str | None:
    """
    Replicate the 4-level prompt resolution from orchestrator/worker.py:132-168.
    1. item.scene_prompt  (explicit per-item prompt)
    2. item.scene_type lookup from SCENE_PROMPTS + brand enhancement
    3. brand_profile default_scene_prompt + keywords + mood
    4. None (no prompt configured)
    """
    if item_scene_prompt:
        return item_scene_prompt

    if item_scene_type and item_scene_type in SCENE_PROMPTS:
        parts = [SCENE_PROMPTS[item_scene_type]]
        if brand_profile:
            if brand_profile.get("style_keywords"):
                parts.append(", ".join(brand_profile["style_keywords"]))
            if brand_profile.get("mood"):
                parts.append(brand_profile["mood"])
        parts.append("photorealistic, high quality")
        return ", ".join(parts)

    if brand_profile:
        parts = []
        if brand_profile.get("default_scene_prompt"):
            parts.append(brand_profile["default_scene_prompt"])
        if brand_profile.get("style_keywords"):
            parts.append(", ".join(brand_profile["style_keywords"]))
        if brand_profile.get("mood"):
            parts.append(brand_profile["mood"])
        parts.append("photorealistic, high quality")
        return ", ".join(parts)

    return None


class TestOrchestratorPromptPriority:
    def test_item_scene_prompt_wins(self):
        """Level 1: explicit item prompt overrides everything."""
        result = resolve_orchestrator_prompt(
            item_scene_prompt="custom dark loft scene",
            item_scene_type="studio",
            brand_profile={"default_scene_prompt": "should not appear"},
        )
        assert result == "custom dark loft scene"

    def test_scene_type_lookup(self):
        """Level 2: scene_type resolved from SCENE_PROMPTS."""
        result = resolve_orchestrator_prompt(
            item_scene_prompt=None,
            item_scene_type="studio",
            brand_profile=None,
        )
        assert SCENE_PROMPTS["studio"] in result
        assert "photorealistic, high quality" in result

    def test_scene_type_with_brand_enhancement(self):
        """Level 2: scene_type + brand keywords/mood appended."""
        bp = {"style_keywords": ["minimalist", "Scandinavian"], "mood": "calm"}
        result = resolve_orchestrator_prompt(
            item_scene_prompt=None,
            item_scene_type="lifestyle",
            brand_profile=bp,
        )
        assert SCENE_PROMPTS["lifestyle"] in result
        assert "minimalist, Scandinavian" in result
        assert "calm" in result

    def test_brand_profile_fallback(self):
        """Level 3: brand profile prompt when no item prompt or scene type."""
        bp = {
            "default_scene_prompt": "luxury bathroom",
            "style_keywords": ["modern"],
            "mood": "serene",
        }
        result = resolve_orchestrator_prompt(
            item_scene_prompt=None,
            item_scene_type=None,
            brand_profile=bp,
        )
        assert "luxury bathroom" in result
        assert "modern" in result
        assert "serene" in result

    def test_none_when_nothing_configured(self):
        """Level 4: returns None when nothing is set."""
        result = resolve_orchestrator_prompt(
            item_scene_prompt=None,
            item_scene_type=None,
            brand_profile=None,
        )
        assert result is None

    def test_unknown_scene_type_falls_through(self):
        """Unknown scene_type not in SCENE_PROMPTS falls to brand profile."""
        bp = {"default_scene_prompt": "fallback scene"}
        result = resolve_orchestrator_prompt(
            item_scene_prompt=None,
            item_scene_type="nonexistent_type",
            brand_profile=bp,
        )
        assert "fallback scene" in result

    def test_empty_string_scene_prompt_is_falsy(self):
        """Empty string scene_prompt should fall through (falsy)."""
        result = resolve_orchestrator_prompt(
            item_scene_prompt="",
            item_scene_type="studio",
            brand_profile=None,
        )
        assert SCENE_PROMPTS["studio"] in result


# ---------------------------------------------------------------------------
# Multi-scene item creation fan-out (replicates routes_jobs.py:69-102)
# ---------------------------------------------------------------------------

def fan_out_items(filename: str, scene_count: int, scene_types: list[str] | None, scene_prompt: str | None):
    """Replicate the item fan-out logic from routes_jobs.py create_job."""
    if scene_types and len(scene_types) != scene_count:
        raise ValueError(
            f"scene_types length ({len(scene_types)}) must equal scene_count ({scene_count})"
        )

    items = []
    for scene_idx in range(scene_count):
        scene_type = None
        if scene_count > 1:
            if scene_types:
                scene_type = scene_types[scene_idx]
            else:
                scene_type = DEFAULT_SCENE_TYPES[scene_idx % len(DEFAULT_SCENE_TYPES)]

        items.append({
            "filename": filename,
            "scene_prompt": scene_prompt,
            "scene_index": scene_idx if scene_count > 1 else None,
            "scene_type": scene_type,
        })
    return items


class TestMultiSceneItemCreation:
    def test_single_scene_no_index(self):
        items = fan_out_items("product.png", scene_count=1, scene_types=None, scene_prompt=None)
        assert len(items) == 1
        assert items[0]["scene_index"] is None
        assert items[0]["scene_type"] is None

    def test_multi_scene_with_explicit_types(self):
        types = ["studio", "lifestyle", "outdoor"]
        items = fan_out_items("product.png", scene_count=3, scene_types=types, scene_prompt=None)
        assert len(items) == 3
        for i, t in enumerate(types):
            assert items[i]["scene_index"] == i
            assert items[i]["scene_type"] == t

    def test_multi_scene_default_types(self):
        items = fan_out_items("product.png", scene_count=2, scene_types=None, scene_prompt=None)
        assert len(items) == 2
        assert items[0]["scene_type"] == DEFAULT_SCENE_TYPES[0]
        assert items[1]["scene_type"] == DEFAULT_SCENE_TYPES[1]

    def test_scene_types_length_mismatch_raises(self):
        import pytest
        with pytest.raises(ValueError, match="scene_types length"):
            fan_out_items("product.png", scene_count=2, scene_types=["studio"], scene_prompt=None)

    def test_scene_prompt_propagates_to_all_siblings(self):
        items = fan_out_items("product.png", scene_count=3, scene_types=None, scene_prompt="custom prompt")
        assert all(it["scene_prompt"] == "custom prompt" for it in items)

    def test_default_types_wrap_around(self):
        """When scene_count > len(DEFAULT_SCENE_TYPES), types wrap via modulo."""
        count = len(DEFAULT_SCENE_TYPES) + 2
        items = fan_out_items("product.png", scene_count=count, scene_types=None, scene_prompt=None)
        assert items[-1]["scene_type"] == DEFAULT_SCENE_TYPES[1]
        assert items[-2]["scene_type"] == DEFAULT_SCENE_TYPES[0]


# ---------------------------------------------------------------------------
# Export worker ZIP filename logic (tests _build_zip_filename directly)
# ---------------------------------------------------------------------------

class _FakeItem:
    """Minimal stand-in for JobItem with only the fields _build_zip_filename needs."""
    def __init__(self, filename: str, scene_index: int | None = None, scene_type: str | None = None):
        self.filename = filename
        self.scene_index = scene_index
        self.scene_type = scene_type


def build_zip_filename(item) -> str:
    """Replicate _build_zip_filename from export_worker/worker.py."""
    stem = PurePosixPath(item.filename).stem
    suffix = PurePosixPath(item.filename).suffix or ".png"
    if item.scene_index is not None:
        label = item.scene_type or f"scene{item.scene_index}"
        return f"{stem}_{label}{suffix}"
    return f"{stem}{suffix}"


class TestExportZipFilename:
    def test_single_item_no_scene(self):
        item = _FakeItem("product.png")
        assert build_zip_filename(item) == "product.png"

    def test_multi_scene_with_type(self):
        item = _FakeItem("product.png", scene_index=0, scene_type="studio")
        assert build_zip_filename(item) == "product_studio.png"

    def test_multi_scene_without_type(self):
        item = _FakeItem("product.png", scene_index=2, scene_type=None)
        assert build_zip_filename(item) == "product_scene2.png"

    def test_preserves_original_extension(self):
        item = _FakeItem("photo.jpg", scene_index=1, scene_type="lifestyle")
        assert build_zip_filename(item) == "photo_lifestyle.jpg"

    def test_no_extension_defaults_to_png(self):
        item = _FakeItem("photo", scene_index=0, scene_type="outdoor")
        assert build_zip_filename(item) == "photo_outdoor.png"

    def test_scene_index_zero_is_not_none(self):
        """scene_index=0 should still trigger the label (not be treated as falsy)."""
        item = _FakeItem("product.png", scene_index=0, scene_type="minimal")
        assert build_zip_filename(item) == "product_minimal.png"
