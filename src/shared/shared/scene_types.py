"""
Pre-defined scene type prompts for multi-scene generation.
"""

SCENE_PROMPTS: dict[str, str] = {
    "studio": "a white seamless paper backdrop with a flat surface, soft even studio lighting, shallow depth of field",
    "lifestyle": "a wooden tabletop with a blurred warm-toned room in the background, soft side lighting, shallow depth of field",
    "outdoor": "a flat stone surface with blurred green foliage in the background, warm golden hour sunlight, shallow depth of field",
    "minimal": "a solid soft grey gradient backdrop with a flat matte surface, one directional light with soft shadow",
    "luxury": "a polished dark marble slab with a dark backdrop, warm accent light, subtle surface reflection",
    "kitchen": "a light countertop with a blurred bright window in the background, natural light, shallow depth of field",
    "office": "a light wooden desk with a soft blurred background, overhead light, shallow depth of field",
    "nature": "a rough wooden surface with blurred earthy green tones in the background, soft diffused daylight, shallow depth of field",
}

DEFAULT_SCENE_TYPES: list[str] = [
    "studio",
    "lifestyle",
    "outdoor",
    "minimal",
    "luxury",
    "kitchen",
    "office",
    "nature",
]

# ── Lighting styles ──────────────────────────────────────────────
# Lighting instructions injected into the FLUX.2 Pro Edit prompt.
# These ONLY describe lighting — never camera angle or product
# repositioning, since FLUX.2 Pro Edit composites onto the original
# product image which must stay exactly as-is.

ANGLE_PROMPTS: dict[str, str] = {
    "eye-level": "even balanced lighting from both sides, clean symmetrical illumination, neutral shadows",
    "low-angle": "subtle upward lighting casting gentle highlights on the upper edges of the product",
    "overhead": "soft even diffused lighting from directly above, gentle top-down illumination, minimal harsh shadows",
    "side-lit": "strong directional side lighting from the left, dramatic shadows and highlights, moody contrast, depth and texture",
    "backlit": "soft warm backlighting creating a gentle glow and rim light around the product, dreamy halo effect, silhouette edges",
    "golden": "warm golden hour lighting, long soft shadows, rich amber tones, inviting and natural warmth",
}

DEFAULT_ANGLE_TYPES: list[str] = [
    "eye-level",
    "low-angle",
    "overhead",
    "side-lit",
    "backlit",
    "golden",
]
