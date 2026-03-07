"""Tests for WooCommerce and Etsy client libraries."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_woocommerce_oauth_url():
    with patch("shared.settings_service.get_setting", return_value="test_key"):
        from shared.woocommerce_client import build_oauth_url
        url = build_oauth_url("https://example.com", "state123", "https://opal.io/callback")
        assert "example.com/wc-auth/v1/authorize" in url
        assert "state123" in url
        assert "Opal" in url


def test_etsy_oauth_url():
    with patch("shared.settings_service.get_setting", return_value="etsy_test_key"):
        from shared.etsy_client import build_oauth_url
        url = build_oauth_url("state123", "https://opal.io/callback")
        assert "etsy.com/oauth/connect" in url
        assert "etsy_test_key" in url
        assert "state123" in url
        assert "listings_r" in url


def test_woocommerce_client_init():
    from shared.woocommerce_client import WooCommerceClient
    client = WooCommerceClient("https://shop.example.com", "ck_key", "cs_secret")
    assert client.store_url == "https://shop.example.com"
    assert client.base_url == "https://shop.example.com/wp-json/wc/v3"
    assert client._auth() == ("ck_key", "cs_secret")


def test_etsy_client_init():
    from shared.etsy_client import EtsyClient
    client = EtsyClient("token123", "shop456")
    assert client.access_token == "token123"
    assert client.shop_id == "shop456"
    with patch("shared.etsy_client.get_setting", return_value="etsy_key"):
        headers = client._headers()
        assert headers["Authorization"] == "Bearer token123"
        assert headers["x-api-key"] == "etsy_key"


def test_integration_provider_enum():
    from shared.models import IntegrationProvider
    assert IntegrationProvider.shopify.value == "shopify"
    assert IntegrationProvider.woocommerce.value == "woocommerce"
    assert IntegrationProvider.etsy.value == "etsy"
