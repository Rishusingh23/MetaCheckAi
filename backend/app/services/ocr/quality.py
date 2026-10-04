import io
import logging
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image

from app.services.ocr.models import ImageQualityMetrics, ImageValidationResult

logger = logging.getLogger(__name__)

# Supported MIME types and magic headers
SUPPORTED_MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",  # Requires checking WEBP at offset 8
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
    b"BM": "image/bmp",
}

MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MIN_IMAGE_DIMENSION = 50
MAX_IMAGE_DIMENSION = 8192
RECOMMENDED_MIN_DIMENSION = 400

# Quality thresholds
SHARPNESS_BLUR_THRESHOLD = 100.0
BRIGHTNESS_DARK_THRESHOLD = 50.0
BRIGHTNESS_BRIGHT_THRESHOLD = 215.0
CONTRAST_LOW_THRESHOLD = 22.0


def detect_mime_type(data: bytes) -> Optional[str]:
    """Detect MIME type using file signature magic bytes."""
    if len(data) < 12:
        return None
    for magic, mime in SUPPORTED_MAGIC_BYTES.items():
        if data.startswith(magic):
            if magic == b"RIFF":
                if data[8:12] == b"WEBP":
                    return "image/webp"
                continue
            return mime
    return None


def validate_image_file(
    file_bytes: bytes,
    max_size_bytes: int = MAX_IMAGE_SIZE_BYTES,
) -> ImageValidationResult:
    """
    Validate image file for size limits, valid MIME format, and uncorrupted decoding.
    """
    size_bytes = len(file_bytes)
    if size_bytes == 0:
        return ImageValidationResult(
            is_valid=False,
            size_bytes=0,
            error_message="Empty file received. Image size cannot be 0 bytes.",
        )

    if size_bytes > max_size_bytes:
        return ImageValidationResult(
            is_valid=False,
            size_bytes=size_bytes,
            error_message=f"Image file size ({size_bytes / (1024*1024):.2f}MB) exceeds limit of {max_size_bytes / (1024*1024):.1f}MB.",
        )

    mime_type = detect_mime_type(file_bytes)
    if not mime_type:
        return ImageValidationResult(
            is_valid=False,
            size_bytes=size_bytes,
            error_message="Unsupported or unrecognized image format. Allowed formats: JPEG, PNG, WebP, TIFF, BMP.",
        )

    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.load()  # Forces decoding to ensure no corruption
            width, height = img.size

            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                return ImageValidationResult(
                    is_valid=False,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    width=width,
                    height=height,
                    error_message=f"Image dimensions ({width}x{height}) are too small. Minimum dimension is {MIN_IMAGE_DIMENSION}px.",
                )

            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                return ImageValidationResult(
                    is_valid=False,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    width=width,
                    height=height,
                    error_message=f"Image dimensions ({width}x{height}) exceed maximum allowed dimension of {MAX_IMAGE_DIMENSION}px.",
                )

            return ImageValidationResult(
                is_valid=True,
                mime_type=mime_type,
                size_bytes=size_bytes,
                width=width,
                height=height,
            )
    except Exception as exc:
        logger.warning("Corrupted image decoding failure: %s", exc)
        return ImageValidationResult(
            is_valid=False,
            mime_type=mime_type,
            size_bytes=size_bytes,
            error_message=f"Corrupted image payload: unable to decode image data ({str(exc)}).",
        )


def calculate_laplacian_variance(gray_array: np.ndarray) -> float:
    """
    Compute variance of the discrete 2D Laplacian operator over a grayscale NumPy array.
    Uses standard kernel: [[0, 1, 0], [1, -4, 1], [0, 1, 0]].
    A higher variance corresponds to crisper edges (less blur).
    """
    if gray_array.ndim != 2 or gray_array.shape[0] < 3 or gray_array.shape[1] < 3:
        return 0.0

    arr = gray_array.astype(np.float64)
    # Discrete 2D convolution for 3x3 Laplacian
    lap = (
        arr[:-2, 1:-1]
        + arr[2:, 1:-1]
        + arr[1:-1, :-2]
        + arr[1:-1, 2:]
        - 4.0 * arr[1:-1, 1:-1]
    )
    return float(np.var(lap))


