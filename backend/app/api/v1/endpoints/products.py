from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.history import InspectionHistory
from app.models.inspection import Inspection
from app.models.product import Product, ProductImage
from app.models.report import Report
from app.models.user import RoleEnum, User
from app.models.violation import Violation
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.product import (
    ProductCreate,
    ProductDetailRead,
    ProductDossierInspectionItem,
    ProductDossierRead,
    ProductDossierReportItem,
    ProductDossierViolationItem,
    ProductImageCreate,
    ProductImageRead,
    ProductRead,
    ProductRepositoryItem,
    ProductUpdate,
)

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[ProductRepositoryItem],
    summary="Search Packaged Commodity Repository",
    description="Retrieve paginated list of packaged products with multi-attribute search and compliance stats.",
)
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name, brand, barcode/GTIN, or manufacturer"),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer"),
    barcode_gtin: Optional[str] = Query(None, description="Filter by exact barcode / GTIN"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Product)

    if search:
        search_filter = or_(
            Product.name.ilike(f"%{search}%"),
            Product.brand.ilike(f"%{search}%"),
            Product.barcode_gtin.ilike(f"%{search}%"),
            Product.manufacturer.ilike(f"%{search}%"),
            Product.packer.ilike(f"%{search}%"),
            Product.importer.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if category:
        query = query.where(Product.category.ilike(category))

    if brand:
        query = query.where(Product.brand.ilike(f"%{brand}%"))

    if manufacturer:
        query = query.where(Product.manufacturer.ilike(f"%{manufacturer}%"))

    if barcode_gtin:
        query = query.where(Product.barcode_gtin == barcode_gtin)

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    # Enrich each product with inspection stats
    items: List[ProductRepositoryItem] = []
    for p in products:
        # Fetch inspection aggregate
        insp_q = (
            select(Inspection)
            .where(Inspection.product_id == p.id)
            .order_by(desc(Inspection.inspection_date))
        )
        insp_res = await db.execute(insp_q)
        inspections = insp_res.scalars().all()

        insp_count = len(inspections)
        latest_insp = inspections[0] if inspections else None

        items.append(
            ProductRepositoryItem(
                id=p.id,
                name=p.name,
                brand=p.brand,
                category=p.category,
                manufacturer=p.manufacturer,
                packer=p.packer,
                importer=p.importer,
                barcode_gtin=p.barcode_gtin,
                country_of_origin=p.country_of_origin,
                description=p.description,
                created_at=p.created_at,
                updated_at=p.updated_at,
                inspection_count=insp_count,
                latest_inspection_id=latest_insp.id if latest_insp else None,
                latest_inspection_status=latest_insp.status.value if latest_insp and hasattr(latest_insp.status, "value") else (str(latest_insp.status) if latest_insp else None),
                latest_compliance_result=latest_insp.overall_result_placeholder.value if latest_insp and latest_insp.overall_result_placeholder and hasattr(latest_insp.overall_result_placeholder, "value") else (str(latest_insp.overall_result_placeholder) if latest_insp and latest_insp.overall_result_placeholder else None),
                last_inspected_at=latest_insp.inspection_date if latest_insp else None,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items)) < total,
    )


