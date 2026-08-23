import io

from PIL import Image

from blasphemy import cover
from conftest import png_bytes


def test_badge_returns_modified_image_same_size():
    original = png_bytes()
    stamped = cover.badge(original)
    assert stamped != original
    image = Image.open(io.BytesIO(stamped))
    assert image.format == "PNG"
    assert image.size == (200, 300)


def test_badge_keeps_jpeg_format():
    buffer = io.BytesIO()
    Image.new("RGB", (100, 150), (200, 200, 200)).save(buffer, format="JPEG")
    stamped = cover.badge(buffer.getvalue(), "TEST")
    assert Image.open(io.BytesIO(stamped)).format == "JPEG"


def test_badge_pixels_changed_in_band_only():
    stamped = Image.open(io.BytesIO(cover.badge(png_bytes())))
    top_pixel = stamped.getpixel((100, 10))
    band_pixel = stamped.getpixel((5, int(300 * 0.80) + 5))
    assert top_pixel[:3] == (20, 80, 160)
    assert band_pixel[:3] != (20, 80, 160)
