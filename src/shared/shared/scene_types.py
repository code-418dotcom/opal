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

# ── Multi-angle product photography ──────────────────────────────
# Angle instructions injected into the FLUX.2 Pro Edit prompt to
# render the product from different camera viewpoints.

ANGLE_PROMPTS: dict[str, str] = {
    "front": "straight-on front view of the product, camera at eye level facing the front",
    "back": "back view of the product, camera positioned behind showing the rear side",
    "left": "left side profile view of the product, camera positioned to the left",
    "right": "right side profile view of the product, camera positioned to the right",
    "3/4": "three-quarter angle view of the product, camera positioned at 45 degrees showing front and side",
    "top": "overhead top-down view of the product, camera positioned directly above looking straight down",
}

DEFAULT_ANGLE_TYPES: list[str] = [
    "front",
    "3/4",
    "left",
    "right",
    "back",
    "top",
]
