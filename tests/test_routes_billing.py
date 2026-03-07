"""Tests for billing routes: balance, packages, purchase, webhook, transactions."""
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

MOCK_USER = {
    "user_id": "user_test123",
    "tenant_id": "tenant_test",
    "email": "test@example.com",
    "token_balance": 100,
    "is_admin": False,
}


# ── GET /v1/billing/packages (public, no auth) ────────────────────

class TestListPackages:
    @patch("web_api.routes_billing.list_token_packages")
    def test_list_active_packages(self, mock_list, client):
        mock_list.return_value = [
            {"id": "pkg_1", "name": "Starter", "tokens": 50, "price_cents": 990, "currency": "EUR", "active": True},
            {"id": "pkg_2", "name": "Pro", "tokens": 200, "price_cents": 2990, "currency": "EUR", "active": True},
        ]
        resp = client.get("/v1/billing/packages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["packages"]) == 2
        mock_list.assert_called_once_with(active_only=True)

    @patch("web_api.routes_billing.list_token_packages")
    def test_empty_packages(self, mock_list, client):
        mock_list.return_value = []
        resp = client.get("/v1/billing/packages")
        assert resp.status_code == 200
        assert resp.json()["packages"] == []


# ── GET /v1/billing/balance ────────────────────────────────────────

class TestGetBalance:
    @patch("web_api.routes_billing.get_user_by_id")
    def test_returns_balance_and_admin_flag(self, mock_get, client):
        mock_get.return_value = {"token_balance": 75, "is_admin": False}
        resp = client.get("/v1/billing/balance")
        assert resp.status_code == 200
        assert resp.json() == {"token_balance": 75, "is_admin": False}

    @patch("web_api.routes_billing.get_user_by_id")
    def test_returns_zero_for_unknown_user(self, mock_get, client):
        mock_get.return_value = None
        resp = client.get("/v1/billing/balance")
        assert resp.status_code == 200
        assert resp.json()["token_balance"] == 0


# ── POST /v1/billing/purchase ─────────────────────────────────────

class TestPurchaseTokens:
    @patch("web_api.routes_billing.create_payment")
    @patch("web_api.routes_billing.create_mollie_payment")
    @patch("web_api.routes_billing.get_setting")
    @patch("web_api.routes_billing.get_token_package")
    def test_successful_purchase(self, mock_pkg, mock_setting, mock_mollie, mock_create, client):
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        mock_setting.side_effect = lambda k: {
            "MOLLIE_API_KEY": "test_key",
            "PUBLIC_BASE_URL": "https://api.example.com",
        }.get(k, "")
        mock_mollie.return_value = {"id": "tr_test123", "checkout_url": "https://mollie.com/pay"}

        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173/billing",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_url"] == "https://mollie.com/pay"
        assert "payment_id" in data

        # Verify Mollie was called correctly
        call_kwargs = mock_mollie.call_args[1]
        assert call_kwargs["amount_cents"] == 990
        assert call_kwargs["currency"] == "EUR"
        assert "webhook_url" in call_kwargs

        # Verify payment record was stored
        mock_create.assert_called_once()

    @patch("web_api.routes_billing.get_token_package")
    def test_purchase_unknown_package_404(self, mock_pkg, client):
        mock_pkg.return_value = None
        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_invalid",
            "redirect_url": "http://localhost:5173",
        })
        assert resp.status_code == 404

    @patch("web_api.routes_billing.get_setting")
    @patch("web_api.routes_billing.get_token_package")
    def test_purchase_no_mollie_key_503(self, mock_pkg, mock_setting, client):
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        mock_setting.return_value = ""  # No MOLLIE_API_KEY
        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173",
        })
        assert resp.status_code == 503

    @patch("web_api.routes_billing.create_mollie_payment")
    @patch("web_api.routes_billing.get_setting")
    @patch("web_api.routes_billing.get_token_package")
    def test_purchase_mollie_error_502(self, mock_pkg, mock_setting, mock_mollie, client):
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        mock_setting.side_effect = lambda k: "test_key" if k == "MOLLIE_API_KEY" else ""
        mock_mollie.side_effect = Exception("Mollie API error")

        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173",
        })
        assert resp.status_code == 502

    @patch("web_api.routes_billing.get_token_package")
    def test_purchase_inactive_package_404(self, mock_pkg, client):
        mock_pkg.return_value = {"id": "pkg_1", "active": False}
        resp = client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173",
        })
        assert resp.status_code == 404

    @patch("web_api.routes_billing.create_payment")
    @patch("web_api.routes_billing.create_mollie_payment")
    @patch("web_api.routes_billing.get_setting")
    @patch("web_api.routes_billing.get_token_package")
    def test_purchase_appends_payment_id_to_redirect(self, mock_pkg, mock_setting, mock_mollie, mock_create, client):
        mock_pkg.return_value = {
            "id": "pkg_1", "name": "Starter", "tokens": 50,
            "price_cents": 990, "currency": "EUR", "active": True,
        }
        mock_setting.side_effect = lambda k: {
            "MOLLIE_API_KEY": "test_key",
            "PUBLIC_BASE_URL": "https://api.example.com",
        }.get(k, "")
        mock_mollie.return_value = {"id": "tr_test", "checkout_url": "https://mollie.com/pay"}

        # URL without query params
        client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173/billing",
        })
        redirect = mock_mollie.call_args[1]["redirect_url"]
        assert "?payment_id=" in redirect

        # URL with existing query params
        mock_mollie.reset_mock()
        client.post("/v1/billing/purchase", json={
            "package_id": "pkg_1",
            "redirect_url": "http://localhost:5173/billing?tab=tokens",
        })
        redirect = mock_mollie.call_args[1]["redirect_url"]
        assert "&payment_id=" in redirect


