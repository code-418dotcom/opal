"""WooCommerce REST API client for product image operations."""
import base64
import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from .settings_service import get_setting

LOG = logging.getLogger(__name__)

WC_API_VERSION = "wc/v3"


def build_oauth_url(store_url: str, state: str, redirect_uri: str) -> str:
    """Build WooCommerce REST API key authorization URL.

    WooCommerce uses its built-in auth endpoint that lets users generate
    read/write API keys for your app.
    """
    params = {
        "app_name": "Opal Product Photography",
        "scope": "read_write",
        "user_id": state,  # WooCommerce returns this in callback
        "return_url": redirect_uri,
        "callback_url": redirect_uri,
    }
    base = store_url.rstrip("/")
    return f"{base}/wc-auth/v1/authorize?{urlencode(params)}"


class WooCommerceClient:
    """Client for WooCommerce REST API v3."""

    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.store_url = store_url.rstrip("/")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.base_url = f"{self.store_url}/wp-json/{WC_API_VERSION}"

    def _auth(self) -> tuple[str, str]:
        return (self.consumer_key, self.consumer_secret)

    async def get_products(self, per_page: int = 50, page: int = 1) -> dict[str, Any]:
        """Get products with images. Returns {products, total_pages}."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/products",
                auth=self._auth(),
                params={"per_page": per_page, "page": page},
            )
            resp.raise_for_status()
            total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
            products = resp.json()
            return {
                "products": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "status": p["status"],
                        "images": [
                            {
                                "id": img["id"],
                                "src": img["src"],
                                "name": img.get("name", ""),
                                "alt": img.get("alt", ""),
                            }
                            for img in p.get("images", [])
                        ],
                    }
                    for p in products
                ],
                "total_pages": total_pages,
                "page": page,
            }

    async def get_product(self, product_id: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/products/{product_id}",
                auth=self._auth(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_product_images(self, product_id: int) -> list[dict[str, Any]]:
        product = await self.get_product(product_id)
        return product.get("images", [])

    async def upload_image(
        self, product_id: int, image_data: bytes, filename: str, alt: str = ""
    ) -> dict[str, Any]:
        """Add a new image to a product by uploading to WP media then linking."""
        # Step 1: Upload to WordPress media library
        async with httpx.AsyncClient(timeout=60) as client:
            media_resp = await client.post(
                f"{self.store_url}/wp-json/wp/v2/media",
                auth=self._auth(),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "image/png",
                },
                content=image_data,
            )
            media_resp.raise_for_status()
            media = media_resp.json()
            media_url = media["source_url"]

            # Step 2: Add image to product
            product = await self.get_product(product_id)
            images = product.get("images", [])
            images.append({"src": media_url, "name": filename, "alt": alt})

            resp = await client.put(
                f"{self.base_url}/products/{product_id}",
                auth=self._auth(),
                json={"images": images},
            )
            resp.raise_for_status()
            updated = resp.json()
            return updated["images"][-1] if updated.get("images") else {}

    async def update_image(
        self, product_id: int, image_id: int, image_data: bytes, filename: str, alt: str = ""
    ) -> dict[str, Any]:
        """Replace an existing product image."""
        # Upload new media
        async with httpx.AsyncClient(timeout=60) as client:
            media_resp = await client.post(
                f"{self.store_url}/wp-json/wp/v2/media",
                auth=self._auth(),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "image/png",
                },
                content=image_data,
            )
            media_resp.raise_for_status()
            media_url = media_resp.json()["source_url"]

            # Update product: replace the matching image
            product = await self.get_product(product_id)
            images = [
                {"src": media_url, "name": filename, "alt": alt}
                if img["id"] == image_id
                else {"id": img["id"], "src": img["src"]}
                for img in product.get("images", [])
            ]

            resp = await client.put(
                f"{self.base_url}/products/{product_id}",
                auth=self._auth(),
                json={"images": images},
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_image(self, product_id: int, image_id: int) -> None:
        """Remove an image from a product."""
        product = await self.get_product(product_id)
        images = [
            {"id": img["id"], "src": img["src"]}
            for img in product.get("images", [])
            if img["id"] != image_id
        ]
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{self.base_url}/products/{product_id}",
                auth=self._auth(),
                json={"images": images},
            )
            resp.raise_for_status()
