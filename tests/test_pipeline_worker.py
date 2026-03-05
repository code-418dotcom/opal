"""
Tests for the unified pipeline worker: pipeline execution, error classification, retry behavior.
"""
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

import httpx

from pipeline_worker.retry import TransientError, PermanentError, classify_and_raise
from pipeline_worker.pipeline import execute_pipeline, PipelineResult, composite_product_on_scene


# ---------------------------------------------------------------------------
# Helper: minimal valid PNG bytes (1x1 red pixel)
# ---------------------------------------------------------------------------
def _make_png(r=255, g=0, b=0):
    import struct, zlib
    raw_pixel = b"\x00" + bytes([r, g, b])
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_pixel))
        + chunk(b"IEND", b"")
    )


def _make_rgba_png():
    """Create a 2x2 RGBA PNG for compositing tests."""
    from io import BytesIO
    from PIL import Image
    img = Image.new('RGBA', (2, 2), (255, 0, 0, 128))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


RAW_PNG = _make_png()
RGBA_PNG = _make_rgba_png()


# ---------------------------------------------------------------------------
# 1. Error Classification
# ---------------------------------------------------------------------------

class TestErrorClassification:
    def test_timeout_is_transient(self):
        with pytest.raises(TransientError):
            classify_and_raise(httpx.ReadTimeout("timed out"))

    def test_http_400_is_permanent(self):
        resp = httpx.Response(400, request=httpx.Request("GET", "http://x"))
        with pytest.raises(PermanentError, match="HTTP 400"):
            classify_and_raise(httpx.HTTPStatusError("bad", request=resp.request, response=resp))

    def test_http_500_is_transient(self):
        resp = httpx.Response(500, request=httpx.Request("GET", "http://x"))
        with pytest.raises(TransientError, match="HTTP 500"):
            classify_and_raise(httpx.HTTPStatusError("err", request=resp.request, response=resp))

    def test_http_429_is_transient(self):
        resp = httpx.Response(429, request=httpx.Request("GET", "http://x"))
        with pytest.raises(TransientError, match="HTTP 429"):
            classify_and_raise(httpx.HTTPStatusError("rate", request=resp.request, response=resp))

    def test_value_error_is_permanent(self):
        with pytest.raises(PermanentError):
            classify_and_raise(ValueError("bad data"))

    def test_connection_error_is_transient(self):
        with pytest.raises(TransientError):
            classify_and_raise(ConnectionError("refused"))

    def test_unknown_error_defaults_transient(self):
        with pytest.raises(TransientError):
            classify_and_raise(RuntimeError("mystery"))

    def test_already_classified_passthrough(self):
        with pytest.raises(PermanentError, match="already"):
            classify_and_raise(PermanentError("already"))
        with pytest.raises(TransientError, match="already"):
            classify_and_raise(TransientError("already"))


# ---------------------------------------------------------------------------
# 2. Pipeline Step Sequencing
# ---------------------------------------------------------------------------

