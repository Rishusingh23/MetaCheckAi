import logging
from typing import Any, Dict, Tuple
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


def correct_orientation(image: Image.Image) -> Tuple[Image.Image, int]:
    """
    Correct image orientation according to EXIF metadata.
    Returns (corrected_image, rotation_angle_applied).
    """
    try:
        # ImageOps.exif_transpose automatically handles standard EXIF tags 1-8
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None:
            return transposed, 0
    except Exception as exc:
        logger.debug("EXIF transpose skipped: %s", exc)
    return image, 0


def convert_to_grayscale(image: Image.Image) -> Image.Image:
    """Convert any image mode (RGB, RGBA, CMYK, P) to 8-bit Grayscale ('L')."""
    if image.mode == "L":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        # Convert transparent background to white before grayscale
        alpha_img = image.convert("RGBA")
        background = Image.new("RGBA", alpha_img.size, (255, 255, 255, 255))
        composite = Image.alpha_composite(background, alpha_img)
        return composite.convert("L")
    return image.convert("L")


def enhance_contrast(
    image: Image.Image,
    contrast_factor: float = 1.3,
    autocontrast: bool = True,
) -> Image.Image:
    """
    Enhance contrast using auto-contrast normalization and linear contrast stretching.
    """
    img = image
    if autocontrast:
        # Cut off 1% of the darkest and lightest pixels to remove noise/spikes
        img = ImageOps.autocontrast(img, cutoff=1)
    if contrast_factor != 1.0:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)
    return img


def apply_sharpening(
    image: Image.Image,
    radius: float = 1.5,
    percent: int = 150,
    threshold: int = 3,
) -> Image.Image:
    """
    Apply Unsharp Mask sharpening to accentuate edge boundaries for text characters.
    """
    return image.filter(
        ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
    )


def compute_otsu_threshold(gray_np: np.ndarray) -> int:
    """
    Calculate Otsu's optimum global binarization threshold value using histogram analysis.
    """
    hist, bin_edges = np.histogram(gray_np, bins=256, range=(0, 256))
    total_pixels = gray_np.size
    current_max = 0.0
    threshold = 127

    sum_total = np.dot(np.arange(256), hist)
    sum_b = 0.0
    weight_b = 0

    for t in range(256):
        weight_b += hist[t]
        if weight_b == 0:
            continue
        weight_f = total_pixels - weight_b
        if weight_f == 0:
            break

        sum_b += t * hist[t]
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / weight_f

        # Between class variance
        var_between = float(weight_b) * float(weight_f) * ((mean_b - mean_f) ** 2)

        if var_between > current_max:
            current_max = var_between
            threshold = t

    return threshold


def apply_otsu_binarization(image: Image.Image) -> Image.Image:
    """
    Apply Otsu's thresholding to generate a clean black-and-white binary image.
    """
    gray = convert_to_grayscale(image)
    gray_np = np.array(gray, dtype=np.uint8)
    threshold = compute_otsu_threshold(gray_np)
    binary_np = (gray_np > threshold).astype(np.uint8) * 255
    return Image.fromarray(binary_np)



def preprocess_image(
    image: Image.Image,
    enable_contrast: bool = True,
    enable_sharpening: bool = True,
    enable_threshold: bool = False,
    contrast_factor: float = 1.25,
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Standard OCR preprocessing pipeline:
    1. EXIF Orientation correction
    2. Grayscale conversion
    3. Normalization and contrast enhancement
    4. Edge sharpening (Unsharp Mask)
    5. Optional Otsu binarization
    """
    steps_applied = []

    # 1. Orientation
    processed_img, rot_angle = correct_orientation(image)
    if rot_angle != 0:
        steps_applied.append(f"orientation_corrected_{rot_angle}deg")

    # 2. Grayscale
    processed_img = convert_to_grayscale(processed_img)
    steps_applied.append("grayscale_converted")

    # 3. Contrast
    if enable_contrast:
        processed_img = enhance_contrast(
            processed_img, contrast_factor=contrast_factor, autocontrast=True
        )
        steps_applied.append("contrast_enhanced")

    # 4. Sharpening
    if enable_sharpening:
        processed_img = apply_sharpening(processed_img)
        steps_applied.append("unsharp_mask_sharpened")

    # 5. Optional Binarization
    if enable_threshold:
        processed_img = apply_otsu_binarization(processed_img)
        steps_applied.append("otsu_binarized")

    # Preserve original metadata
    if hasattr(image, "info") and image.info:
        processed_img.info = dict(image.info)

    metadata = {
        "original_size": {"width": image.size[0], "height": image.size[1]},
        "processed_size": {"width": processed_img.size[0], "height": processed_img.size[1]},
        "mode": processed_img.mode,
        "steps_applied": steps_applied,
    }

    return processed_img, metadata
