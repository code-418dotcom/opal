"""
Pre-defined scene type prompts for multi-scene generation.
"""

SCENE_PROMPTS: dict[str, str] = {
    "studio": "Professional studio photography setup with clean white background, soft directional lighting, subtle shadow beneath product",
    "lifestyle": "Lifestyle setting showing the product in everyday use, warm natural lighting, modern home environment",
    "outdoor": "Outdoor natural environment, golden hour lighting, lush green foliage in background, product on natural surface",
    "minimal": "Ultra-minimalist scene, single accent color backdrop, dramatic product shadow, gallery-style presentation",
    "luxury": "Luxury high-end setting, marble surface, gold accents, premium brand aesthetic, sophisticated mood lighting",
    "kitchen": "Modern kitchen countertop, natural morning light through window, fresh ingredients nearby, clean and bright",
    "office": "Contemporary office desk setup, clean workspace, tech-forward aesthetic, professional environment",
    "nature": "Natural elements scene, wooden textures, plants, earth tones, organic and sustainable feel",
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
