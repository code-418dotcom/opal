"""Image resizing and padding for marketplace export presets."""

import io
from PIL import Image

from .export_presets import ExportPreset


def resize_image(image_bytes: bytes, preset: ExportPreset) -> bytes:
    """Resize an image to fit the preset dimensions.

    - fit="contain": scales down to fit within target, pads remaining space
    - fit="cover": scales up to fill target, crops excess
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert to RGBA if we need transparency, otherwise RGB
    if preset.bg_color == "transparent":
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    target_w, target_h = preset.width, preset.height

    if preset.fit == "cover":
        img = _fit_cover(img, target_w, target_h)
    else:
        img = _fit_contain(img, target_w, target_h, preset.bg_color)

    # Save to bytes
    buf = io.BytesIO()
    if preset.bg_color == "transparent":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=preset.quality, optimize=True)
    return buf.getvalue()


def _fit_contain(img: Image.Image, target_w: int, target_h: int, bg_color: str) -> Image.Image:
    """Scale image to fit within target, pad remaining space with bg_color."""
    orig_w, orig_h = img.size

    # Calculate scale to fit within target
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    # Only resize if we need to scale down (or up to fill more space)
    if (new_w, new_h) != (orig_w, orig_h):
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Create canvas with background color
    if bg_color == "transparent":
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    elif bg_color == "white":
        canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    else:
        # Parse hex color
        hex_color = bg_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        canvas = Image.new("RGB", (target_w, target_h), (r, g, b))

    # Center the image on the canvas
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2

    if img.mode == "RGBA":
        canvas.paste(img, (offset_x, offset_y), img)
    else:
        canvas.paste(img, (offset_x, offset_y))

    return canvas


def _fit_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Scale image to cover target dimensions, crop excess."""
    orig_w, orig_h = img.size

    # Calculate scale to cover target
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    if (new_w, new_h) != (orig_w, orig_h):
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return img
