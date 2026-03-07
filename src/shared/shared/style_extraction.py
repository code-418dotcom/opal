"""Extract style cues (colors, lighting, mood) from reference images.

Uses Pillow for color palette extraction and optionally fal.ai Florence-2
for scene description analysis.
"""
import io
import logging
from collections import Counter
from typing import Optional

from PIL import Image

from .settings_service import get_setting

LOG = logging.getLogger(__name__)


def extract_style(image_bytes: bytes) -> dict:
    """Extract style cues from a reference image.

    Returns: {
        "colors": ["#hex1", "#hex2", ...],
        "lighting": "warm" | "cool" | "neutral" | "dramatic",
        "mood": str,
        "keywords": [str],
    }
    """
    result = {}

    # Always extract color palette (no API needed)
    result["colors"] = _extract_colors(image_bytes)
    result["lighting"] = _analyze_lighting(image_bytes)

    # Try AI-powered scene analysis
    fal_key = get_setting("FAL_API_KEY")
    if fal_key:
        try:
            ai_style = _extract_with_fal(image_bytes, fal_key)
            result["mood"] = ai_style.get("mood", "")
            result["keywords"] = ai_style.get("keywords", [])
        except Exception as e:
            LOG.warning("AI style extraction failed (using Pillow only): %s", e)
            result["mood"] = ""
            result["keywords"] = []
    else:
        result["mood"] = ""
        result["keywords"] = []

    return result


def _extract_colors(image_bytes: bytes, num_colors: int = 5) -> list[str]:
    """Extract dominant colors from an image using quantization."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Resize for speed
    img = img.resize((150, 150), Image.Resampling.LANCZOS)

    # Quantize to reduce colors
    quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    if not palette:
        return []

    # Get the most common colors
    color_counts = Counter(quantized.getdata())
    sorted_colors = color_counts.most_common(num_colors)

    hex_colors = []
    for color_index, _count in sorted_colors:
        r = palette[color_index * 3]
        g = palette[color_index * 3 + 1]
        b = palette[color_index * 3 + 2]
        hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")

    return hex_colors


def _analyze_lighting(image_bytes: bytes) -> str:
    """Analyze image lighting from color temperature."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((100, 100), Image.Resampling.LANCZOS)

    pixels = list(img.getdata())
    avg_r = sum(p[0] for p in pixels) / len(pixels)
    avg_g = sum(p[1] for p in pixels) / len(pixels)
    avg_b = sum(p[2] for p in pixels) / len(pixels)

    # Simple heuristic: warm (red-shifted), cool (blue-shifted), or neutral
    avg_brightness = (avg_r + avg_g + avg_b) / 3

    if avg_brightness < 80:
        return "dramatic"
    elif avg_r > avg_b + 20:
        return "warm"
    elif avg_b > avg_r + 20:
        return "cool"
    else:
        return "neutral"


def _extract_with_fal(image_bytes: bytes, api_key: str) -> dict:
    """Use fal.ai Florence-2 to describe the image style."""
    import base64
    import httpx

    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:image/jpeg;base64,{b64}"

    endpoint = "https://fal.run/fal-ai/florence-2-large/more-detailed-caption"

    headers = {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(endpoint, json={"image_url": data_uri}, headers=headers)
        response.raise_for_status()
        result = response.json()

    caption = result.get("results", "")

    # Parse caption for style keywords
    mood_words = {
        "warm", "cozy", "elegant", "modern", "rustic", "minimalist", "luxurious",
        "bright", "dark", "moody", "cheerful", "natural", "industrial", "bohemian",
        "scandinavian", "vintage", "contemporary", "clean", "soft",
    }

    caption_lower = caption.lower()
    found_moods = [w for w in mood_words if w in caption_lower]

    # Extract short keywords from caption
    words = caption_lower.split()
    keywords = [w for w in words if len(w) > 3 and w.isalpha()][:10]

    return {
        "mood": found_moods[0] if found_moods else "",
        "keywords": list(set(found_moods + keywords[:5])),
    }
