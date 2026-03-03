"""Regression tests for PipelineMessage — ensure scene_prompt is carried through."""
import json
from shared.pipeline import PipelineMessage, ProcessingOptions


def _base_dict(**overrides):
    d = {
        "job_id": "job_1",
        "item_id": "item_1",
        "tenant_id": "t1",
        "correlation_id": "corr_1",
        "raw_blob_path": "t1/jobs/job_1/items/item_1/raw/img.png",
    }
    d.update(overrides)
    return d


class TestPipelineMessageScenePrompt:
    def test_scene_prompt_round_trips_through_dict(self):
        prompt = "luxury bathroom, marble surfaces, warm light"
        msg = PipelineMessage.from_dict(_base_dict(scene_prompt=prompt))
        assert msg.scene_prompt == prompt
        d = msg.to_dict()
        assert d["scene_prompt"] == prompt
        msg2 = PipelineMessage.from_dict(d)
        assert msg2.scene_prompt == prompt

    def test_scene_prompt_round_trips_through_json(self):
        prompt = "dark moody kitchen, slate countertops"
        msg = PipelineMessage(**_base_dict(), scene_prompt=prompt)
        j = msg.to_json()
        msg2 = PipelineMessage.from_json(j)
        assert msg2.scene_prompt == prompt

    def test_missing_scene_prompt_defaults_to_none(self):
        """Backward compat: old messages without scene_prompt still parse."""
        msg = PipelineMessage.from_dict(_base_dict())
        assert msg.scene_prompt is None

    def test_none_scene_prompt_serializes(self):
        msg = PipelineMessage.from_dict(_base_dict())
        d = msg.to_dict()
        assert "scene_prompt" in d
        assert d["scene_prompt"] is None


class TestProcessingOptions:
    def test_defaults(self):
        opts = ProcessingOptions()
        assert opts.remove_background is True
        assert opts.generate_scene is True
        assert opts.upscale is True

    def test_from_empty_dict(self):
        opts = ProcessingOptions.from_dict({})
        assert opts.remove_background is True

    def test_round_trip(self):
        opts = ProcessingOptions(remove_background=False, generate_scene=True, upscale=False)
        d = opts.to_dict()
        opts2 = ProcessingOptions.from_dict(d)
        assert opts2.remove_background is False
        assert opts2.upscale is False


class TestBestAvailableBlob:
    def test_raw_only(self):
        msg = PipelineMessage.from_dict(_base_dict())
        container, path = msg.best_available_blob()
        assert container == "raw"

    def test_bg_removed_preferred(self):
        msg = PipelineMessage.from_dict(_base_dict(bg_removed_blob_path="out/bg.png"))
        container, path = msg.best_available_blob()
        assert container == "outputs"
        assert path == "out/bg.png"

    def test_scene_preferred_over_bg(self):
        msg = PipelineMessage.from_dict(
            _base_dict(bg_removed_blob_path="out/bg.png", scene_blob_path="out/scene.png")
        )
        container, path = msg.best_available_blob()
        assert path == "out/scene.png"
