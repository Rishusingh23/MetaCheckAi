import io
import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ocr_pipeline import ImageQualitySchema
from app.services.ocr.quality import assess_image_quality, validate_image_file

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/analyze-quality", response_model=ImageQualitySchema)
async def analyze_image_quality(
    file: UploadFile = File(..., description="Image file to analyze for blur, lighting, contrast, and resolution"),
    current_user: User = Depends(get_current_user),
):
    """
    Perform immediate quantitative computer vision quality analytics on an uploaded image.
    Checks sharpness/blur (Laplacian variance), mean brightness, contrast, and resolution.
    Returns quantitative scores and non-blocking advisory warnings.
    Requires authenticated user session.
    """
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    from app.core.config import settings
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum allowed size of {settings.UPLOAD_MAX_SIZE_MB}MB.",
        )

    # 1. Structural validation
    validation = validate_image_file(file_bytes)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.error_message,
        )

    # 2. Quality assessment
    try:
        pil_image = Image.open(io.BytesIO(file_bytes))
        pil_image.load()
        metrics = assess_image_quality(pil_image)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to process image data: {str(exc)}",
        )

    return ImageQualitySchema(
        sharpness_score=metrics.sharpness_score,
        is_blurry=metrics.is_blurry,
        brightness_mean=metrics.brightness_mean,
        is_too_dark=metrics.is_too_dark,
        is_too_bright=metrics.is_too_bright,
        contrast_score=metrics.contrast_score,
        is_low_contrast=metrics.is_low_contrast,
        width=metrics.width,
        height=metrics.height,
        is_low_resolution=metrics.is_low_resolution,
        quality_score=metrics.quality_score,
        warnings=metrics.warnings,
    )
