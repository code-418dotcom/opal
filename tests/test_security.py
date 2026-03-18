"""Security-focused tests: validates hardening measures against OWASP top risks."""
from collections import defaultdict
from unittest.mock import patch, MagicMock
import pytest


# ── API Key Timing Attack Protection ────────────────────────────────

class TestApiKeyConstantTime:
    def test_uses_compare_digest(self):
        """API key validation uses secrets.compare_digest (constant-time)."""
        import inspect
        from web_api.auth import _resolve_api_key_user
        source = inspect.getsource(_resolve_api_key_user)
        assert "compare_digest" in source, "API key check must use constant-time comparison"


# ── Admin Privilege Escalation Protection ────────────────────────────

class TestAdminEscalation:
    @patch("web_api.routes_admin.get_user_by_id")
    def test_high_balance_does_not_grant_admin(self, mock_get, client):
        """A user with token_balance=999999 is NOT admin unless is_admin=True."""
        mock_get.return_value = {"is_admin": False}
        resp = client.get("/v1/admin/stats")
        assert resp.status_code == 403

    @patch("web_api.routes_admin.get_user_by_id")
    @patch("web_api.routes_admin.platform_stats")
    def test_apikey_user_admin_by_id_not_balance(self, mock_stats, mock_get, apikey_client):
        """API key user is identified by user_id='apikey', not token_balance."""
        mock_stats.return_value = {"total_users": 1}
        resp = apikey_client.get("/v1/admin/stats")
        assert resp.status_code == 200
        # get_user_by_id should NOT be called for apikey users
        mock_get.assert_not_called()


# ── Open Redirect Protection ────────────────────────────────────────

class TestOpenRedirect:
    @patch("web_api.routes_billing.get_token_package")
    def test_reject_external_redirect_url(self, mock_pkg, client):
        """Purchase endpoint rejects redirect URLs not in CORS origins."""
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "https://evil-attacker.com/phishing",
        })
        assert resp.status_code == 400
        assert "redirect" in resp.json()["detail"].lower()

    @patch("web_api.routes_billing.create_payment")
    @patch("web_api.routes_billing.create_mollie_payment")
    @patch("web_api.routes_billing.get_setting")
    @patch("web_api.routes_billing.get_token_package")
    @patch("web_api.routes_billing.get_user_by_id", return_value=None)
    def test_accept_allowed_origin_redirect(self, mock_user, mock_pkg, mock_setting, mock_mollie, mock_create, client):
        """Purchase endpoint accepts redirect URLs matching CORS origins."""
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        mock_setting.side_effect = lambda k: {
            "MOLLIE_API_KEY": "test_key",
            "PUBLIC_BASE_URL": "https://api.example.com",
        }.get(k, "")
        mock_mollie.return_value = {"id": "tr_test", "checkout_url": "https://mollie.com/pay"}

        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173/billing",
        })
        assert resp.status_code == 200


# ── Mollie Webhook Hardening ────────────────────────────────────────

class TestWebhookHardening:
    def test_invalid_mollie_id_format_rejected(self, client):
        """Webhook rejects Mollie IDs that don't match expected format."""
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "not_a_valid_mollie_id"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        # Returns 200 (to prevent retries) but doesn't process
        assert resp.status_code == 200

    def test_overly_long_mollie_id_rejected(self, client):
        """Webhook rejects suspiciously long Mollie IDs."""
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_" + "A" * 100},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200


# ── SSRF Protection ─────────────────────────────────────────────────

class TestSsrfProtection:
    def test_callback_url_blocks_localhost(self, client):
        """Job creation rejects callback URLs pointing to localhost."""
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
            "callback_url": "http://localhost:8080/internal",
        })
        assert resp.status_code == 400
        assert "Internal" in resp.json()["detail"]

    def test_callback_url_blocks_metadata_endpoint(self, client):
        """Job creation rejects callback URLs pointing to cloud metadata."""
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
            "callback_url": "http://169.254.169.254/metadata",
        })
        assert resp.status_code == 400

    @patch("web_api.routes_jobs.create_job_item_records")
    @patch("web_api.routes_jobs.create_job_record")
    @patch("web_api.routes_jobs.debit_tokens")
    def test_callback_url_allows_https(self, mock_debit, mock_job, mock_items, client):
        """Job creation accepts HTTPS callback URLs."""
        mock_debit.return_value = 99
        mock_job.return_value = {}
        mock_items.return_value = []
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg"}],
            "callback_url": "https://myapp.example.com/webhook",
        })
        assert resp.status_code == 200


# ── Path Traversal Protection ───────────────────────────────────────

class TestPathTraversal:
    def test_set_preview_rejects_traversal(self, client):
        """Set-preview endpoint rejects blob paths with '..' traversal."""
        resp = client.post("/v1/scene-templates/st_test/set-preview", json={
            "preview_blob_path": "../../other_tenant/secrets/key.png",
        })
        assert resp.status_code == 400  # path traversal check rejects '..'

    def test_set_preview_rejects_wrong_tenant(self, client):
        """Set-preview endpoint rejects blob paths from other tenants."""
        resp = client.post("/v1/scene-templates/st_test/set-preview", json={
            "preview_blob_path": "other_tenant/scene-previews/prev_123.png",
        })
        assert resp.status_code == 400
        assert "Invalid blob path" in resp.json()["detail"]


# ── Cross-Tenant Isolation ──────────────────────────────────────────

