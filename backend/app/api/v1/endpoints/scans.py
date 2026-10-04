import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.inspection import Inspection, InspectionStatusEnum
from app.models.ocr import OCRResult
from app.models.product import ImageTypeEnum, Product, ProductImage
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.models.user import RoleEnum, User
from app.schemas.ocr_pipeline import (
    BoundingBoxSchema,
    ImageQualitySchema,
    OCRProcessRequest,
    OCRProcessResponse,
    OCRRegionSchema,
    ScanUploadAndProcessResponse,
)
from app.schemas.scan import ScanRead
from app.services.scan_processor import ScanProcessorService
from app.services.storage.local import LocalStorageProvider

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_ocr_process_response(scan: Scan, ocr_result: OCRResult, quality_metrics: ImageQualitySchema) -> OCRProcessResponse:
    bounding_boxes = ocr_result.bounding_boxes or {}
    raw_regions = bounding_boxes.get("regions", [])
    proc_meta = ocr_result.processing_metadata or {}

    regions = [
        OCRRegionSchema(
            text=r.get("text", ""),
            confidence=float(r.get("confidence", 0.0)),
            bbox=BoundingBoxSchema(
                x1=r.get("bbox", {}).get("x1", 0),
                y1=r.get("bbox", {}).get("y1", 0),
                x2=r.get("bbox", {}).get("x2", 0),
                y2=r.get("bbox", {}).get("y2", 0),
            ),
            polygon=r.get("polygon"),
            angle=float(r.get("angle", 0.0)),
            field_hint=r.get("field_hint"),
        )
        for r in raw_regions
    ]

    status_str = (
        scan.processing_status.value
        if hasattr(scan.processing_status, "value")
        else str(scan.processing_status)
    )

    return OCRProcessResponse(
        scan_id=scan.id,
        status=status_str,
        full_text=ocr_result.extracted_text,
        confidence_score=float(ocr_result.confidence or 0.0),
        ocr_engine=ocr_result.ocr_engine or "unknown",
        engine_version=proc_meta.get("engine_version", "1.0.0"),
        language=proc_meta.get("language", "en"),
        processing_time_ms=float(proc_meta.get("processing_time_ms", 0.0)),
        regions=regions,
        quality_metrics=quality_metrics,
    )