@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register Packaged Product",
    description="Register a new packaged commodity in the repository.",
)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    product = Product(**product_in.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.get(
    "/{product_id}/dossier",
    response_model=ProductDossierRead,
    summary="Get Product Compliance Dossier",
    description="Retrieve complete multi-inspection history, violations, reports, and audit trail for a commodity.",
)
async def get_product_dossier(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch product with images
    prod_q = (
        select(Product)
        .options(selectinload(Product.images))
        .where(Product.id == product_id)
    )
    prod_res = await db.execute(prod_q)
    product = prod_res.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    # Fetch all inspections for this product
    insp_q = (
        select(Inspection)
        .options(
            selectinload(Inspection.inspector),
            selectinload(Inspection.violations),
        )
        .where(Inspection.product_id == product_id)
        .order_by(desc(Inspection.inspection_date))
    )
    insp_res = await db.execute(insp_q)
    inspections = insp_res.scalars().all()

    inspection_items: List[ProductDossierInspectionItem] = []
    all_violations: List[ProductDossierViolationItem] = []
    latest_insp_dict: Optional[Dict[str, Any]] = None

    for idx, insp in enumerate(inspections):
        insp_item = ProductDossierInspectionItem(
            id=insp.id,
            inspection_date=insp.inspection_date,
            status=insp.status.value if hasattr(insp.status, "value") else str(insp.status),
            overall_result=insp.overall_result_placeholder.value if insp.overall_result_placeholder and hasattr(insp.overall_result_placeholder, "value") else (str(insp.overall_result_placeholder) if insp.overall_result_placeholder else None),
            inspector_name=insp.inspector.name if insp.inspector else "Unassigned",
            violations_count=len(insp.violations),
        )
        inspection_items.append(insp_item)

        if idx == 0:
            latest_insp_dict = {
                "id": insp.id,
                "inspection_date": insp.inspection_date.isoformat(),
                "status": insp_item.status,
                "overall_result": insp_item.overall_result,
                "inspector_name": insp_item.inspector_name,
                "notes": insp.notes,
            }

        for v in insp.violations:
            all_violations.append(
                ProductDossierViolationItem(
                    id=v.id,
                    inspection_id=v.inspection_id,
                    violation_code=v.violation_code,
                    description=v.description,
                    severity=v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                    status=v.status.value if hasattr(v.status, "value") else str(v.status),
                    created_at=v.created_at,
                )
            )

    # Fetch reports for this product's inspections
    inspection_ids = [i.id for i in inspections]
    reports_items: List[ProductDossierReportItem] = []
    if inspection_ids:
        rep_q = (
            select(Report)
            .where(Report.inspection_id.in_(inspection_ids))
            .order_by(desc(Report.generated_at))
        )
        rep_res = await db.execute(rep_q)
        for r in rep_res.scalars().all():
            reports_items.append(
                ProductDossierReportItem(
                    id=r.id,
                    inspection_id=r.inspection_id,
                    report_type=r.report_type,
                    format=r.format.value if hasattr(r.format, "value") else str(r.format),
                    generated_at=r.generated_at,
                )
            )

    # Fetch audit logs related to inspections
    audit_entries: List[Dict[str, Any]] = []
    if inspection_ids:
        hist_q = (
            select(InspectionHistory)
            .options(selectinload(InspectionHistory.user))
            .where(InspectionHistory.inspection_id.in_(inspection_ids))
            .order_by(desc(InspectionHistory.timestamp))
        )
        hist_res = await db.execute(hist_q)
        for h in hist_res.scalars().all():
            audit_entries.append({
                "id": h.id,
                "inspection_id": h.inspection_id,
                "action": h.action,
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "timestamp": h.timestamp.isoformat(),
                "user_name": h.user.name if h.user else "System",
                "metadata": h.change_metadata,
            })

    return ProductDossierRead(
        product=ProductDetailRead.model_validate(product),
        inspections=inspection_items,
        latest_inspection=latest_insp_dict,
        violations=all_violations,
        reports=reports_items,
        audit_history=audit_entries,
    )


@router.get(
    "/{product_id}",
    response_model=ProductDetailRead,
    summary="Get Product Details",
    description="Retrieve product information with registered package images.",
)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Product).options(selectinload(Product.images)).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )
    return ProductDetailRead.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update Product",
    description="Update metadata and attributes of an existing product.",
)
async def update_product(
    product_id: str,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Delete Product",
    description="Remove a packaged commodity from the repository.",
)
async def delete_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value)),
):
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    await db.delete(product)
    await db.commit()
    return MessageResponse(message=f"Product '{product_id}' deleted successfully")


@router.post(
    "/{product_id}/images",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Product Image Reference",
)
async def add_product_image(
    product_id: str,
    image_in: ProductImageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    # Verify product exists
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    image = ProductImage(product_id=product_id, **image_in.model_dump())
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return ProductImageRead.model_validate(image)
