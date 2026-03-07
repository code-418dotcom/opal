"""SEO alt-text and filename generation from processed images.

Uses fal.ai Florence-2 for image captioning, or Azure OpenAI GPT-4o vision.
Falls back to rule-based generation if no vision API is configured.
"""
import logging
import re
import httpx
from typing import Optional

from .settings_service import get_setting

LOG = logging.getLogger(__name__)


def generate_seo_metadata(
    image_bytes: bytes,
    product_filename: str,
    brand_name: Optional[str] = None,
    product_category: Optional[str] = None,
) -> dict:
    """Generate SEO alt-text and filename for a product image.

    Returns: {"alt_text": str, "seo_filename": str}
    """
    # Try vision API first
    fal_key = get_setting("FAL_API_KEY")
    if fal_key:
        try:
            return _generate_with_fal(image_bytes, product_filename, brand_name, product_category, fal_key)
        except Exception as e:
            LOG.warning("Vision API failed, using fallback: %s", e)

    # Fallback: rule-based from filename and metadata
    return _generate_fallback(product_filename, brand_name, product_category)


def _generate_with_fal(
    image_bytes: bytes,
    product_filename: str,
    brand_name: Optional[str],
    product_category: Optional[str],
    api_key: str,
) -> dict:
    """Use fal.ai Florence-2 for image captioning."""
    import base64

    # Upload image data as base64 data URI
    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:image/jpeg;base64,{b64}"

    # Florence-2 is fast and cost-effective for captioning
    endpoint = "https://fal.run/fal-ai/florence-2-large/more-detailed-caption"

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "image_url": data_uri,
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

    caption = result.get("results", "")
    if not caption:
        return _generate_fallback(product_filename, brand_name, product_category)

    # Build SEO-optimized alt-text (max 125 chars for accessibility)
    alt_text = _build_alt_text(caption, brand_name, product_category)

    # Build SEO filename from caption
    seo_filename = _caption_to_filename(caption)

    return {"alt_text": alt_text, "seo_filename": seo_filename}


def _build_alt_text(caption: str, brand_name: Optional[str], product_category: Optional[str]) -> str:
    """Build SEO-optimized alt-text from caption and brand context."""
    parts = []

    if brand_name and brand_name != "default":
        parts.append(brand_name)

    if product_category:
        parts.append(product_category)

    # Use first sentence of caption, cleaned up
    first_sentence = caption.split(".")[0].strip()
    if first_sentence:
        parts.append(first_sentence)

    alt_text = " — ".join(parts) if len(parts) > 1 else (parts[0] if parts else caption)

    # Truncate to 125 chars (SEO best practice)
    if len(alt_text) > 125:
        alt_text = alt_text[:122] + "..."

    return alt_text


def _caption_to_filename(caption: str) -> str:
    """Convert a caption to an SEO-friendly filename."""
    # Take first 8 words
    words = caption.lower().split()[:8]
    # Keep only alphanumeric chars
    clean_words = []
    for word in words:
        cleaned = re.sub(r'[^a-z0-9]', '', word)
        if cleaned:
            clean_words.append(cleaned)

    filename = "-".join(clean_words) if clean_words else "product-image"
    return f"{filename}.jpg"


def _generate_fallback(
    product_filename: str,
    brand_name: Optional[str],
    product_category: Optional[str],
) -> dict:
    """Rule-based SEO metadata from filename and brand context."""
    # Clean filename: remove extension, replace separators with spaces
    stem = product_filename.rsplit(".", 1)[0] if "." in product_filename else product_filename
    # Remove common prefixes (shopify_, item_, etc.)
    stem = re.sub(r'^(shopify|item|img|photo|image|product)_?', '', stem, flags=re.IGNORECASE)
    # Convert to readable words
    words = re.sub(r'[_\-]', ' ', stem).strip()

    parts = []
    if brand_name and brand_name != "default":
        parts.append(brand_name)
    if product_category:
        parts.append(product_category)
    if words:
        parts.append(words)
    else:
        parts.append("product image")

    alt_text = " — ".join(parts) if len(parts) > 1 else parts[0]

    # Filename
    slug = re.sub(r'[^a-z0-9]+', '-', alt_text.lower()).strip('-')
    seo_filename = f"{slug[:60]}.jpg"

    return {"alt_text": alt_text[:125], "seo_filename": seo_filename}
