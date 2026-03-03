"""Test that scene worker uses scene_prompt from message with correct fallback."""
from shared.pipeline import PipelineMessage

HARDCODED_FALLBACK = (
    "modern minimalist living room, bright natural lighting, "
    "wooden floor, white walls, plants, photorealistic, high quality"
)


def resolve_prompt(msg: PipelineMessage) -> str:
    """Replicate the one-liner from scene_worker/worker.py line ~140."""
    return msg.scene_prompt or HARDCODED_FALLBACK


class TestSceneWorkerPromptResolution:
    def test_custom_prompt_used(self):
        msg = PipelineMessage(
            job_id="j1", item_id="i1", tenant_id="t1",
            correlation_id="c1", raw_blob_path="r.png",
            scene_prompt="dark industrial loft, concrete walls",
        )
        assert resolve_prompt(msg) == "dark industrial loft, concrete walls"

    def test_fallback_when_none(self):
        msg = PipelineMessage(
            job_id="j1", item_id="i1", tenant_id="t1",
            correlation_id="c1", raw_blob_path="r.png",
        )
        assert resolve_prompt(msg) == HARDCODED_FALLBACK

    def test_fallback_when_empty_string(self):
        msg = PipelineMessage(
            job_id="j1", item_id="i1", tenant_id="t1",
            correlation_id="c1", raw_blob_path="r.png",
            scene_prompt="",
        )
        assert resolve_prompt(msg) == HARDCODED_FALLBACK
