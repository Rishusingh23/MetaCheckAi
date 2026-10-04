import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.services.ocr.quality import (
    assess_image_quality,
    calculate_laplacian_variance,
)


def test_calculate_laplacian_variance_sharp_vs_blurry():
    # Sharp image: high frequency grid
    sharp_np = np.zeros((100, 100), dtype=np.uint8)
    sharp_np[::2, ::2] = 255
    sharp_var = calculate_laplacian_variance(sharp_np)

    # Blurry/flat image: constant values
    flat_np = np.full((100, 100), 128, dtype=np.uint8)
    flat_var = calculate_laplacian_variance(flat_np)

    assert sharp_var > 1000.0
    assert flat_var == 0.0


def test_assess_image_quality_sharp_image():
    # Create sharp high-res image
    img = Image.new("RGB", (600, 400), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for i in range(10, 390, 20):
        draw.line([(10, i), (590, i)], fill=(0, 0, 0), width=2)

    metrics = assess_image_quality(img)
    assert metrics.width == 600
    assert metrics.height == 400
    assert metrics.is_low_resolution is False
    assert metrics.is_blurry is False
    assert metrics.quality_score > 50.0


def test_assess_image_quality_blurry_image():
    # Create a blurred image
    img = Image.new("RGB", (500, 500), (128, 128, 128))
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 400, 400], fill=(200, 200, 200))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=25))

    metrics = assess_image_quality(blurred)
    assert metrics.is_blurry is True
    assert any("blurry" in w.lower() for w in metrics.warnings)


def test_assess_image_quality_dark_image():
    # Very dark image
    img = Image.new("RGB", (500, 500), (10, 10, 10))
    metrics = assess_image_quality(img)
    assert metrics.is_too_dark is True
    assert any("dark" in w.lower() or "underexposed" in w.lower() for w in metrics.warnings)


def test_assess_image_quality_bright_image():
    # Very bright/overexposed image
    img = Image.new("RGB", (500, 500), (245, 245, 245))
    metrics = assess_image_quality(img)
    assert metrics.is_too_bright is True
    assert any("overexposed" in w.lower() or "bright" in w.lower() for w in metrics.warnings)


def test_assess_image_quality_low_resolution():
    # Small image (below 400px)
    img = Image.new("RGB", (200, 150), (150, 150, 150))
    metrics = assess_image_quality(img)
    assert metrics.is_low_resolution is True
    assert any("resolution" in w.lower() for w in metrics.warnings)
