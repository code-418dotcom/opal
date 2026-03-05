"""Shopify Admin API client for product image operations."""
import hashlib
import hmac
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from .settings_service import get_setting

LOG = logging.getLogger(__name__)

SHOPIFY_API_VERSION = "2024-10"


def build_oauth_url(shop: str, state: str, redirect_uri: str) -> str:
    """Build Shopify OAuth authorization URL."""
    params = {
        "client_id": get_setting('SHOPIFY_API_KEY'),
        "scope": get_setting('SHOPIFY_SCOPES') or 'read_products,write_products',
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"


async def exchange_token(shop: str, code: str) -> dict[str, Any]:
    """Exchange OAuth authorization code for permanent access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": get_setting('SHOPIFY_API_KEY'),
                "client_secret": get_setting('SHOPIFY_API_SECRET'),
                "code": code,
            },
        )
        resp.raise_for_status()
        return resp.json()


def verify_hmac(query_params: dict[str, str]) -> bool:
    """Verify Shopify HMAC signature on OAuth callback."""
    hmac_value = query_params.get("hmac", "")
    params_without_hmac = {k: v for k, v in query_params.items() if k != "hmac"}
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params_without_hmac.items()))
    digest = hmac.new(
        get_setting('SHOPIFY_API_SECRET').encode(),
        sorted_params.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, hmac_value)


def verify_webhook_hmac(body: bytes, hmac_header: str) -> bool:
    """Verify Shopify webhook HMAC (for GDPR webhooks)."""
    digest = hmac.new(
        get_setting('SHOPIFY_API_SECRET').encode(),
        body,
        hashlib.sha256,
    ).digest()
    import base64
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, hmac_header)


class ShopifyClient:
    """Client for Shopify Admin REST API."""

    def __init__(self, shop: str, access_token: str):
        self.shop = shop
        self.access_token = access_token
        self.base_url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}"

    def _headers(self) -> dict[str, str]:
        return {"X-Shopify-Access-Token": self.access_token}

    async def get_shop_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/shop.json",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()["shop"]

    async def get_products(self, limit: int = 50, page_info: str | None = None) -> dict[str, Any]:
        """Get products with images. Returns {products, next_page_info}."""
        params: dict[str, Any] = {"limit": limit, "fields": "id,title,images,status,variants"}
        url = f"{self.base_url}/products.json"

        headers = self._headers()
        if page_info:
            url = f"{self.base_url}/products.json?page_info={page_info}&limit={limit}"
            params = {}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()

            # Parse cursor-based pagination from Link header
            next_page = None
            link = resp.headers.get("link", "")
            if 'rel="next"' in link:
                for part in link.split(","):
                    if 'rel="next"' in part:
                        next_page = part.split("page_info=")[1].split("&")[0].split(">")[0]
                        break

            return {
                "products": resp.json()["products"],
                "next_page_info": next_page,
            }

    async def get_product(self, product_id: int) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/products/{product_id}.json",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()["product"]

    async def get_product_images(self, product_id: int) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/products/{product_id}/images.json",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()["images"]

    async def upload_image(self, product_id: int, image_data: bytes, filename: str, position: int | None = None) -> dict[str, Any]:
        """Upload a new image to a product."""
        import base64
        payload: dict[str, Any] = {
            "image": {
                "attachment": base64.b64encode(image_data).decode(),
                "filename": filename,
            }
        }
        if position is not None:
            payload["image"]["position"] = position

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/products/{product_id}/images.json",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["image"]

    async def update_image(self, product_id: int, image_id: int, image_data: bytes, filename: str) -> dict[str, Any]:
        """Replace an existing product image."""
        import base64
        payload = {
            "image": {
                "id": image_id,
                "attachment": base64.b64encode(image_data).decode(),
                "filename": filename,
            }
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(
                f"{self.base_url}/products/{product_id}/images/{image_id}.json",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["image"]

    async def delete_image(self, product_id: int, image_id: int) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/products/{product_id}/images/{image_id}.json",
                headers=self._headers(),
            )
            resp.raise_for_status()