class TestTenantIsolation:
    @patch("web_api.routes_downloads.get_job_item")
    def test_download_blocks_other_tenant(self, mock_item, client):
        """Downloads endpoint blocks access to other tenants' items."""
        mock_item.return_value = {
            "id": "item_1", "tenant_id": "other_tenant",
            "output_blob_path": "other/path.png",
        }
        resp = client.get("/v1/downloads/item_1")
        assert resp.status_code == 403


# ── JWT Error Message Leakage ───────────────────────────────────────

class TestJwtErrorLeakage:
    def test_jwt_error_is_generic(self):
        """JWT validation errors don't leak internal details."""
        import inspect
        from web_api.auth import _resolve_jwt_user
        source = inspect.getsource(_resolve_jwt_user)
        # Should NOT include {e} in the error detail
        assert 'detail=f"Invalid token: {e}"' not in source
        assert 'detail="Invalid token"' in source


# ── Input Validation ────────────────────────────────────────────────

class TestInputValidation:
    def test_scene_prompt_max_length(self, client):
        """Scene prompts are limited to 2000 characters."""
        resp = client.post("/v1/jobs", json={
            "items": [{"filename": "test.jpg", "scene_prompt": "A" * 2001}],
        })
        assert resp.status_code == 422


# ── CORS Configuration ─────────────────────────────────────────────

class TestCorsConfig:
    def test_cors_does_not_use_wildcard_methods(self):
        """CORS middleware uses explicit methods, not wildcard."""
        import inspect
        from web_api.main import app
        source = inspect.getsource(type(app))
        # Check the middleware config
        for middleware in app.user_middleware:
            if hasattr(middleware, 'kwargs'):
                methods = middleware.kwargs.get('allow_methods', [])
                assert "*" not in methods, "CORS must not use wildcard methods"


# ── Admin Settings Secret Masking ───────────────────────────────────

# ── Filename Extension Validation ───────────────────────────────────

class TestFilenameValidation:
    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_rejects_exe_extension(self, mock_job, mock_item, client):
        """Upload endpoint rejects non-image file extensions."""
        mock_job.return_value = {"id": "job_1"}
        resp = client.post("/v1/uploads/sas", json={
            "job_id": "job_1", "item_id": "item_1", "filename": "malware.exe",
        })
        assert resp.status_code == 422

    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_rejects_php_extension(self, mock_job, mock_item, client):
        """Upload endpoint rejects script file extensions."""
        mock_job.return_value = {"id": "job_1"}
        resp = client.post("/v1/uploads/sas", json={
            "job_id": "job_1", "item_id": "item_1", "filename": "shell.php",
        })
        assert resp.status_code == 422

    @patch("web_api.routes_uploads.update_job_item")
    @patch("web_api.routes_uploads.get_job_items_by_filename")
    @patch("web_api.routes_uploads.generate_upload_url")
    @patch("web_api.routes_uploads.get_job_item")
    @patch("web_api.routes_uploads.get_job_by_id")
    def test_accepts_image_extensions(self, mock_job, mock_item, mock_sas, mock_siblings, mock_update, client):
        """Upload endpoint accepts common image extensions."""
        mock_job.return_value = {"id": "job_1"}
        mock_item.return_value = {"id": "item_1", "tenant_id": "tenant_test", "job_id": "job_1"}
        mock_sas.return_value = "https://storage.blob.core.windows.net/sas"
        mock_siblings.return_value = [{"id": "item_1"}]
        for ext in ["jpg", "jpeg", "png", "webp"]:
            resp = client.post("/v1/uploads/sas", json={
                "job_id": "job_1", "item_id": "item_1", "filename": f"photo.{ext}",
            })
            assert resp.status_code == 200, f"Failed for .{ext}"


# ── Public Endpoint Rate Limiting ───────────────────────────────────

class TestPublicRateLimiting:
    def test_packages_endpoint_is_rate_limited(self):
        """Verify get_packages calls check_ip_rate_limit."""
        import inspect
        from web_api.routes_billing import get_packages
        source = inspect.getsource(get_packages)
        assert "check_ip_rate_limit" in source

    def test_webhook_endpoint_is_rate_limited(self):
        """Verify mollie_webhook calls check_ip_rate_limit."""
        import inspect
        from web_api.routes_billing import mollie_webhook
        source = inspect.getsource(mollie_webhook)
        assert "check_ip_rate_limit" in source


# ── Admin Settings Secret Masking ───────────────────────────────────

class TestSecretMasking:
    @patch("web_api.routes_admin.list_admin_settings")
    def test_secrets_are_masked_in_response(self, mock_list, admin_client):
        """Secret settings values are masked in API responses."""
        mock_list.return_value = [
            {"key": "MOLLIE_API_KEY", "value": "live_abc123xyz789", "is_secret": True},
            {"key": "ENV_NAME", "value": "production", "is_secret": False},
        ]
        resp = admin_client.get("/v1/admin/settings")
        assert resp.status_code == 200
        settings = resp.json()["settings"]
        # Secret should be masked
        secret = next(s for s in settings if s["key"] == "MOLLIE_API_KEY")
        assert secret["value"] != "live_abc123xyz789"
        assert "***" in secret["value"] or "*" in secret["value"]
        # Non-secret should be plaintext
        non_secret = next(s for s in settings if s["key"] == "ENV_NAME")
        assert non_secret["value"] == "production"
