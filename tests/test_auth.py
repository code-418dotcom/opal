"""Tests for authentication: API key validation, JIT provisioning, admin bootstrap."""
from collections import defaultdict
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from fastapi.testclient import TestClient


def _get_app():
    from web_api.main import app
    # Clear any dependency overrides so we test real auth
    app.dependency_overrides.clear()
    return app


class TestApiKeyAuth:
    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_valid_api_key(self, mock_settings):
        mock_settings.API_KEYS = "dev_testkey123"
        mock_settings.ENTRA_ISSUER = ""
        mock_settings.ENTRA_CLIENT_ID = ""
        mock_settings.ENTRA_TENANT_ID = ""

        app = _get_app()
        client = TestClient(app)

        with patch("web_api.routes_billing.list_token_packages", return_value=[]):
            # Public endpoint should work without auth
            resp = client.get("/v1/billing/packages")
            assert resp.status_code == 200

        with patch("web_api.routes_billing.get_user_by_id", return_value={"token_balance": 999999, "is_admin": True}):
            resp = client.get("/v1/billing/balance", headers={"X-API-Key": "dev_testkey123"})
            assert resp.status_code == 200

    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_invalid_api_key_403(self, mock_settings):
        mock_settings.API_KEYS = "dev_testkey123"
        mock_settings.ENTRA_ISSUER = ""
        mock_settings.ENTRA_CLIENT_ID = ""
        mock_settings.ENTRA_TENANT_ID = ""

        app = _get_app()
        client = TestClient(app)
        resp = client.get("/v1/billing/balance", headers={"X-API-Key": "wrong_key"})
        assert resp.status_code == 403

    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_no_auth_401(self, mock_settings):
        mock_settings.API_KEYS = "dev_testkey123"
        mock_settings.ENTRA_ISSUER = "https://issuer.example.com"
        mock_settings.ENTRA_CLIENT_ID = "client123"
        mock_settings.ENTRA_TENANT_ID = "tenant123"

        app = _get_app()
        client = TestClient(app)
        resp = client.get("/v1/billing/balance")
        assert resp.status_code == 401

    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_dev_mode_no_auth_configured(self, mock_settings):
        """When no API keys and no Entra config, allow anonymous access."""
        mock_settings.API_KEYS = ""
        mock_settings.ENTRA_ISSUER = ""
        mock_settings.ENTRA_CLIENT_ID = ""
        mock_settings.ENTRA_TENANT_ID = ""

        app = _get_app()
        client = TestClient(app)

        with patch("web_api.routes_billing.get_user_by_id", return_value={"token_balance": 999999, "is_admin": True}):
            resp = client.get("/v1/billing/balance")
            assert resp.status_code == 200

    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_api_key_extracts_tenant(self, mock_settings):
        mock_settings.API_KEYS = "acme_key456"
        mock_settings.ENTRA_ISSUER = ""
        mock_settings.ENTRA_CLIENT_ID = ""
        mock_settings.ENTRA_TENANT_ID = ""

        app = _get_app()
        client = TestClient(app)

        with patch("web_api.routes_brand_profiles.list_brand_profiles", return_value=[]) as mock_list:
            resp = client.get("/v1/brand-profiles", headers={"X-API-Key": "acme_key456"})
            assert resp.status_code == 200
            # Tenant should be extracted from key prefix
            mock_list.assert_called_once_with("acme")


class TestApiKeyUserProperties:
    def test_api_key_user_has_unlimited_tokens(self):
        from web_api.auth import _resolve_api_key_user
        with patch("web_api.auth.settings") as mock_settings:
            mock_settings.API_KEYS = "dev_testkey123"
            user = _resolve_api_key_user("dev_testkey123")
            assert user["token_balance"] == 999999
            assert user["user_id"] == "apikey"

    def test_invalid_key_raises(self):
        from web_api.auth import _resolve_api_key_user
        from fastapi import HTTPException
        with patch("web_api.auth.settings") as mock_settings:
            mock_settings.API_KEYS = "dev_testkey123"
            with pytest.raises(HTTPException) as exc_info:
                _resolve_api_key_user("wrong")
            assert exc_info.value.status_code == 403


class TestRateLimit:
    @patch("web_api.rate_limit._requests", defaultdict(list))
    @patch("web_api.auth.settings")
    def test_rate_limit_exceeded(self, mock_settings):
        mock_settings.API_KEYS = "dev_testkey123"
        mock_settings.ENTRA_ISSUER = ""
        mock_settings.ENTRA_CLIENT_ID = ""
        mock_settings.ENTRA_TENANT_ID = ""

        app = _get_app()
        client = TestClient(app)

        with patch("web_api.routes_billing.get_user_by_id", return_value={"token_balance": 999999, "is_admin": True}):
            # Make 60 requests (the limit)
            for _ in range(60):
                resp = client.get("/v1/billing/balance", headers={"X-API-Key": "dev_testkey123"})
                assert resp.status_code == 200

            # 61st should be rate limited
            resp = client.get("/v1/billing/balance", headers={"X-API-Key": "dev_testkey123"})
            assert resp.status_code == 429
