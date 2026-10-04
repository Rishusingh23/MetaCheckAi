import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.models.declaration import (
    Declaration,
    DeclarationTypeEnum,
    ExtractionStatusEnum,
)
from app.models.ocr import OCRResult
from app.models.scan import Scan
from app.models.user import RoleEnum, User
from app.schemas.declaration_extraction import (
    DeclarationItemSchema,
    DeclarationUpdatePayload,
    ScanDeclarationsResponse,
)
from app.services.declarations.extractor import DeclarationExtractorService
from app.services.ocr.models import BoundingBox, OCRRegion

logger = logging.getLogger(__name__)

router = APIRouter()


def _map_declaration_to_schema(d: Declaration) -> DeclarationItemSchema:
    decl_type = (
        d.declaration_type
        if isinstance(d.declaration_type, DeclarationTypeEnum)
        else DeclarationTypeEnum(str(d.declaration_type))
    )
    status_enum = (
        d.extraction_status
        if isinstance(d.extraction_status, ExtractionStatusEnum)
        else ExtractionStatusEnum(str(d.extraction_status))
    )
    return DeclarationItemSchema(
        id=d.id,
        scan_id=d.scan_id,
        declaration_type=decl_type,
        raw_value=d.raw_value,
        normalized_value=d.normalized_value,
        confidence=d.confidence,
        source_text=d.source_text,
        bounding_box=d.bounding_box,
        extraction_status=status_enum,
        created_at=d.created_at,
    )


@router.post("/scans/{scan_id}/extract-declarations", response_model=ScanDeclarationsResponse)
async def extract_declarations_for_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    """
    Execute Legal Metrology declaration extraction and value normalization on a completed scan.
    Identifies MRP, Net Quantity, Dates, Manufacturer/Packer/Importer, Consumer Care, Origin, etc.
    """
    # 1. Verify Scan exists
    scan_res = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_res.scalar_one_or_none()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' not found.",
        )

    # 2. Verify OCRResult exists
    ocr_res = await db.execute(select(OCRResult).where(OCRResult.scan_id == scan_id))
    ocr_result = ocr_res.scalar_one_or_none()
    if not ocr_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No OCR extraction result found for scan ID '{scan_id}'. Run process-ocr first.",
        )

    # 3. Reconstruct OCRRegion objects from stored structured bounding box data
    raw_boxes = ocr_result.bounding_boxes or {}
    raw_regions = raw_boxes.get("regions", [])

    ocr_regions = []
    for r in raw_regions:
        bbox_dict = r.get("bbox", {})
        ocr_regions.append(
            OCRRegion(
                text=r.get("text", ""),
                confidence=float(r.get("confidence", 0.0)),
                bbox=BoundingBox(
                    x1=int(bbox_dict.get("x1", 0)),
                    y1=int(bbox_dict.get("y1", 0)),
                    x2=int(bbox_dict.get("x2", 0)),
                    y2=int(bbox_dict.get("y2", 0)),
                ),
                polygon=r.get("polygon"),
                angle=float(r.get("angle", 0.0)),
                field_hint=r.get("field_hint"),
            )
        )

    full_text = ocr_result.extracted_text or ""

    # 4. Run Declaration Extraction Service
    extractor = DeclarationExtractorService()
    candidates = await extractor.extract_declarations(full_text=full_text, regions=ocr_regions)
    saved_entities = await extractor.persist_declarations_for_scan(
        db=db,
        scan_id=scan_id,
        candidates=candidates,
    )

    total = len(saved_entities)
    mean_conf = (
        sum(float(d.confidence or 0.0) for d in saved_entities) / total if total > 0 else 0.0
    )

    items = [_map_declaration_to_schema(d) for d in saved_entities]

    return ScanDeclarationsResponse(
        scan_id=scan_id,
        status="COMPLETED",
        total_declarations=total,
        mean_confidence=round(mean_conf, 4),
        declarations=items,
    )


@router.get("/scans/{scan_id}/declarations", response_model=ScanDeclarationsResponse)
async def get_declarations_for_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve stored Legal Metrology declarations and bounding box metadata for a scan.
    """
    scan_res = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_res.scalar_one_or_none()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID '{scan_id}' not found.",
        )

    stmt = (
        select(Declaration)
        .where(Declaration.scan_id == scan_id)
        .order_by(desc(Declaration.confidence))
    )
    res = await db.execute(stmt)
    declarations = res.scalars().all()

    total = len(declarations)
    mean_conf = (
        sum(float(d.confidence or 0.0) for d in declarations) / total
        if total > 0
        else 0.0
    )

    items = [_map_declaration_to_schema(d) for d in declarations]

    return ScanDeclarationsResponse(
        scan_id=scan_id,
        status="COMPLETED",
        total_declarations=total,
        mean_confidence=round(mean_conf, 4),
        declarations=items,
    )


@router.get("/declarations/{declaration_id}", response_model=DeclarationItemSchema)
async def get_declaration_by_id(
    declaration_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific declaration by ID.
    """
    res = await db.execute(select(Declaration).where(Declaration.id == declaration_id))
    declaration = res.scalar_one_or_none()
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Declaration with ID '{declaration_id}' not found.",
        )
    return _map_declaration_to_schema(declaration)


@router.patch("/declarations/{declaration_id}", response_model=DeclarationItemSchema)
async def update_declaration(
    declaration_id: str,
    payload: DeclarationUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    """
    Update / manually verify an extracted declaration value.
    Preserves original raw_value and logs manual edit audit flag.
    """
    res = await db.execute(select(Declaration).where(Declaration.id == declaration_id))
    declaration = res.scalar_one_or_none()
    if not declaration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Declaration with ID '{declaration_id}' not found.",
        )

    if payload.normalized_value is not None:
        declaration.normalized_value = payload.normalized_value

    if payload.extraction_status is not None:
        declaration.extraction_status = payload.extraction_status

    # Preserve edit history in bounding box metadata
    existing_meta = dict(declaration.bounding_box or {})
    existing_meta["is_manually_edited"] = True
    if payload.notes:
        existing_meta["officer_notes"] = payload.notes
    declaration.bounding_box = existing_meta

    await db.commit()
    await db.refresh(declaration)

    return _map_declaration_to_schema(declaration)