# ── POST /v1/billing/mollie/webhook ───────────────────────────────

class TestMollieWebhook:
    @patch("web_api.routes_billing.credit_tokens")
    @patch("web_api.routes_billing.get_token_package")
    @patch("web_api.routes_billing.update_payment_status")
    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_paid_webhook_credits_tokens(self, mock_mollie, mock_get_pay, mock_update, mock_pkg, mock_credit, client):
        mock_mollie.return_value = {"id": "tr_123", "status": "paid", "metadata": {}}
        mock_get_pay.return_value = {
            "id": "pay_1", "user_id": "user_test123", "package_id": "pkg_1",
            "status": "open", "mollie_payment_id": "tr_123",
        }
        mock_pkg.return_value = {"id": "pkg_1", "name": "Starter", "tokens": 50}
        mock_credit.return_value = 150  # new balance

        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_123"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        mock_update.assert_called_once_with("pay_1", "paid")
        mock_credit.assert_called_once()
        credit_kwargs = mock_credit.call_args[1]
        assert credit_kwargs["amount"] == 50
        assert credit_kwargs["user_id"] == "user_test123"

    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_already_paid_is_idempotent(self, mock_mollie, mock_get_pay, client):
        mock_mollie.return_value = {"id": "tr_123", "status": "paid", "metadata": {}}
        mock_get_pay.return_value = {
            "id": "pay_1", "user_id": "user_test123", "status": "paid",
        }
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_123"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        assert resp.json()["note"] == "already processed"

    @patch("web_api.routes_billing.update_payment_status")
    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_failed_payment_updates_status(self, mock_mollie, mock_get_pay, mock_update, client):
        mock_mollie.return_value = {"id": "tr_123", "status": "failed", "metadata": {}}
        mock_get_pay.return_value = {
            "id": "pay_1", "user_id": "user_test123", "status": "open",
        }
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_123"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        mock_update.assert_called_once_with("pay_1", "failed")

    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_unknown_payment_returns_200(self, mock_mollie, mock_get_pay, client):
        mock_mollie.return_value = {"id": "tr_unknown", "status": "paid", "metadata": {}}
        mock_get_pay.return_value = None  # No payment record
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_unknown"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200  # 200 to avoid Mollie retries

    def test_webhook_missing_id_400(self, client):
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 400

    @patch("web_api.routes_billing.get_mollie_payment")
    def test_webhook_mollie_unreachable_502(self, mock_mollie, client):
        mock_mollie.side_effect = Exception("Connection error")
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_123"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 502

    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_webhook_ignores_pending_status(self, mock_mollie, mock_get_pay, client):
        mock_mollie.return_value = {"id": "tr_123", "status": "open", "metadata": {}}
        mock_get_pay.return_value = {
            "id": "pay_1", "user_id": "user_test123", "status": "open",
        }
        resp = client.post(
            "/v1/billing/mollie/webhook",
            data={"id": "tr_123"},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        assert "ignored" in resp.json().get("note", "")

    @patch("web_api.routes_billing.update_payment_status")
    @patch("web_api.routes_billing.get_payment_by_mollie_id")
    @patch("web_api.routes_billing.get_mollie_payment")
    def test_webhook_json_body(self, mock_mollie, mock_get_pay, mock_update, client):
        mock_mollie.return_value = {"id": "tr_json", "status": "expired", "metadata": {}}
        mock_get_pay.return_value = {
            "id": "pay_1", "user_id": "user_test123", "status": "open",
        }
        resp = client.post("/v1/billing/mollie/webhook", json={"id": "tr_json"})
        assert resp.status_code == 200
        mock_update.assert_called_once_with("pay_1", "expired")


# ── GET /v1/billing/usage ─────────────────────────────────────────

class TestGetUsage:
    @patch("web_api.routes_billing.list_token_transactions")
    @patch("web_api.routes_billing.get_user_by_id")
    def test_usage_summary(self, mock_user, mock_txs, client):
        mock_user.return_value = {"token_balance": 80}
        mock_txs.return_value = [
            {"amount": 50, "type": "purchase"},
            {"amount": -5, "type": "usage"},
            {"amount": -3, "type": "usage"},
        ]
        resp = client.get("/v1/billing/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_balance"] == 80
        assert data["total_tokens_spent"] == 8  # 5 + 3
        assert data["total_tokens_purchased"] == 50
        assert data["total_jobs"] == 2


# ── GET /v1/billing/transactions ──────────────────────────────────

class TestGetTransactions:
    @patch("web_api.routes_billing.list_token_transactions")
    def test_transactions_with_pagination(self, mock_txs, client):
        mock_txs.return_value = [{"id": "tx_1", "amount": -5, "type": "usage"}]
        resp = client.get("/v1/billing/transactions?limit=10&offset=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 10
        assert data["offset"] == 5
        mock_txs.assert_called_once_with(MOCK_USER["user_id"], limit=10, offset=5)


# ── GET /v1/billing/payments/{payment_id} ─────────────────────────

class TestGetPaymentStatus:
    @patch("web_api.routes_billing.get_payment_by_id")
    def test_owner_can_view_payment(self, mock_get, client):
        mock_get.return_value = {
            "id": "pay_1", "user_id": MOCK_USER["user_id"],
            "status": "paid", "amount_cents": 990, "currency": "EUR",
        }
        resp = client.get("/v1/billing/payments/pay_1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

    @patch("web_api.routes_billing.get_payment_by_id")
    def test_non_owner_gets_403(self, mock_get, client):
        mock_get.return_value = {
            "id": "pay_1", "user_id": "other_user",
            "status": "paid",
        }
        resp = client.get("/v1/billing/payments/pay_1")
        assert resp.status_code == 403

    @patch("web_api.routes_billing.get_payment_by_id")
    def test_unknown_payment_404(self, mock_get, client):
        mock_get.return_value = None
        resp = client.get("/v1/billing/payments/pay_nonexistent")
        assert resp.status_code == 404
