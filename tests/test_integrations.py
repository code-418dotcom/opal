"""Tests for integration CRUD and Shopify client utilities."""
import hashlib
import hmac
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def _mock_get_setting(overrides: dict):
    """Return a get_setting mock that returns values from overrides dict."""
    def _get(key):
        return overrides.get(key, '')
    return _get


class TestShopifyHMAC:
    """Test Shopify HMAC verification."""

    def test_verify_hmac_valid(self):
        from shared.shopify_client import verify_hmac

        secret = "test_secret"
        params = {"code": "abc123", "shop": "test.myshopify.com", "state": "xyz", "timestamp": "1234567890"}
        sorted_msg = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        expected_hmac = hmac.new(secret.encode(), sorted_msg.encode(), hashlib.sha256).hexdigest()

        with patch("shared.shopify_client.get_setting", side_effect=_mock_get_setting({"SHOPIFY_API_SECRET": secret})):
            result = verify_hmac({**params, "hmac": expected_hmac})
            assert result is True

    def test_verify_hmac_invalid(self):
        from shared.shopify_client import verify_hmac

        with patch("shared.shopify_client.get_setting", side_effect=_mock_get_setting({"SHOPIFY_API_SECRET": "test_secret"})):
            result = verify_hmac({"code": "abc", "shop": "test.myshopify.com", "hmac": "invalid"})
            assert result is False

    def test_verify_webhook_hmac(self):
        from shared.shopify_client import verify_webhook_hmac
        import base64

        secret = "test_secret"
        body = b'{"shop_id": 123}'
        digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        valid_hmac = base64.b64encode(digest).decode()

        with patch("shared.shopify_client.get_setting", side_effect=_mock_get_setting({"SHOPIFY_API_SECRET": secret})):
            assert verify_webhook_hmac(body, valid_hmac) is True
            assert verify_webhook_hmac(body, "invalid") is False


class TestShopifyOAuthURL:
    """Test OAuth URL generation."""

    def test_build_oauth_url(self):
        from shared.shopify_client import build_oauth_url

        overrides = {
            "SHOPIFY_API_KEY": "test_key",
            "SHOPIFY_SCOPES": "read_products,write_products",
        }
        with patch("shared.shopify_client.get_setting", side_effect=_mock_get_setting(overrides)):
            url = build_oauth_url("test.myshopify.com", "state123", "https://example.com/callback")
            assert "test.myshopify.com" in url
            assert "client_id=test_key" in url
            assert "scope=read_products" in url
            assert "state=state123" in url
            assert "redirect_uri=https" in url


class TestEncryption:
    """Test Fernet encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        import shared.encryption as enc
        enc._fernet = None

        with patch("shared.encryption.get_setting", return_value=key):
            encrypted = enc.encrypt("my_secret_token")
            assert encrypted != "my_secret_token"
            assert enc.decrypt(encrypted) == "my_secret_token"

        enc._fernet = None

    def test_encrypt_missing_key_raises(self):
        import shared.encryption as enc
        enc._fernet = None

        with patch("shared.encryption.get_setting", return_value=""):
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY not configured"):
                enc.encrypt("test")

        enc._fernet = None


class TestShopifyClient:
    """Test ShopifyClient methods."""

    def test_get_products(self):
        import asyncio
        from shared.shopify_client import ShopifyClient

        client = ShopifyClient("test.myshopify.com", "token123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"products": [{"id": 1, "title": "Test"}]}
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_http

            result = asyncio.run(client.get_products(limit=10))
            assert len(result["products"]) == 1
            assert result["products"][0]["title"] == "Test"
            assert result["next_page_info"] is None

    def test_get_products_with_pagination(self):
        import asyncio
        from shared.shopify_client import ShopifyClient

        client = ShopifyClient("test.myshopify.com", "token123")

        mock_response = MagicMock()
        mock_response.json.return_value = {"products": []}
        mock_response.headers = {"link": '<https://test.myshopify.com/admin/api/2024-10/products.json?page_info=abc123&limit=50>; rel="next"'}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_response)
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_http

            result = asyncio.run(client.get_products())
            assert result["next_page_info"] == "abc123"
