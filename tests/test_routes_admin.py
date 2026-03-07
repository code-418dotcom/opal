"""Tests for admin routes: settings, users, packages, stats, system."""
from unittest.mock import patch
import pytest



# ── Admin Access Control ──────────────────────────────────────────

class TestAdminAuth:
    @patch("web_api.routes_admin.get_user_by_id")
    def test_non_admin_gets_403(self, mock_get, client):
        """Normal users are blocked from admin endpoints."""
        mock_get.return_value = {"is_admin": False}
        resp = client.get("/v1/admin/stats")
        assert resp.status_code == 403

    @patch("web_api.routes_admin.platform_stats")
    def test_admin_user_passes(self, mock_stats, admin_client):
        mock_stats.return_value = {"total_users": 1}
        resp = admin_client.get("/v1/admin/stats")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.platform_stats")
    def test_apikey_user_is_admin(self, mock_stats, apikey_client):
        """API key users (user_id=apikey) bypass admin check."""
        mock_stats.return_value = {"total_users": 1}
        resp = apikey_client.get("/v1/admin/stats")
        assert resp.status_code == 200


# ── GET /v1/admin/stats ───────────────────────────────────────────

class TestPlatformStats:
    @patch("web_api.routes_admin.platform_stats")
    def test_returns_stats(self, mock_stats, admin_client):
        mock_stats.return_value = {
            "total_users": 5, "total_jobs": 100,
            "total_tokens_sold": 5000, "total_revenue_cents": 49500,
        }
        resp = admin_client.get("/v1/admin/stats")
        assert resp.status_code == 200
        assert resp.json()["total_users"] == 5


# ── Settings CRUD ─────────────────────────────────────────────────

