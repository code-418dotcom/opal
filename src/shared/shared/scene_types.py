"""
Pre-defined scene type prompts for multi-scene generation.
"""

SCENE_PROMPTS: dict[str, str] = {
    "studio": "Empty product photography studio, clean white seamless backdrop, soft diffused lighting, subtle floor shadow, no objects, no products, blank surface ready for product placement",
    "lifestyle": "Empty modern living room surface, blurred cozy home interior background, warm natural window light, clean uncluttered tabletop, no objects in foreground, product photography backdrop",
    "outdoor": "Empty natural stone surface outdoors, soft golden hour sunlight, blurred green foliage bokeh background, no objects, clean foreground for product placement",
    "minimal": "Empty minimalist backdrop, single soft accent color gradient, clean flat surface, dramatic directional lighting, no objects, gallery-style product photography background",
    "luxury": "Empty polished marble surface, dark moody backdrop with soft warm lighting, gold-tinted reflections, no objects, premium product photography background",
    "kitchen": "Empty clean kitchen countertop, bright morning light from window, blurred kitchen interior background, no food no utensils, uncluttered surface for product placement",
    "office": "Empty clean desk surface, blurred modern office background, soft neutral lighting, no objects no clutter, professional product photography backdrop",
    "nature": "Empty wooden surface with natural texture, blurred green plants and earth tones in background, soft diffused light, no objects, organic product photography backdrop",
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
