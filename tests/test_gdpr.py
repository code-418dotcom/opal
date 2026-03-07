"""Tests for GDPR/AVG compliance endpoints."""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from web_api.main import app

client = TestClient(app)
AUTH = {"X-API-Key": "test_key_123"}


@pytest.fixture(autouse=True)
def _mock_auth():
    with patch("web_api.auth.get_valid_api_keys", return_value={"test_key_123"}):
        yield


# ── Privacy Info (public, no auth) ──────────────────────────────────

class TestPrivacyInfo:
    def test_privacy_info_no_auth_required(self):
        """GET /v1/privacy/info should work without authentication."""
        resp = client.get("/v1/privacy/info")
        assert resp.status_code == 200

    def test_privacy_info_contains_required_fields(self):
        resp = client.get("/v1/privacy/info")
        data = resp.json()
        assert "data_controller" in data
        assert "data_collected" in data
        assert "third_parties" in data
        assert "your_rights" in data
        assert "contact" in data
        assert "legal_basis" in data

    def test_privacy_info_lists_data_fields(self):
        resp = client.get("/v1/privacy/info")
        data = resp.json()
        field_names = [f["field"] for f in data["data_collected"]]
        assert "email" in field_names
        assert "product_images" in field_names

    def test_privacy_info_lists_third_parties(self):
        resp = client.get("/v1/privacy/info")
        data = resp.json()
        party_names = [p["name"] for p in data["third_parties"]]
        assert "Mollie" in party_names
        assert "Microsoft Entra" in party_names


# ── Data Export (GDPR Art. 15) ──────────────────────────────────────

class TestDataExport:
    @patch("web_api.routes_gdpr.export_user_data")
    def test_export_returns_user_data(self, mock_export):
        mock_export.return_value = {
            "user": {"user_id": "user_abc", "email": "test@example.com"},
            "jobs": [],
            "transactions": [],
        }
        resp = client.get("/v1/privacy/export", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data

    @patch("web_api.routes_gdpr.export_user_data")
    def test_export_no_data(self, mock_export):
        mock_export.return_value = None
        resp = client.get("/v1/privacy/export", headers=AUTH)
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"] == "No data found"

    def test_export_requires_auth(self):
        resp = client.get("/v1/privacy/export")
        assert resp.status_code in (401, 403)


# ── Account Deletion (GDPR Art. 17) ────────────────────────────────

class TestAccountDeletion:
    @patch("web_api.routes_gdpr.delete_blob")
    @patch("web_api.routes_gdpr.delete_user_data")
    def test_delete_account_success(self, mock_delete, mock_blob):
        mock_delete.return_value = {
            "deleted": True,
            "blob_paths": [("raw", "tenant/jobs/j1/items/i1/raw/file.jpg")],
        }
        mock_blob.return_value = True
        resp = client.post(
            "/v1/privacy/delete-account",
            headers=AUTH,
            json={"confirm": True},
        )
        # API key users ("apikey") are blocked from deletion
        assert resp.status_code == 400
        assert "system accounts" in resp.json()["detail"]

    @patch("web_api.routes_gdpr.delete_user_data")
    def test_delete_requires_confirm(self, mock_delete):
        resp = client.post(
            "/v1/privacy/delete-account",
            headers=AUTH,
            json={"confirm": False},
        )
        assert resp.status_code == 400
        assert "confirm" in resp.json()["detail"].lower()
        mock_delete.assert_not_called()

    def test_delete_requires_auth(self):
        resp = client.post("/v1/privacy/delete-account", json={"confirm": True})
        assert resp.status_code in (401, 403)

    @patch("web_api.routes_gdpr.delete_blob")
    @patch("web_api.routes_gdpr.delete_user_data")
    @patch("web_api.auth._resolve_jwt_user")
    def test_delete_account_as_jwt_user(self, mock_jwt, mock_delete, mock_blob):
        """A real JWT user (not apikey) should be able to delete their account."""
        mock_jwt.return_value = {
            "user_id": "user_real123",
            "tenant_id": "tenant_abc",
            "email": "user@example.com",
            "token_balance": 50,
            "is_admin": False,
        }
        mock_delete.return_value = {
            "deleted": True,
            "blob_paths": [("raw", "t/j/i/raw/f.jpg"), ("outputs", "t/j/i/outputs/f.jpg")],
        }
        mock_blob.return_value = True
        resp = client.post(
            "/v1/privacy/delete-account",
            headers={"Authorization": "Bearer fake_jwt_token"},
            json={"confirm": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["blobs_deleted"] == 2

    @patch("web_api.routes_gdpr.delete_user_data")
    @patch("web_api.auth._resolve_jwt_user")
    def test_delete_user_not_found(self, mock_jwt, mock_delete):
        mock_jwt.return_value = {
            "user_id": "user_gone",
            "tenant_id": "tenant_abc",
            "email": "gone@example.com",
            "token_balance": 0,
            "is_admin": False,
        }
        mock_delete.return_value = {"deleted": False}
        resp = client.post(
            "/v1/privacy/delete-account",
            headers={"Authorization": "Bearer fake_jwt_token"},
            json={"confirm": True},
        )
        assert resp.status_code == 404


# ── Shopify GDPR Webhooks ──────────────────────────────────────────

class TestShopifyGdprWebhooks:
    @patch("web_api.routes_integrations.verify_webhook_hmac", return_value=True)
    def test_customer_data_request(self, mock_hmac):
        resp = client.post(
            "/v1/integrations/shopify/webhooks/customers/data_request",
            content=json.dumps({"shop_domain": "test.myshopify.com"}),
            headers={"X-Shopify-Hmac-Sha256": "valid", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @patch("web_api.routes_integrations.verify_webhook_hmac", return_value=True)
    def test_customer_redact(self, mock_hmac):
        resp = client.post(
            "/v1/integrations/shopify/webhooks/customers/redact",
            content=json.dumps({"shop_domain": "test.myshopify.com", "customer": {"id": 123}}),
            headers={"X-Shopify-Hmac-Sha256": "valid", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200

    @patch("shared.db_sqlalchemy.delete_integrations_by_store", return_value=2)
    @patch("web_api.routes_integrations.verify_webhook_hmac", return_value=True)
    def test_shop_redact_deletes_integrations(self, mock_hmac, mock_delete):
        resp = client.post(
            "/v1/integrations/shopify/webhooks/shop/redact",
            content=json.dumps({"shop_domain": "closing.myshopify.com"}),
            headers={"X-Shopify-Hmac-Sha256": "valid", "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        mock_delete.assert_called_once_with("shopify", "closing.myshopify.com")

    @patch("web_api.routes_integrations.verify_webhook_hmac", return_value=False)
    def test_gdpr_webhook_rejects_invalid_hmac(self, mock_hmac):
        resp = client.post(
            "/v1/integrations/shopify/webhooks/customers/data_request",
            content=json.dumps({"shop_domain": "evil.myshopify.com"}),
            headers={"X-Shopify-Hmac-Sha256": "invalid"},
        )
        assert resp.status_code == 401


# ── PII Logging ────────────────────────────────────────────────────

class TestPiiLogging:
    def test_auth_logs_do_not_contain_email(self):
        """Verify auth.py log statements don't include email addresses."""
        import ast
        with open("src/web_api/web_api/auth.py") as f:
            source = f.read()

        # Check that LOG.info calls don't contain email variable interpolation
        # Look for patterns like: LOG.info("...", ..., email)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "info"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "LOG"):
                # Check all args after the format string
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Name) and arg.id == "email":
                        pytest.fail(f"LOG.info at line {node.lineno} logs email PII")