@router.get("/", response_model=List[ScanRead])
async def list_scans(
    inspection_id: Optional[str] = Query(None, description="Filter by inspection ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scans with optional filtering by inspection."""
    stmt = select(Scan)
    if inspection_id:
        stmt = stmt.where(Scan.inspection_id == inspection_id)
    stmt = stmt.order_by(desc(Scan.created_at)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{scan_id}", response_model=ScanRead)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve scan details by ID."""
    stmt = select(Scan).where(Scan.id == scan_id)
    res = await db.execute(stmt)
    scan = res.scalar_one_or_none()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' not found.",
        )
    return scan


@router.get("/{scan_id}/ocr", response_model=OCRProcessResponse)
async def get_scan_ocr_result(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve extracted OCR text, confidence scores, spatial bounding boxes,
    and image quality metrics for a completed scan.
    """
    scan_stmt = select(Scan).where(Scan.id == scan_id)
    scan_res = await db.execute(scan_stmt)
    scan = scan_res.scalar_one_or_none()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' not found.",
        )

    ocr_stmt = select(OCRResult).where(OCRResult.scan_id == scan_id)
    ocr_res = await db.execute(ocr_stmt)
    ocr_result = ocr_res.scalar_one_or_none()

    if not ocr_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OCR extraction result found for scan ID '{scan_id}'. Run process-ocr first.",
        )

    proc_meta = ocr_result.processing_metadata or {}
    raw_quality = proc_meta.get("quality_metrics", {})

    quality_metrics = ImageQualitySchema(
        sharpness_score=float(raw_quality.get("sharpness_score", 0.0)),
        is_blurry=bool(raw_quality.get("is_blurry", False)),
        brightness_mean=float(raw_quality.get("brightness_mean", 128.0)),
        is_too_dark=bool(raw_quality.get("is_too_dark", False)),
        is_too_bright=bool(raw_quality.get("is_too_bright", False)),
        contrast_score=float(raw_quality.get("contrast_score", 0.0)),
        is_low_contrast=bool(raw_quality.get("is_low_contrast", False)),
        width=int(raw_quality.get("width", 0)),
        height=int(raw_quality.get("height", 0)),
        is_low_resolution=bool(raw_quality.get("is_low_resolution", False)),
        quality_score=float(raw_quality.get("quality_score", 0.0)),
        warnings=raw_quality.get("warnings", []),
    )

    return _build_ocr_process_response(scan, ocr_result, quality_metrics)


@router.post("/{scan_id}/process-ocr", response_model=OCRProcessResponse)
async def process_scan_ocr(
    scan_id: str,
    payload: Optional[OCRProcessRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    """
    Trigger OCR and computer vision extraction pipeline for an existing scan record.
    """
    engine_name = payload.engine_name if payload else None
    language = payload.language if payload else "en"

    processor = ScanProcessorService()
    try:
        scan, ocr_result, quality = await processor.process_scan(
            db=db,
            scan_id=scan_id,
            engine_name=engine_name,
            language=language,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR pipeline processing failed: {str(exc)}",
        )

    quality_metrics = ImageQualitySchema(
        sharpness_score=quality.sharpness_score,
        is_blurry=quality.is_blurry,
        brightness_mean=quality.brightness_mean,
        is_too_dark=quality.is_too_dark,
        is_too_bright=quality.is_too_bright,
        contrast_score=quality.contrast_score,
        is_low_contrast=quality.is_low_contrast,
        width=quality.width,
        height=quality.height,
        is_low_resolution=quality.is_low_resolution,
        quality_score=quality.quality_score,
        warnings=quality.warnings,
    )

    return _build_ocr_process_response(scan, ocr_result, quality_metrics)


@router.post("/upload-and-process", response_model=ScanUploadAndProcessResponse)
async def upload_and_process_image(
    file: UploadFile = File(..., description="Package commodity label image file"),
    inspection_id: Optional[str] = Form(None, description="Optional existing inspection ID"),
    product_id: Optional[str] = Form(None, description="Optional existing product ID"),
    engine_name: Optional[str] = Form(None, description="OCR engine ('mock', 'tesseract', 'paddleocr', 'auto')"),
    language: str = Form("en", description="Target language"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    """
    Combined endpoint: Uploads image file, creates database associations,
    and runs full OCR & Computer Vision Pipeline immediately.
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

    storage = LocalStorageProvider()

    # 1. Resolve or create Product
    if product_id:
        prod_res = await db.execute(select(Product).where(Product.id == product_id))
        product = prod_res.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID '{product_id}' not found.",
            )
    else:
        # Default intake product
        product = Product(
            name="Intake Commodity Item",
            brand="Generic",
            category="Packaged Commodity",
            description="Standard Pre-packaged commodity",
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

    # 2. Resolve or create Inspection
    if inspection_id:
        insp_res = await db.execute(
            select(Inspection).where(Inspection.id == inspection_id)
        )
        inspection = insp_res.scalar_one_or_none()
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inspection with ID '{inspection_id}' not found.",
            )
    else:
        # Default intake inspection
        inspection = Inspection(
            product_id=product.id,
            status=InspectionStatusEnum.CREATED,
            notes="Automated OCR intake scan",
        )
        db.add(inspection)
        await db.commit()
        await db.refresh(inspection)

    # 3. Store uploaded file safely
    try:
        storage_info = await storage.save_file(
            file_bytes=file_bytes,
            filename=file.filename or "commodity_label.jpg",
            subfolder="labels",
        )
    except Exception as save_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist uploaded image: {str(save_err)}",
        )

    # 4. Create ProductImage record
    product_image = ProductImage(
        product_id=product.id,
        image_url_or_path=storage_info["storage_path"],
        image_type=ImageTypeEnum.FRONT_PDP,
        file_metadata={
            "original_filename": file.filename,
            "content_type": file.content_type,
            "url": storage_info["url"],
            "file_size_bytes": storage_info["file_size_bytes"],
        },
    )
    db.add(product_image)
    await db.commit()
    await db.refresh(product_image)

    # 5. Create Scan record
    scan = Scan(
        inspection_id=inspection.id,
        product_image_id=product_image.id,
        image_path=storage_info["storage_path"],
        panel_type=PanelTypeEnum.FRONT_PDP,
        processing_status=ScanStatusEnum.PENDING,
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    # 6. Run Scan Processing Pipeline
    processor = ScanProcessorService(storage_provider=storage)
    try:
        scan, ocr_result, quality = await processor.process_scan(
            db=db,
            scan_id=scan.id,
            engine_name=engine_name,
            language=language,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {str(exc)}",
        )

    quality_metrics = ImageQualitySchema(
        sharpness_score=quality.sharpness_score,
        is_blurry=quality.is_blurry,
        brightness_mean=quality.brightness_mean,
        is_too_dark=quality.is_too_dark,
        is_too_bright=quality.is_too_bright,
        contrast_score=quality.contrast_score,
        is_low_contrast=quality.is_low_contrast,
        width=quality.width,
        height=quality.height,
        is_low_resolution=quality.is_low_resolution,
        quality_score=quality.quality_score,
        warnings=quality.warnings,
    )

    ocr_response = _build_ocr_process_response(scan, ocr_result, quality_metrics)

    return ScanUploadAndProcessResponse(
        scan_id=scan.id,
        inspection_id=inspection.id,
        image_id=product_image.id,
        image_url=storage_info["url"],
        ocr_result=ocr_response,
    )
