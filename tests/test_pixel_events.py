"""Tests for pixel event ingestion, variant attribution, auto-conclude, and pixel key generation."""
import math
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from web_api.routes_pixel_events import (
    _compute_significance_quick,
    _check_auto_conclude_batch,
    PixelEvent,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def pixel_client():
    """TestClient with no auth override (pixel endpoint is public)."""
    from web_api.main import app
    from web_api.auth import get_current_user

    async def _mock_user():
        return {
            "user_id": "user_1",
            "tenant_id": "tenant_1",
            "email": "test@test.com",
            "token_balance": 100,
        }

    app.dependency_overrides[get_current_user] = _mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


MOCK_INTEGRATION = {
    "id": "int_abc",
    "user_id": "user_1",
    "provider": "shopify",
    "store_url": "test-store.myshopify.com",
    "status": "active",
    "pixel_key": "pk_test_key_123",
}

MOCK_RUNNING_TEST = {
    "id": "abtest_001",
    "user_id": "user_1",
    "integration_id": "int_abc",
    "product_id": "12345",
    "active_variant": "a",
    "status": "running",
    "tracking_mode": "pixel",
    "auto_conclude": False,
}


# ── Pixel event ingestion ────────────────────────────────────────────

def test_pixel_events_valid_key(pixel_client):
    """Valid pixel key + events → 202 with accepted count."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None), \
         patch("web_api.routes_pixel_events.find_running_test", return_value=MOCK_RUNNING_TEST), \
         patch("web_api.routes_pixel_events.get_active_variant_at", return_value="a"), \
         patch("web_api.routes_pixel_events.increment_ab_test_metric") as mock_inc:

        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {
                    "event_type": "view",
                    "product_id": "12345",
                    "timestamp": "2026-03-12T20:00:00Z",
                },
                {
                    "event_type": "conversion",
                    "product_id": "12345",
                    "timestamp": "2026-03-12T20:05:00Z",
                    "revenue_cents": 1990,
                },
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted"] == 2
        assert mock_inc.call_count == 2

        # First call: view — only views=1 is passed
        call1 = mock_inc.call_args_list[0]
        assert call1.kwargs.get("views", 0) == 1

        # Second call: conversion with revenue
        call2 = mock_inc.call_args_list[1]
        assert call2.kwargs.get("conversions", 0) == 1
        assert call2.kwargs.get("revenue_cents", 0) == 1990


def test_pixel_events_invalid_key(pixel_client):
    """Invalid pixel key → 401."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=None):
        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "view", "product_id": "12345", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "bad_key"})

        assert resp.status_code == 401
        assert "Invalid pixel key" in resp.json()["detail"]


def test_pixel_events_empty_batch(pixel_client):
    """Empty events list → 202 with 0 accepted."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None):
        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        assert resp.json()["accepted"] == 0


def test_pixel_events_no_running_test(pixel_client):
    """Events for a product with no running test → skipped."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None), \
         patch("web_api.routes_pixel_events.find_running_test", return_value=None), \
         patch("web_api.routes_pixel_events.increment_ab_test_metric") as mock_inc:

        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "view", "product_id": "99999", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        assert resp.json()["accepted"] == 0
        assert resp.json()["skipped"] == 1
        mock_inc.assert_not_called()


def test_pixel_events_missing_header(pixel_client):
    """Missing X-Pixel-Key header → 422."""
    resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
        "shop_domain": "test-store.myshopify.com",
        "events": [],
    })
    assert resp.status_code == 422


