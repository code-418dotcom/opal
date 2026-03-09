"""Image quality scoring for e-commerce product photography.

Combines programmatic heuristics (resolution, exposure, composition) with
AI vision analysis (Florence-2 captioning) to produce quality scores and
actionable improvement suggestions.
"""
import logging
import math
from io import BytesIO
from typing import Optional

from PIL import Image, ImageStat

from .settings_service import get_setting

LOG = logging.getLogger(__name__)

# Marketplace minimum/recommended resolutions
_MIN_RES = 500    # absolute minimum
_GOOD_RES = 1200  # decent quality
_BEST_RES = 2048  # marketplace recommended (Shopify, Amazon)


def score_image(
    image_bytes: bytes,
    image_count: int = 1,
    category: str = "general",
) -> dict:
    """Score a product image across multiple quality dimensions.

    Returns: {
        "scores": {metric: int(0-100), ...},
        "overall_score": int,
        "caption": str | None,
        "suggestions": [{metric, action, message}, ...],
    }
    """
    img = Image.open(BytesIO(image_bytes))
    scores = {}

    # Heuristic scores (always available, no API cost)
    scores["resolution"] = _score_resolution(img)
    scores["lighting"] = _score_lighting(img)
    scores["composition"] = _score_composition(img)
    scores["image_count"] = _score_image_count(image_count)

    # AI-enhanced scores (requires FAL_API_KEY)
    caption = None
    fal_key = get_setting("FAL_API_KEY")
    if fal_key:
        try:
            caption = _get_caption(image_bytes, fal_key)
            scores["background"] = _score_background_from_caption(caption, img)
            scores["text_penalty"] = _score_text_penalty(caption)
        except Exception as e:
            LOG.warning("Vision scoring failed, using heuristic fallback: %s", e)
            scores["background"] = _score_background_heuristic(img)
            scores["text_penalty"] = 90  # assume no text if we can't check
    else:
        scores["background"] = _score_background_heuristic(img)
        scores["text_penalty"] = 90

    # Weighted overall score
    weights = {
        "resolution": 0.20,
        "background": 0.25,
        "lighting": 0.20,
        "composition": 0.15,
        "text_penalty": 0.10,
        "image_count": 0.10,
    }
    overall = sum(scores[k] * weights[k] for k in weights)
    overall_score = round(overall)

    suggestions = _generate_suggestions(scores, category)

    return {
        "scores": scores,
        "overall_score": overall_score,
        "caption": caption,
        "suggestions": suggestions,
    }


def _score_resolution(img: Image.Image) -> int:
    """Score based on pixel dimensions vs marketplace recommendations."""
    min_dim = min(img.width, img.height)
    if min_dim >= _BEST_RES:
        return 100
    if min_dim >= _GOOD_RES:
        return 70 + int(30 * (min_dim - _GOOD_RES) / (_BEST_RES - _GOOD_RES))
    if min_dim >= _MIN_RES:
        return 30 + int(40 * (min_dim - _MIN_RES) / (_GOOD_RES - _MIN_RES))
    return max(0, int(30 * min_dim / _MIN_RES))


def _score_lighting(img: Image.Image) -> int:
    """Score based on exposure histogram analysis."""
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean_brightness = stat.mean[0]  # 0-255
    stddev = stat.stddev[0]

    # Ideal: mean ~120-140, good spread (stddev 40-80)
    brightness_score = 100 - abs(mean_brightness - 130) * 1.2
    brightness_score = max(0, min(100, brightness_score))

    # Good dynamic range = higher stddev (but not extreme)
    if stddev < 20:
        contrast_score = 30  # flat/washed out
    elif stddev < 40:
        contrast_score = 60
    elif stddev <= 80:
        contrast_score = 100
    else:
        contrast_score = 80  # over-contrasty

    return round(brightness_score * 0.6 + contrast_score * 0.4)


def _score_composition(img: Image.Image) -> int:
    """Score based on product centering and white space ratio."""
    w, h = img.size
    aspect_ratio = max(w, h) / min(w, h)

    # Square-ish images score highest for e-commerce
    if aspect_ratio <= 1.1:
        aspect_score = 100
    elif aspect_ratio <= 1.5:
        aspect_score = 80
    elif aspect_ratio <= 2.0:
        aspect_score = 60
    else:
        aspect_score = 40

    # Check if the subject is centered (using edge-weighted luminance)
    gray = img.convert("L")
    stat = ImageStat.Stat(gray)
    mean_lum = stat.mean[0]

    # Crop center 60% and compare luminance
    cx, cy = w // 5, h // 5
    center_crop = gray.crop((cx, cy, w - cx, h - cy))
    center_stat = ImageStat.Stat(center_crop)
    center_lum = center_stat.mean[0]

    # Product images: center should be different from edges (subject vs background)
    lum_diff = abs(center_lum - mean_lum)
    centering_score = min(100, 50 + int(lum_diff * 2))

    return round(aspect_score * 0.5 + centering_score * 0.5)


