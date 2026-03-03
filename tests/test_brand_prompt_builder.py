"""
Test the brand prompt building logic extracted from the orchestrator.

Since the orchestrator's process_message() has heavy infrastructure deps
(Service Bus, DB sessions), we test the prompt-building logic directly.
"""


def build_scene_prompt(brand_profile: dict) -> str:
    """
    Replicate the prompt-building logic from orchestrator/worker.py process_message().
    If this diverges from the real code, the test needs updating.
    """
    parts = []
    if brand_profile.get("default_scene_prompt"):
        parts.append(brand_profile["default_scene_prompt"])
    if brand_profile.get("style_keywords"):
        parts.append(", ".join(brand_profile["style_keywords"]))
    if brand_profile.get("mood"):
        parts.append(brand_profile["mood"])
    parts.append("photorealistic, high quality")
    return ", ".join(parts)


class TestBrandPromptBuilder:
    def test_full_profile(self):
        bp = {
            "default_scene_prompt": "luxury bathroom with marble",
            "style_keywords": ["minimalist", "Scandinavian"],
            "mood": "calm and serene",
        }
        prompt = build_scene_prompt(bp)
        assert "luxury bathroom with marble" in prompt
        assert "minimalist, Scandinavian" in prompt
        assert "calm and serene" in prompt
        assert "photorealistic, high quality" in prompt

    def test_prompt_only(self):
        bp = {"default_scene_prompt": "modern kitchen"}
        prompt = build_scene_prompt(bp)
        assert prompt == "modern kitchen, photorealistic, high quality"

    def test_empty_profile(self):
        bp = {}
        prompt = build_scene_prompt(bp)
        assert prompt == "photorealistic, high quality"

    def test_keywords_only(self):
        bp = {"style_keywords": ["dark", "moody"]}
        prompt = build_scene_prompt(bp)
        assert prompt == "dark, moody, photorealistic, high quality"

    def test_none_fields_ignored(self):
        bp = {
            "default_scene_prompt": None,
            "style_keywords": None,
            "mood": None,
        }
        prompt = build_scene_prompt(bp)
        assert prompt == "photorealistic, high quality"

    def test_empty_keywords_ignored(self):
        bp = {
            "default_scene_prompt": "outdoor patio",
            "style_keywords": [],
            "mood": "vibrant",
        }
        prompt = build_scene_prompt(bp)
        assert prompt == "outdoor patio, vibrant, photorealistic, high quality"