def assess_image_quality(image: Image.Image) -> ImageQualityMetrics:
    """
    Assess quantitative image quality indicators:
    - Sharpness / Blur score
    - Brightness mean & extremes
    - Contrast standard deviation
    - Resolution adequacy
    Returns metric structure with non-blocking advisory warnings.
    """
    # Ensure image is in RGB or Grayscale
    if image.mode != "L":
        gray_image = image.convert("L")
    else:
        gray_image = image

    width, height = image.size
    gray_np = np.array(gray_image, dtype=np.uint8)

    # 1. Sharpness calculation
    sharpness_score = calculate_laplacian_variance(gray_np)
    is_blurry = bool(sharpness_score < SHARPNESS_BLUR_THRESHOLD)

    # 2. Brightness calculation
    brightness_mean = float(np.mean(gray_np))
    is_too_dark = bool(brightness_mean < BRIGHTNESS_DARK_THRESHOLD)
    is_too_bright = bool(brightness_mean > BRIGHTNESS_BRIGHT_THRESHOLD)

    # 3. Contrast calculation
    contrast_score = float(np.std(gray_np))
    is_low_contrast = bool(contrast_score < CONTRAST_LOW_THRESHOLD)

    # 4. Resolution check
    is_low_resolution = bool(
        width < RECOMMENDED_MIN_DIMENSION or height < RECOMMENDED_MIN_DIMENSION
    )

    # 5. Composite Quality Score (0 - 100)
    # Sharpness factor (0-40 pts): saturates at variance 400
    sharp_pts = min(40.0, (sharpness_score / 400.0) * 40.0)

    # Contrast factor (0-30 pts): saturates at std 60
    contrast_pts = min(30.0, (contrast_score / 60.0) * 30.0)

    # Brightness factor (0-20 pts): centered at 128
    bright_dist = abs(brightness_mean - 128.0)
    bright_pts = max(0.0, 20.0 - (bright_dist / 128.0) * 20.0)

    # Resolution factor (0-10 pts):
    res_factor = min(1.0, min(width, height) / float(RECOMMENDED_MIN_DIMENSION))
    res_pts = res_factor * 10.0

    quality_score = float(np.clip(sharp_pts + contrast_pts + bright_pts + res_pts, 5.0, 100.0))

    # Construct human-readable advisory warnings
    warnings: List[str] = []
    if is_blurry:
        warnings.append(
            f"Image appears blurry (sharpness score {sharpness_score:.1f} < {SHARPNESS_BLUR_THRESHOLD:.0f}). Text recognition accuracy may be degraded."
        )
    if is_too_dark:
        warnings.append(
            f"Image is underexposed or dark (mean brightness {brightness_mean:.1f}/255). Text contrast may be insufficient."
        )
    elif is_too_bright:
        warnings.append(
            f"Image is overexposed or washed out (mean brightness {brightness_mean:.1f}/255). Glare or saturation detected."
        )
    if is_low_contrast:
        warnings.append(
            f"Low contrast detected (contrast score {contrast_score:.1f} < {CONTRAST_LOW_THRESHOLD:.0f}). Background and text may blend together."
        )
    if is_low_resolution:
        warnings.append(
            f"Image resolution ({width}x{height}) is below recommended {RECOMMENDED_MIN_DIMENSION}x{RECOMMENDED_MIN_DIMENSION}px. Small text like Net Quantity or MRP may not be resolved clearly."
        )

    return ImageQualityMetrics(
        sharpness_score=sharpness_score,
        is_blurry=is_blurry,
        brightness_mean=brightness_mean,
        is_too_dark=is_too_dark,
        is_too_bright=is_too_bright,
        contrast_score=contrast_score,
        is_low_contrast=is_low_contrast,
        width=width,
        height=height,
        is_low_resolution=is_low_resolution,
        quality_score=quality_score,
        warnings=warnings,
    )