def _score_image_count(count: int) -> int:
    """Score based on number of images per product listing."""
    if count >= 7:
        return 100
    if count >= 5:
        return 85
    if count >= 3:
        return 65
    if count >= 2:
        return 45
    return 25


def _score_background_heuristic(img: Image.Image) -> int:
    """Heuristic background scoring based on edge pixel uniformity."""
    rgb = img.convert("RGB")
    w, h = rgb.size

    # Sample edge pixels (top/bottom/left/right strips, 5% deep)
    border = max(int(min(w, h) * 0.05), 2)
    edge_pixels = []
    for x in range(0, w, max(1, w // 50)):
        for y in range(border):
            edge_pixels.append(rgb.getpixel((x, y)))
            edge_pixels.append(rgb.getpixel((x, h - 1 - y)))
    for y in range(0, h, max(1, h // 50)):
        for x in range(border):
            edge_pixels.append(rgb.getpixel((x, y)))
            edge_pixels.append(rgb.getpixel((w - 1 - x, y)))

    if not edge_pixels:
        return 50

    # Calculate color variance of edge pixels
    r_vals = [p[0] for p in edge_pixels]
    g_vals = [p[1] for p in edge_pixels]
    b_vals = [p[2] for p in edge_pixels]

    def _stddev(vals):
        mean = sum(vals) / len(vals)
        return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))

    avg_std = (_stddev(r_vals) + _stddev(g_vals) + _stddev(b_vals)) / 3

    # Low variance = clean background (white, solid color)
    # High variance = cluttered/busy background
    if avg_std < 10:
        return 100  # very uniform (white/solid)
    if avg_std < 25:
        return 80
    if avg_std < 50:
        return 55
    return 30


def _score_background_from_caption(caption: str, img: Image.Image) -> int:
    """Score background quality using AI caption + heuristics."""
    heuristic = _score_background_heuristic(img)
    caption_lower = caption.lower()

    # Boost for clean/studio backgrounds detected by AI
    clean_keywords = ["white background", "plain background", "studio", "clean background",
                      "solid background", "neutral background", "simple background"]
    cluttered_keywords = ["cluttered", "messy", "busy background", "outdoor", "street",
                         "room", "table with", "kitchen", "bedroom", "living room"]

    bonus = 0
    for kw in clean_keywords:
        if kw in caption_lower:
            bonus += 10
            break
    for kw in cluttered_keywords:
        if kw in caption_lower:
            bonus -= 15
            break

    return max(0, min(100, heuristic + bonus))


def _score_text_penalty(caption: str) -> int:
    """Score based on detected text/watermarks in image (higher = better, no text)."""
    caption_lower = caption.lower()
    text_keywords = ["text", "watermark", "logo", "stamp", "writing", "letters",
                     "words", "sign", "label", "tag", "banner", "copyright"]

    penalty = 0
    for kw in text_keywords:
        if kw in caption_lower:
            penalty += 20

    return max(0, 100 - penalty)


def _get_caption(image_bytes: bytes, api_key: str) -> str:
    """Get image caption from fal.ai Florence-2."""
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

    return result.get("results", "")


def _generate_suggestions(scores: dict, category: str) -> list:
    """Generate actionable improvement suggestions based on scores."""
    suggestions = []

    if scores.get("resolution", 100) < 70:
        suggestions.append({
            "metric": "resolution",
            "action": "upscale",
            "message": "Image resolution is below marketplace recommendations. Upscale to at least 2048px.",
            "priority": "high" if scores["resolution"] < 50 else "medium",
        })

    if scores.get("background", 100) < 60:
        suggestions.append({
            "metric": "background",
            "action": "remove_bg",
            "message": "Background appears cluttered or distracting. Remove and replace with a clean scene.",
            "priority": "high" if scores["background"] < 40 else "medium",
        })

    if scores.get("lighting", 100) < 60:
        suggestions.append({
            "metric": "lighting",
            "action": "reprocess",
            "message": "Lighting is uneven or too dark/bright. Consider re-shooting or processing with scene generation.",
            "priority": "medium",
        })

    if scores.get("composition", 100) < 55:
        suggestions.append({
            "metric": "composition",
            "action": "reprocess",
            "message": "Product is not well-centered or aspect ratio is unusual for marketplace listings.",
            "priority": "low",
        })

    if scores.get("text_penalty", 100) < 70:
        suggestions.append({
            "metric": "text_penalty",
            "action": "remove_bg",
            "message": "Text or watermarks detected. Remove background to get a clean product image.",
            "priority": "high",
        })

    if scores.get("image_count", 100) < 65:
        suggestions.append({
            "metric": "image_count",
            "action": "multi_angle",
            "message": "Too few images for this listing. Generate additional angles to improve conversion.",
            "priority": "medium",
        })

    return suggestions
