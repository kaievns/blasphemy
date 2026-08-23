import io

from PIL import Image, ImageDraw, ImageFont

FONT_PATHS = (
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def _font(size: int) -> ImageFont.ImageFont:
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def badge(image_bytes: bytes, text: str = "OPTIMISED") -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    fmt = (image.format or "JPEG").upper()
    image = image.convert("RGBA")
    width, height = image.size

    band_height = max(int(height * 0.09), 24)
    band_top = int(height * 0.80)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(
        (0, band_top, width, band_top + band_height), fill=(178, 34, 34, 235)
    )
    font = _font(int(band_height * 0.55))
    text_width = draw.textlength(text, font=font)
    draw.text(
        ((width - text_width) / 2, band_top + band_height * 0.22),
        text,
        font=font,
        fill=(255, 255, 255, 255),
    )

    stamped = Image.alpha_composite(image, overlay)
    if fmt in ("JPEG", "JPG"):
        stamped = stamped.convert("RGB")
        fmt = "JPEG"
    buffer = io.BytesIO()
    stamped.save(buffer, format=fmt)
    return buffer.getvalue()
