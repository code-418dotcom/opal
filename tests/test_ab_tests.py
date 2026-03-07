"""Tests for A/B testing routes and significance computation."""
import math
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from web_api.routes_ab_tests import _compute_significance, _normal_cdf


# ── Significance computation tests ───────────────────────────────────

def test_significance_insufficient_data():
    """Returns not confident when views < 10."""
    result = _compute_significance({
        "a": {"views": 5, "clicks": 3, "conversions": 1},
        "b": {"views": 8, "clicks": 4, "conversions": 2},
    })
    assert result["confident"] is False
    assert result["p_value"] is None
    assert result["recommended_winner"] is None
    assert "Not enough data" in result["message"]


def test_significance_empty_data():
    result = _compute_significance({})
    assert result["confident"] is False
    assert result["p_value"] is None


def test_significance_equal_rates():
    """Equal conversion rates → not significant."""
    result = _compute_significance({
        "a": {"views": 100, "conversions": 10},
        "b": {"views": 100, "conversions": 10},
    })
    assert result["confident"] is False
    assert result["p_value"] == 1.0
    assert result["conversion_rate_a"] == 10.0
    assert result["conversion_rate_b"] == 10.0


def test_significance_clear_winner():
    """Large difference in conversion rates → significant."""
    result = _compute_significance({
        "a": {"views": 1000, "conversions": 50},
        "b": {"views": 1000, "conversions": 100},
    })
    assert result["confident"] is True
    assert result["p_value"] is not None
    assert result["p_value"] < 0.05
    assert result["recommended_winner"] == "b"
    assert result["lift_percent"] is not None
    assert result["lift_percent"] > 0


def test_significance_a_wins():
    """When A has higher conversion, recommends A."""
    result = _compute_significance({
        "a": {"views": 1000, "conversions": 100},
        "b": {"views": 1000, "conversions": 50},
    })
    assert result["confident"] is True
    assert result["recommended_winner"] == "a"
    assert result["lift_percent"] < 0  # B is worse


def test_significance_zero_conversions():
    """Zero conversions both sides → no division error."""
    result = _compute_significance({
        "a": {"views": 100, "conversions": 0},
        "b": {"views": 100, "conversions": 0},
    })
    assert result["confident"] is False
    assert result["conversion_rate_a"] == 0.0
    assert result["conversion_rate_b"] == 0.0


def test_normal_cdf_values():
    """Normal CDF should return expected approximations."""
    assert abs(_normal_cdf(0) - 0.5) < 0.001
    assert _normal_cdf(3) > 0.99
    assert _normal_cdf(-3) < 0.01


# ── Model / validation tests ─────────────────────────────────────────

def test_create_body_validation():
    """CreateABTestIn validates required fields."""
    from web_api.routes_ab_tests import CreateABTestIn

    body = CreateABTestIn(
        integration_id="int_123",
        product_id="prod_456",
        variant_a_job_item_id="item_a",
        variant_b_job_item_id="item_b",
    )
    assert body.variant_a_label == "Variant A"
    assert body.variant_b_label == "Variant B"
    assert body.original_image_id is None


def test_conclude_body_validation():
    """ConcludeIn only accepts 'a' or 'b'."""
    from web_api.routes_ab_tests import ConcludeIn

    c = ConcludeIn(winner="a")
    assert c.winner == "a"

    c = ConcludeIn(winner="b")
    assert c.winner == "b"

    with pytest.raises(Exception):
        ConcludeIn(winner="c")


def test_metric_body_validation():
    """MetricIn validates variant pattern."""
    from web_api.routes_ab_tests import MetricIn

    m = MetricIn(variant="a", date="2025-01-01", views=100, clicks=50)
    assert m.conversions == 0
    assert m.revenue_cents == 0

    with pytest.raises(Exception):
        MetricIn(variant="x", date="2025-01-01")


# ── Route-level tests (with mocking) ──────────────────────────────────

@pytest.fixture
def app_client():
    """Create a TestClient with mocked auth."""
    from web_api.main import app
    with patch("web_api.routes_ab_tests.get_current_user", return_value={
        "user_id": "user_1",
        "tenant_id": "tenant_1",
        "email": "test@test.com",
        "token_balance": 100,
    }):
        yield TestClient(app)


def test_list_tests_empty(app_client):
    """GET /v1/ab-tests returns empty list when no tests exist."""
    with patch("web_api.routes_ab_tests.list_ab_tests", return_value=[]):
        resp = app_client.get("/v1/ab-tests")
        assert resp.status_code == 200
        assert resp.json()["tests"] == []


def test_get_test_not_found(app_client):
    """GET /v1/ab-tests/{id} returns 404 for missing test."""
    with patch("web_api.routes_ab_tests.get_ab_test", return_value=None):
        resp = app_client.get("/v1/ab-tests/nonexistent")
        assert resp.status_code == 404


def test_create_test_missing_integration(app_client):
    """POST /v1/ab-tests returns 404 when integration not found."""
    with patch("web_api.routes_ab_tests.get_integration", return_value=None):
        resp = app_client.post("/v1/ab-tests", json={
            "integration_id": "int_missing",
            "product_id": "prod_1",
            "variant_a_job_item_id": "item_a",
            "variant_b_job_item_id": "item_b",
        })
        assert resp.status_code == 404


def test_create_test_missing_variant_a(app_client):
    """POST /v1/ab-tests returns 400 when variant A job item not found."""
    with patch("web_api.routes_ab_tests.get_integration", return_value={"id": "int_1"}):
        with patch("web_api.routes_ab_tests.get_job_item", return_value=None):
            resp = app_client.post("/v1/ab-tests", json={
                "integration_id": "int_1",
                "product_id": "prod_1",
                "variant_a_job_item_id": "item_a",
                "variant_b_job_item_id": "item_b",
            })
            assert resp.status_code == 400
            assert "Variant A" in resp.json()["detail"]


def test_cancel_wrong_state(app_client):
    """POST /v1/ab-tests/{id}/cancel rejects concluded tests."""
    with patch("web_api.routes_ab_tests.get_ab_test", return_value={
        "id": "test_1",
        "status": "concluded",
    }):
        resp = app_client.post("/v1/ab-tests/test_1/cancel")
        assert resp.status_code == 400
        assert "Cannot cancel" in resp.json()["detail"]


def test_start_wrong_state(app_client):
    """POST /v1/ab-tests/{id}/start rejects running tests."""
    with patch("web_api.routes_ab_tests.get_ab_test", return_value={
        "id": "test_1",
        "status": "running",
    }):
        resp = app_client.post("/v1/ab-tests/test_1/start")
        assert resp.status_code == 400


def test_swap_not_running(app_client):
    """POST /v1/ab-tests/{id}/swap rejects non-running tests."""
    with patch("web_api.routes_ab_tests.get_ab_test", return_value={
        "id": "test_1",
        "status": "created",
    }):
        resp = app_client.post("/v1/ab-tests/test_1/swap")
        assert resp.status_code == 400
