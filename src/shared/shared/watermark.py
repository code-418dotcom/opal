"""Apply a diagonal text watermark to images for free-tier users."""
import io
from PIL import Image, ImageDraw, ImageFont


def apply_watermark(image_bytes: bytes, text: str = "OPAL PREVIEW") -> bytes:
    """Apply a semi-transparent diagonal text watermark across the image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    # Create watermark layer
    watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)

    # Calculate font size relative to image (roughly 1/15 of diagonal)
    diag = (img.width ** 2 + img.height ** 2) ** 0.5
    font_size = max(int(diag / 15), 20)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Tile the watermark diagonally across the image
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Spacing between watermark instances
    step_x = int(text_w * 1.5)
    step_y = int(text_h * 3)

    for y in range(-img.height, img.height * 2, step_y):
        for x in range(-img.width, img.width * 2, step_x):
            # Create a small rotated text image
            txt_img = Image.new("RGBA", (text_w + 20, text_h + 20), (0, 0, 0, 0))
            txt_draw = ImageDraw.Draw(txt_img)
            txt_draw.text((10, 10), text, font=font, fill=(255, 255, 255, 45))

            # Rotate
            rotated = txt_img.rotate(30, expand=True, fillcolor=(0, 0, 0, 0))

            # Paste onto watermark layer
            watermark.paste(rotated, (x, y), rotated)

    # Composite
    result = Image.alpha_composite(img, watermark)
    result = result.convert("RGB")

    buf = io.BytesIO()
    result.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