class TestPipelineSequencing:
    def _make_providers(self):
        bg = MagicMock()
        bg.name = "mock-bg"
        bg.remove_background.return_value = b"bg_removed"

        scene = MagicMock()
        scene.name = "mock-scene"
        scene.generate.return_value = RGBA_PNG  # valid image for compositing

        upscale = MagicMock()
        upscale.name = "mock-upscale"
        upscale.upscale.return_value = b"upscaled"

        return bg, scene, upscale

    def test_all_steps_enabled(self):
        bg, scene, upscale = self._make_providers()
        # bg returns valid PNG for scene compositing
        bg.remove_background.return_value = RGBA_PNG

        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=True, generate_scene=True, upscale=True,
            scene_prompt="test prompt",
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )

        bg.remove_background.assert_called_once_with(RAW_PNG)
        scene.generate.assert_called_once_with("test prompt")
        upscale.upscale.assert_called_once()
        assert result.output_bytes == b"upscaled"

    def test_only_bg_removal(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=True, generate_scene=False, upscale=False,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        bg.remove_background.assert_called_once()
        scene.generate.assert_not_called()
        upscale.upscale.assert_not_called()
        assert result.output_bytes == b"bg_removed"

    def test_only_scene_gen(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RGBA_PNG,
            remove_background=False, generate_scene=True, upscale=False,
            scene_prompt="my prompt",
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        bg.remove_background.assert_not_called()
        scene.generate.assert_called_once_with("my prompt")
        upscale.upscale.assert_not_called()
        # Result is composited PNG bytes
        assert len(result.output_bytes) > 0

    def test_only_upscale(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=False, generate_scene=False, upscale=True,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        bg.remove_background.assert_not_called()
        scene.generate.assert_not_called()
        upscale.upscale.assert_called_once_with(RAW_PNG)
        assert result.output_bytes == b"upscaled"

    def test_passthrough_all_disabled(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=False, generate_scene=False, upscale=False,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        bg.remove_background.assert_not_called()
        scene.generate.assert_not_called()
        upscale.upscale.assert_not_called()
        assert result.output_bytes == RAW_PNG

    def test_bg_plus_upscale_no_scene(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=True, generate_scene=False, upscale=True,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        bg.remove_background.assert_called_once_with(RAW_PNG)
        scene.generate.assert_not_called()
        upscale.upscale.assert_called_once_with(b"bg_removed")

    def test_no_provider_skips_step(self):
        """If provider is None, step is skipped even if enabled."""
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=True, generate_scene=True, upscale=True,
            scene_prompt="test",
            bg_provider=None, img_gen_provider=None, upscale_provider=None,
        )
        assert result.output_bytes == RAW_PNG

    def test_upscale_disabled_via_setting(self):
        bg, scene, upscale = self._make_providers()
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=False, generate_scene=False, upscale=True,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
            upscale_enabled=False,
        )
        upscale.upscale.assert_not_called()
        assert result.output_bytes == RAW_PNG

    def test_default_prompt_used_when_none(self):
        bg, scene, upscale = self._make_providers()
        execute_pipeline(
            raw_bytes=RGBA_PNG,
            remove_background=False, generate_scene=True, upscale=False,
            scene_prompt=None,
            bg_provider=bg, img_gen_provider=scene, upscale_provider=upscale,
        )
        call_args = scene.generate.call_args[0][0]
        assert "bare scene" in call_args


# ---------------------------------------------------------------------------
# 3. Retry Behavior
# ---------------------------------------------------------------------------

class TestRetryBehavior:
    def test_transient_error_retried(self):
        """Pipeline retries on transient errors up to 3 times."""
        bg = MagicMock()
        bg.name = "mock-bg"
        bg.remove_background.side_effect = [
            ConnectionError("network"),
            b"bg_done",
        ]

        # The retry wraps classify_and_raise which converts ConnectionError -> TransientError
        # but execute_pipeline catches via _run_step. Since _run_step calls classify_and_raise
        # which raises TransientError, and execute_pipeline has @retry for TransientError,
        # the second call should succeed.
        result = execute_pipeline(
            raw_bytes=RAW_PNG,
            remove_background=True, generate_scene=False, upscale=False,
            scene_prompt=None,
            bg_provider=bg,
        )
        assert result.output_bytes == b"bg_done"
        assert bg.remove_background.call_count == 2

    def test_permanent_error_not_retried(self):
        """Pipeline does NOT retry on permanent errors."""
        bg = MagicMock()
        bg.name = "mock-bg"
        bg.remove_background.side_effect = ValueError("invalid image format")

        with pytest.raises(PermanentError):
            execute_pipeline(
                raw_bytes=RAW_PNG,
                remove_background=True, generate_scene=False, upscale=False,
                scene_prompt=None,
                bg_provider=bg,
            )
        assert bg.remove_background.call_count == 1


# ---------------------------------------------------------------------------
# 4. Compositing
# ---------------------------------------------------------------------------

class TestCompositing:
    def test_composite_produces_valid_png(self):
        from PIL import Image
        from io import BytesIO

        product = _make_rgba_png()
        scene = _make_rgba_png()

        result = composite_product_on_scene(product, scene)
        img = Image.open(BytesIO(result))
        assert img.format == 'PNG'
        assert img.size[0] > 0 and img.size[1] > 0