class TestSettingsManagement:
    @patch("web_api.routes_admin.list_admin_settings")
    def test_list_settings(self, mock_list, admin_client):
        mock_list.return_value = [
            {"key": "FAL_API_KEY", "value": "***", "category": "providers", "is_secret": True},
        ]
        resp = admin_client.get("/v1/admin/settings")
        assert resp.status_code == 200
        assert len(resp.json()["settings"]) == 1

    @patch("web_api.routes_admin.list_admin_settings")
    def test_list_settings_by_category(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/settings?category=providers")
        assert resp.status_code == 200
        mock_list.assert_called_once_with(category="providers")

    @patch("web_api.routes_admin.upsert_admin_setting")
    def test_update_setting(self, mock_upsert, admin_client):
        mock_upsert.return_value = {"key": "FAL_API_KEY", "value": "***"}
        resp = admin_client.put("/v1/admin/settings/FAL_API_KEY", json={"value": "new_key"})
        assert resp.status_code == 200
        mock_upsert.assert_called_once()

    @patch("web_api.routes_admin.get_admin_setting")
    @patch("web_api.routes_admin.upsert_admin_setting")
    def test_create_setting(self, mock_upsert, mock_get, admin_client):
        mock_get.return_value = None  # doesn't exist yet
        mock_upsert.return_value = {"key": "NEW_SETTING", "value": "val"}
        resp = admin_client.post("/v1/admin/settings", json={
            "key": "NEW_SETTING", "value": "val", "category": "general",
        })
        assert resp.status_code == 200

    @patch("web_api.routes_admin.get_admin_setting")
    def test_create_duplicate_setting_409(self, mock_get, admin_client):
        mock_get.return_value = {"key": "EXISTING"}
        resp = admin_client.post("/v1/admin/settings", json={
            "key": "EXISTING", "value": "val",
        })
        assert resp.status_code == 409

    def test_create_setting_invalid_key_422(self, admin_client):
        resp = admin_client.post("/v1/admin/settings", json={
            "key": "lowercase_bad", "value": "val",
        })
        assert resp.status_code == 422

    @patch("web_api.routes_admin.delete_admin_setting")
    def test_delete_setting(self, mock_delete, admin_client):
        mock_delete.return_value = True
        resp = admin_client.delete("/v1/admin/settings/OLD_KEY")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.delete_admin_setting")
    def test_delete_nonexistent_setting_404(self, mock_delete, admin_client):
        mock_delete.return_value = False
        resp = admin_client.delete("/v1/admin/settings/NOPE")
        assert resp.status_code == 404


# ── User Management ───────────────────────────────────────────────

class TestUserManagement:
    @patch("web_api.routes_admin.list_users")
    def test_list_users(self, mock_list, admin_client):
        mock_list.return_value = [
            {"id": "u1", "email": "a@b.com", "token_balance": 50, "is_admin": False},
        ]
        resp = admin_client.get("/v1/admin/users")
        assert resp.status_code == 200
        assert len(resp.json()["users"]) == 1

    @patch("web_api.routes_admin.list_users")
    def test_list_users_pagination(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/users?limit=10&offset=20")
        assert resp.status_code == 200
        mock_list.assert_called_once_with(limit=10, offset=20)

    @patch("web_api.routes_admin.set_user_admin")
    def test_grant_admin(self, mock_set, admin_client):
        mock_set.return_value = {"id": "u1", "is_admin": True}
        resp = admin_client.put("/v1/admin/users/u1/admin", json={"is_admin": True})
        assert resp.status_code == 200
        mock_set.assert_called_once_with("u1", True)

    @patch("web_api.routes_admin.set_user_admin")
    def test_revoke_admin(self, mock_set, admin_client):
        mock_set.return_value = {"id": "u1", "is_admin": False}
        resp = admin_client.put("/v1/admin/users/u1/admin", json={"is_admin": False})
        assert resp.status_code == 200

    @patch("web_api.routes_admin.set_user_admin")
    def test_admin_user_not_found_404(self, mock_set, admin_client):
        mock_set.return_value = None
        resp = admin_client.put("/v1/admin/users/u_missing/admin", json={"is_admin": True})
        assert resp.status_code == 404

    @patch("web_api.routes_admin.set_user_token_balance")
    def test_set_token_balance(self, mock_set, admin_client):
        mock_set.return_value = {"id": "u1", "token_balance": 500}
        resp = admin_client.put("/v1/admin/users/u1/tokens", json={"token_balance": 500})
        assert resp.status_code == 200

    @patch("web_api.routes_admin.set_user_token_balance")
    def test_set_tokens_user_not_found_404(self, mock_set, admin_client):
        mock_set.return_value = None
        resp = admin_client.put("/v1/admin/users/u_missing/tokens", json={"token_balance": 100})
        assert resp.status_code == 404

    def test_set_negative_tokens_422(self, admin_client):
        resp = admin_client.put("/v1/admin/users/u1/tokens", json={"token_balance": -10})
        assert resp.status_code == 422


# ── Token Package Management ─────────────────────────────────────

class TestPackageManagement:
    @patch("web_api.routes_admin.list_all_token_packages")
    def test_list_all_packages(self, mock_list, admin_client):
        mock_list.return_value = [
            {"id": "pkg_1", "name": "Starter", "active": True},
            {"id": "pkg_2", "name": "Legacy", "active": False},
        ]
        resp = admin_client.get("/v1/admin/packages")
        assert resp.status_code == 200
        assert len(resp.json()["packages"]) == 2

    @patch("web_api.routes_admin.create_token_package")
    def test_create_package(self, mock_create, admin_client):
        mock_create.return_value = {"id": "pkg_new", "name": "Enterprise", "tokens": 1000}
        resp = admin_client.post("/v1/admin/packages", json={
            "name": "Enterprise", "tokens": 1000, "price_cents": 9900,
        })
        assert resp.status_code == 200

    @patch("web_api.routes_admin.update_token_package")
    def test_update_package(self, mock_update, admin_client):
        mock_update.return_value = {"id": "pkg_1", "name": "Starter v2"}
        resp = admin_client.put("/v1/admin/packages/pkg_1", json={"name": "Starter v2"})
        assert resp.status_code == 200

    @patch("web_api.routes_admin.update_token_package")
    def test_update_nonexistent_package_404(self, mock_update, admin_client):
        mock_update.return_value = None
        resp = admin_client.put("/v1/admin/packages/pkg_missing", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_package_no_fields_422(self, admin_client):
        resp = admin_client.put("/v1/admin/packages/pkg_1", json={})
        assert resp.status_code == 422

    @patch("web_api.routes_admin.delete_token_package")
    def test_delete_package(self, mock_delete, admin_client):
        mock_delete.return_value = True
        resp = admin_client.delete("/v1/admin/packages/pkg_1")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.delete_token_package")
    def test_delete_nonexistent_package_404(self, mock_delete, admin_client):
        mock_delete.return_value = False
        resp = admin_client.delete("/v1/admin/packages/pkg_missing")
        assert resp.status_code == 404


# ── Admin Views (jobs, integrations, transactions, payments) ─────

class TestAdminViews:
    @patch("web_api.routes_admin.list_all_jobs")
    def test_list_all_jobs(self, mock_list, admin_client):
        mock_list.return_value = [{"id": "job_1", "status": "completed"}]
        resp = admin_client.get("/v1/admin/jobs")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.list_all_jobs")
    def test_list_jobs_with_status_filter(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/jobs?status=failed")
        assert resp.status_code == 200
        mock_list.assert_called_once_with(limit=50, offset=0, status_filter="failed")

    @patch("web_api.routes_admin.list_all_integrations")
    def test_list_all_integrations(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/integrations")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.list_all_transactions")
    def test_list_all_transactions(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/transactions")
        assert resp.status_code == 200

    @patch("web_api.routes_admin.list_all_payments")
    def test_list_all_payments(self, mock_list, admin_client):
        mock_list.return_value = []
        resp = admin_client.get("/v1/admin/payments")
        assert resp.status_code == 200


# ── System Info ───────────────────────────────────────────────────

class TestSystemInfo:
    @patch("shared.settings_service.get_setting", return_value="")
    def test_system_info(self, mock_setting, admin_client):
        resp = admin_client.get("/v1/admin/system")
        assert resp.status_code == 200
        data = resp.json()
        assert "env_name" in data
        assert "storage_backend" in data
        assert data["storage_backend"] == "azure"