def test_pixel_events_add_to_cart(pixel_client):
    """add_to_cart event type increments correct metric."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None), \
         patch("web_api.routes_pixel_events.find_running_test", return_value=MOCK_RUNNING_TEST), \
         patch("web_api.routes_pixel_events.get_active_variant_at", return_value="b"), \
         patch("web_api.routes_pixel_events.increment_ab_test_metric") as mock_inc:

        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "add_to_cart", "product_id": "12345", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        call = mock_inc.call_args_list[0]
        assert call.kwargs.get("add_to_carts", 0) == 1
        # Second positional arg is variant (from get_active_variant_at returning "b")
        assert call.args[1] == "b"


# ── Variant attribution ──────────────────────────────────────────────

def test_variant_attribution_uses_log(pixel_client):
    """Events are attributed to variant from variant_log, not active_variant."""
    # Test where active_variant is 'a' but variant_log says 'b' at event time
    test_with_a_active = {**MOCK_RUNNING_TEST, "active_variant": "a"}

    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None), \
         patch("web_api.routes_pixel_events.find_running_test", return_value=test_with_a_active), \
         patch("web_api.routes_pixel_events.get_active_variant_at", return_value="b"), \
         patch("web_api.routes_pixel_events.increment_ab_test_metric") as mock_inc:

        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "view", "product_id": "12345", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        # Should use variant from log ('b'), not active_variant ('a')
        call = mock_inc.call_args_list[0]
        assert call.args[1] == "b"


def test_variant_attribution_fallback(pixel_client):
    """When no variant_log entry exists, falls back to active_variant."""
    test_with_b_active = {**MOCK_RUNNING_TEST, "active_variant": "b"}

    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION), \
         patch("web_api.routes_pixel_events.get_integration_event_limit", return_value=None), \
         patch("web_api.routes_pixel_events.find_running_test", return_value=test_with_b_active), \
         patch("web_api.routes_pixel_events.get_active_variant_at", return_value=None), \
         patch("web_api.routes_pixel_events.increment_ab_test_metric") as mock_inc:

        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "view", "product_id": "12345", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})

        assert resp.status_code == 202
        call = mock_inc.call_args_list[0]
        assert call.args[1] == "b"


# ── Auto-conclude logic ──────────────────────────────────────────────

def test_auto_conclude_triggers_when_significant():
    """Auto-conclude concludes a test when significance >= 95% and views >= 200."""
    test_auto = {**MOCK_RUNNING_TEST, "auto_conclude": True, "tracking_mode": "pixel"}
    aggregated = {
        "a": {"views": 500, "clicks": 0, "add_to_carts": 0, "conversions": 25, "revenue_cents": 0},
        "b": {"views": 500, "clicks": 0, "add_to_carts": 0, "conversions": 75, "revenue_cents": 0},
    }

    events = [PixelEvent(event_type="view", product_id="12345", timestamp="2026-03-12T20:00:00Z")]

    with patch("web_api.routes_pixel_events.find_running_test", return_value=test_auto), \
         patch("web_api.routes_pixel_events.get_ab_test_aggregated_metrics", return_value=aggregated), \
         patch("web_api.routes_pixel_events.update_ab_test") as mock_update:

        _check_auto_conclude_batch("int_abc", events)

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == "abtest_001"
        updates = call_args[0][1]
        assert updates["status"] == "concluded"
        assert updates["winner"] == "b"


def test_auto_conclude_skips_when_not_enough_views():
    """Auto-conclude does not trigger when total views < 200."""
    test_auto = {**MOCK_RUNNING_TEST, "auto_conclude": True, "tracking_mode": "pixel"}
    aggregated = {
        "a": {"views": 50, "clicks": 0, "add_to_carts": 0, "conversions": 5, "revenue_cents": 0},
        "b": {"views": 50, "clicks": 0, "add_to_carts": 0, "conversions": 15, "revenue_cents": 0},
    }

    events = [PixelEvent(event_type="view", product_id="12345", timestamp="2026-03-12T20:00:00Z")]

    with patch("web_api.routes_pixel_events.find_running_test", return_value=test_auto), \
         patch("web_api.routes_pixel_events.get_ab_test_aggregated_metrics", return_value=aggregated), \
         patch("web_api.routes_pixel_events.update_ab_test") as mock_update:

        _check_auto_conclude_batch("int_abc", events)
        mock_update.assert_not_called()


def test_auto_conclude_skips_when_not_significant():
    """Auto-conclude does not trigger when results are not statistically significant."""
    test_auto = {**MOCK_RUNNING_TEST, "auto_conclude": True, "tracking_mode": "pixel"}
    # Equal conversion rates = not significant
    aggregated = {
        "a": {"views": 200, "clicks": 0, "add_to_carts": 0, "conversions": 20, "revenue_cents": 0},
        "b": {"views": 200, "clicks": 0, "add_to_carts": 0, "conversions": 20, "revenue_cents": 0},
    }

    events = [PixelEvent(event_type="view", product_id="12345", timestamp="2026-03-12T20:00:00Z")]

    with patch("web_api.routes_pixel_events.find_running_test", return_value=test_auto), \
         patch("web_api.routes_pixel_events.get_ab_test_aggregated_metrics", return_value=aggregated), \
         patch("web_api.routes_pixel_events.update_ab_test") as mock_update:

        _check_auto_conclude_batch("int_abc", events)
        mock_update.assert_not_called()


def test_auto_conclude_skips_when_disabled():
    """Auto-conclude does not trigger when auto_conclude is False."""
    test_no_auto = {**MOCK_RUNNING_TEST, "auto_conclude": False}
    events = [PixelEvent(event_type="view", product_id="12345", timestamp="2026-03-12T20:00:00Z")]

    with patch("web_api.routes_pixel_events.find_running_test", return_value=test_no_auto), \
         patch("web_api.routes_pixel_events.get_ab_test_aggregated_metrics") as mock_agg, \
         patch("web_api.routes_pixel_events.update_ab_test") as mock_update:

        _check_auto_conclude_batch("int_abc", events)
        # Should not even check metrics when auto_conclude is off
        mock_agg.assert_not_called()
        mock_update.assert_not_called()


# ── Significance quick computation ───────────────────────────────────

def test_significance_quick_insufficient_data():
    """Returns not confident when views < 10."""
    result = _compute_significance_quick({
        "a": {"views": 5, "conversions": 1},
        "b": {"views": 8, "conversions": 2},
    })
    assert result["confident"] is False


def test_significance_quick_clear_winner():
    """Large difference → significant with recommended winner."""
    result = _compute_significance_quick({
        "a": {"views": 1000, "conversions": 50},
        "b": {"views": 1000, "conversions": 100},
    })
    assert result["confident"] is True
    assert result["recommended_winner"] == "b"
    assert result["p_value"] < 0.05


def test_significance_quick_equal_rates():
    """Equal rates → not significant."""
    result = _compute_significance_quick({
        "a": {"views": 100, "conversions": 10},
        "b": {"views": 100, "conversions": 10},
    })
    assert result["confident"] is False


# ── Pixel key generation ─────────────────────────────────────────────

def test_pixel_key_get(pixel_client):
    """GET /pixel-key/{id} returns a pixel key."""
    with patch("web_api.routes_pixel_events.get_integration", return_value={"id": "int_abc"}), \
         patch("web_api.routes_pixel_events.ensure_pixel_key", return_value="pk_generated_key_42"):

        resp = pixel_client.get("/v1/ab-tests/pixel-key/int_abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pixel_key"] == "pk_generated_key_42"
        assert data["integration_id"] == "int_abc"


def test_pixel_key_not_found(pixel_client):
    """GET /pixel-key/{id} returns 404 for missing integration."""
    with patch("web_api.routes_pixel_events.get_integration", return_value=None):
        resp = pixel_client.get("/v1/ab-tests/pixel-key/int_missing")
        assert resp.status_code == 404


# ── Event type validation ────────────────────────────────────────────

def test_pixel_event_invalid_type(pixel_client):
    """Invalid event_type is rejected by Pydantic."""
    with patch("web_api.routes_pixel_events.get_integration_by_pixel_key", return_value=MOCK_INTEGRATION):
        resp = pixel_client.post("/v1/ab-tests/pixel-events", json={
            "shop_domain": "test-store.myshopify.com",
            "events": [
                {"event_type": "invalid_type", "product_id": "12345", "timestamp": "2026-03-12T20:00:00Z"},
            ],
        }, headers={"X-Pixel-Key": "pk_test_key_123"})
        assert resp.status_code == 422
