import numpy as np
from PIL import Image, ImageDraw

from app.services.ocr.preprocessing import (
    apply_otsu_binarization,
    apply_sharpening,
    compute_otsu_threshold,
    convert_to_grayscale,
    correct_orientation,
    enhance_contrast,
    preprocess_image,
)


def create_sample_image(width: int = 150, height: int = 100) -> Image.Image:
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 130, 80], fill=(50, 50, 50))
    draw.text((30, 35), "TEST LABEL", fill=(255, 255, 255))
    return img


def test_convert_to_grayscale_rgb():
    img = create_sample_image()
    gray = convert_to_grayscale(img)
    assert gray.mode == "L"
    assert gray.size == img.size


def test_convert_to_grayscale_rgba():
    rgba_img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    gray = convert_to_grayscale(rgba_img)
    assert gray.mode == "L"
    assert gray.size == (100, 100)


def test_enhance_contrast():
    img = create_sample_image()
    enhanced = enhance_contrast(img, contrast_factor=1.5, autocontrast=True)
    assert enhanced.size == img.size
    # Grayscale pixel stats should show enhanced spread
    orig_np = np.array(convert_to_grayscale(img))
    enh_np = np.array(convert_to_grayscale(enhanced))
    assert enh_np.std() >= orig_np.std() - 1.0


def test_apply_sharpening():
    img = convert_to_grayscale(create_sample_image())
    sharpened = apply_sharpening(img)
    assert sharpened.size == img.size
    assert sharpened.mode == "L"


def test_compute_otsu_threshold():
    # Synthetic bimodal distribution (dark text at ~30, light background at ~220)
    arr = np.concatenate([np.full((1000,), 30), np.full((1000,), 220)])
    thresh = compute_otsu_threshold(arr)
    assert 30 <= thresh < 220



def test_apply_otsu_binarization():
    img = create_sample_image()
    binary = apply_otsu_binarization(img)
    arr = np.array(binary)
    unique_vals = set(np.unique(arr))
    # Binary should only contain 0 and 255
    assert unique_vals.issubset({0, 255})


def test_correct_orientation():
    img = create_sample_image()
    corr_img, rot = correct_orientation(img)
    assert corr_img.size == img.size


def test_preprocess_image_pipeline():
    img = create_sample_image(width=300, height=200)
    processed, meta = preprocess_image(
        img,
        enable_contrast=True,
        enable_sharpening=True,
        enable_threshold=False,
    )
    assert processed.mode == "L"
    assert processed.size == (300, 200)
    assert "grayscale_converted" in meta["steps_applied"]
    assert "contrast_enhanced" in meta["steps_applied"]
    assert "unsharp_mask_sharpened" in meta["steps_applied"]
