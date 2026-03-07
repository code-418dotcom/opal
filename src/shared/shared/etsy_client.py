"""Etsy Open API v3 client for listing image operations."""
import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from .settings_service import get_setting

LOG = logging.getLogger(__name__)

ETSY_API_BASE = "https://openapi.etsy.com/v3"


def build_oauth_url(state: str, redirect_uri: str) -> str:
    """Build Etsy OAuth2 authorization URL (PKCE flow)."""
    params = {
        "response_type": "code",
        "client_id": get_setting("ETSY_API_KEY"),
        "redirect_uri": redirect_uri,
        "scope": "listings_r listings_w images_r images_w",
        "state": state,
        "code_challenge": state,  # Simplified — production should use proper PKCE
        "code_challenge_method": "S256",
    }
    return f"https://www.etsy.com/oauth/connect?{urlencode(params)}"


async def exchange_token(code: str, redirect_uri: str, code_verifier: str) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.etsy.com/v3/public/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": get_setting("ETSY_API_KEY"),
                "redirect_uri": redirect_uri,
                "code": code,
                "code_verifier": code_verifier,
            },
        )
        resp.raise_for_status()
        return resp.json()  # {access_token, refresh_token, expires_in, token_type}


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Refresh an expired access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.etsy.com/v3/public/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": get_setting("ETSY_API_KEY"),
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        return resp.json()


class EtsyClient:
    """Client for Etsy Open API v3."""

    def __init__(self, access_token: str, shop_id: str):
        self.access_token = access_token
        self.shop_id = shop_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "x-api-key": get_setting("ETSY_API_KEY"),
        }

    async def get_shop_info(self) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{ETSY_API_BASE}/application/shops/{self.shop_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_listings(
        self, limit: int = 25, offset: int = 0, state: str = "active"
    ) -> dict[str, Any]:
        """Get shop listings. Returns {listings, count}."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ETSY_API_BASE}/application/shops/{self.shop_id}/listings",
                headers=self._headers(),
                params={
                    "limit": limit,
                    "offset": offset,
                    "state": state,
                    "includes": "images",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "listings": [
                    {
                        "listing_id": listing["listing_id"],
                        "title": listing["title"],
                        "state": listing["state"],
                        "images": [
                            {
                                "listing_image_id": img["listing_image_id"],
                                "url_fullxfull": img["url_fullxfull"],
                                "url_570xN": img["url_570xN"],
                                "rank": img["rank"],
                            }
                            for img in listing.get("images", [])
                        ],
                    }
                    for listing in data.get("results", [])
                ],
                "count": data.get("count", 0),
            }

    async def get_listing_images(self, listing_id: int) -> list[dict[str, Any]]:
        """Get all images for a listing."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ETSY_API_BASE}/application/listings/{listing_id}/images",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    async def upload_image(
        self, listing_id: int, image_data: bytes, filename: str, rank: int = 1
    ) -> dict[str, Any]:
        """Upload a new image to a listing."""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{ETSY_API_BASE}/application/shops/{self.shop_id}/listings/{listing_id}/images",
                headers=self._headers(),
                files={"image": (filename, image_data, "image/png")},
                data={"rank": str(rank)},
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_image(self, listing_id: int, listing_image_id: int) -> None:
        """Delete a listing image."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{ETSY_API_BASE}/application/shops/{self.shop_id}/listings/{listing_id}/images/{listing_image_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
