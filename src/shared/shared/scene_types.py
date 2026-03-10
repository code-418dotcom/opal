"""
Pre-defined scene type prompts for multi-scene generation.
"""

SCENE_PROMPTS: dict[str, str] = {
    "studio": "plain white seamless paper backdrop, single flat surface, soft even studio lighting, shallow depth of field, completely bare scene, nothing on the surface",
    "lifestyle": "plain wooden tabletop, blurred warm-toned room far in background, single soft light source from the side, shallow depth of field, completely bare surface, nothing on the table",
    "outdoor": "single flat stone slab, blurred green foliage far in background, warm golden hour sunlight, shallow depth of field, completely bare surface, nothing on the stone",
    "minimal": "solid soft grey gradient backdrop, single flat matte surface, one directional light with soft shadow, completely bare scene, nothing on the surface",
    "luxury": "polished dark marble slab, solid dark backdrop, single warm accent light, subtle reflection on surface, completely bare scene, nothing on the marble",
    "kitchen": "plain light countertop surface, blurred bright window far in background, single natural light source, shallow depth of field, completely bare counter, nothing on the surface",
    "office": "plain light wooden desk surface, solid soft blurred background, single overhead light, shallow depth of field, completely bare desk, nothing on the surface",
    "nature": "single rough wooden plank, blurred earthy green tones far in background, soft diffused daylight, shallow depth of field, completely bare surface, nothing on the wood",
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

# ── Scene perspective & lighting styles ──────────────────────────
# Perspective instructions injected into the FLUX.2 Pro Edit prompt
# to vary the lighting, composition, and camera feel per image.

ANGLE_PROMPTS: dict[str, str] = {
    "eye-level": "straight-on eye-level shot, even balanced lighting from both sides, clean symmetrical composition",
    "low-angle": "dramatic low-angle perspective looking slightly upward, product appears bold and prominent, subtle upward lighting",
    "overhead": "overhead flat-lay composition, camera directly above, soft even diffused lighting, clean top-down view",
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
