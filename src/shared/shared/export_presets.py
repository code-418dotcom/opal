"""Platform-specific image export presets for marketplace resizing."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportPreset:
    """Defines target dimensions and behavior for a platform export."""
    name: str           # Human-readable name
    key: str            # Machine key (used in API/ZIP folder names)
    width: int          # Target width in pixels
    height: int         # Target height in pixels
    bg_color: str       # Background fill color: "white", "transparent", or hex
    fit: str            # "contain" (pad to fit) or "cover" (crop to fill)
    quality: int        # JPEG quality (1-100), PNG ignores this


# Platform presets — dimensions based on 2025/2026 platform guidelines
PRESETS: dict[str, ExportPreset] = {
    "amazon_main": ExportPreset(
        name="Amazon Main Image",
        key="amazon_main",
        width=1600, height=1600,
        bg_color="white", fit="contain", quality=90,
    ),
    "amazon_listing": ExportPreset(
        name="Amazon Listing",
        key="amazon_listing",
        width=1000, height=1000,
        bg_color="white", fit="contain", quality=90,
    ),
    "shopify": ExportPreset(
        name="Shopify Product",
        key="shopify",
        width=2048, height=2048,
        bg_color="white", fit="contain", quality=90,
    ),
    "instagram_feed": ExportPreset(
        name="Instagram Feed",
        key="instagram_feed",
        width=1080, height=1080,
        bg_color="white", fit="contain", quality=90,
    ),
    "instagram_story": ExportPreset(
        name="Instagram Story",
        key="instagram_story",
        width=1080, height=1920,
        bg_color="white", fit="contain", quality=90,
    ),
    "etsy": ExportPreset(
        name="Etsy Listing",
        key="etsy",
        width=2000, height=2000,
        bg_color="white", fit="contain", quality=90,
    ),
    "ebay": ExportPreset(
        name="eBay Listing",
        key="ebay",
        width=1600, height=1600,
        bg_color="white", fit="contain", quality=90,
    ),
    "pinterest": ExportPreset(
        name="Pinterest Pin",
        key="pinterest",
        width=1000, height=1500,
        bg_color="white", fit="contain", quality=90,
    ),
    "facebook_ad": ExportPreset(
        name="Facebook Ad",
        key="facebook_ad",
        width=1200, height=630,
        bg_color="white", fit="contain", quality=90,
    ),
    "web_large": ExportPreset(
        name="Web (Large)",
        key="web_large",
        width=1200, height=1200,
        bg_color="transparent", fit="contain", quality=90,
    ),
    "web_thumb": ExportPreset(
        name="Web (Thumbnail)",
        key="web_thumb",
        width=400, height=400,
        bg_color="white", fit="contain", quality=85,
    ),
}


def get_preset(key: str) -> ExportPreset | None:
    return PRESETS.get(key)


def list_presets() -> list[dict]:
    """Return presets as serializable dicts for the API."""
    return [
        {
            "key": p.key,
            "name": p.name,
            "width": p.width,
            "height": p.height,
        }
        for p in PRESETS.values()
    ]
