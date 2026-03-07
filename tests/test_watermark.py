"""Tests for watermark functionality."""
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image


# ── watermark.py unit tests ──


def _make_test_image(width=200, height=200) -> bytes:
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_apply_watermark_returns_png():
    from shared.watermark import apply_watermark

    raw = _make_test_image()
    result = apply_watermark(raw)
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


def test_apply_watermark_preserves_dimensions():
    from shared.watermark import apply_watermark

    raw = _make_test_image(300, 400)
    result = apply_watermark(raw)
    img = Image.open(io.BytesIO(result))
    assert img.size == (300, 400)


def test_apply_watermark_modifies_image():
    from shared.watermark import apply_watermark

    raw = _make_test_image()
    result = apply_watermark(raw)
    assert raw != result


def test_apply_watermark_custom_text():
    from shared.watermark import apply_watermark

    raw = _make_test_image()
    result = apply_watermark(raw, text="TEST MARK")
    assert isinstance(result, bytes)
    img = Image.open(io.BytesIO(result))
    assert img.size == (200, 200)


def test_apply_watermark_small_image():
    from shared.watermark import apply_watermark

    raw = _make_test_image(50, 50)
    result = apply_watermark(raw)
    img = Image.open(io.BytesIO(result))
    assert img.size == (50, 50)


# ── _should_watermark logic tests ──


def _mock_session_with_user(mock_user):
    """Helper to create a mock SessionLocal context manager returning mock_user."""
    mock_s = MagicMock()
    mock_s.query.return_value.filter.return_value.first.return_value = mock_user
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_s)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


def test_should_watermark_no_user_returns_false():
    """Unknown tenant (e.g. API key user) should not be watermarked."""
    from pipeline_worker.worker import _should_watermark

    mock_ctx = _mock_session_with_user(None)
    with patch("pipeline_worker.worker.SessionLocal", return_value=mock_ctx):
        assert _should_watermark({"tenant_id": "unknown"}) is False


def test_should_watermark_user_with_balance_returns_false():
    """User with positive token balance should not be watermarked."""
    from pipeline_worker.worker import _should_watermark

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.token_balance = 50

    mock_ctx = _mock_session_with_user(mock_user)
    with patch("pipeline_worker.worker.SessionLocal", return_value=mock_ctx), \
         patch("pipeline_worker.worker.get_user_subscription", return_value=None):
        assert _should_watermark({"tenant_id": "tenant-123"}) is False


def test_should_watermark_user_with_subscription_returns_false():
    """User with active subscription should not be watermarked."""
    from pipeline_worker.worker import _should_watermark

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.token_balance = 0

    mock_ctx = _mock_session_with_user(mock_user)
    with patch("pipeline_worker.worker.SessionLocal", return_value=mock_ctx), \
         patch("pipeline_worker.worker.get_user_subscription", return_value={"status": "active"}):
        assert _should_watermark({"tenant_id": "tenant-123"}) is False


def test_should_watermark_free_tier_user_returns_true():
    """User with no subscription and zero balance should be watermarked."""
    from pipeline_worker.worker import _should_watermark

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.token_balance = 0

    mock_ctx = _mock_session_with_user(mock_user)
    with patch("pipeline_worker.worker.SessionLocal", return_value=mock_ctx), \
         patch("pipeline_worker.worker.get_user_subscription", return_value=None):
        assert _should_watermark({"tenant_id": "tenant-123"}) is True


def test_should_watermark_pending_subscription_returns_true():
    """User with pending (not active) subscription should be watermarked."""
    from pipeline_worker.worker import _should_watermark

    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.token_balance = 0

    mock_ctx = _mock_session_with_user(mock_user)
    with patch("pipeline_worker.worker.SessionLocal", return_value=mock_ctx), \
         patch("pipeline_worker.worker.get_user_subscription", return_value={"status": "pending"}):
        assert _should_watermark({"tenant_id": "tenant-123"}) is True


def test_should_watermark_exception_returns_false():
    """If anything fails during the check, don't watermark (safe default)."""
    from pipeline_worker.worker import _should_watermark

    with patch("pipeline_worker.worker.SessionLocal", side_effect=Exception("db error")):
        assert _should_watermark({"tenant_id": "tenant-123"}) is False
