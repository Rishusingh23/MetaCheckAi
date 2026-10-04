"""
SIH Demonstration Endpoints for MetaCheck AI.
Provides controlled sample label downloads and one-click real pipeline seeding
for live evaluation during Smart India Hackathon.
"""
import base64
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.config import settings
from app.models.user import RoleEnum, User
from app.services.demo.label_generator import (
    generate_blurry_review_label,
    generate_compliant_label,
    generate_missing_manufacturer_label,
    generate_non_compliant_mrp_label,
    generate_non_metric_quantity_label,
)
from app.services.demo.seeder import demo_seeder_service

router = APIRouter()


@router.get(
    "/samples",
    summary="List Controlled Demo Label Scenarios",
    description="Returns metadata and descriptions for the 5 legal metrology demonstration scenarios.",
)
async def list_demo_samples():
    return [
        {
            "id": "sample_a",
            "name": "Sample A: Compliant Potato Wafers",
            "brand": "Himalayan Crunch",
            "category": "Food & Snacks",
            "expected_outcome": "COMPLIANT",
            "description": "All mandatory declarations present: MRP ₹ 40.00 (Incl. of all taxes), Net Qty: 200 g, USP: ₹ 0.20/g, Mfg address, Consumer Care, Country of Origin: India.",
        },
        {
            "id": "sample_b",
            "name": "Sample B: Missing Manufacturer Address",
            "brand": "Royal Darjeeling",
            "category": "Beverages",
            "expected_outcome": "POTENTIAL_NON_COMPLIANCE",
            "expected_violation": "VIOL_PCR_2011_RULE_6_1_A",
            "description": "Packaged leaf tea missing mandatory manufacturer/packer/importer name and complete address required under Rule 6(1)(a).",
        },
        {
            "id": "sample_c",
            "name": "Sample C: Non-Compliant MRP without Tax Clause",
            "brand": "Pure Almond",
            "category": "Dairy & Alternatives",
            "expected_outcome": "POTENTIAL_NON_COMPLIANCE",
            "expected_violation": "VIOL_PCR_2011_RULE_6_1_E",
            "description": "Retail drink with 'MRP Rs 150.00' missing mandatory statutory clause 'inclusive of all taxes' under Rule 6(1)(e).",
        },
        {
            "id": "sample_d",
            "name": "Sample D: Non-Metric Quantity Units",
            "brand": "Organic Basmati",
            "category": "Grains & Staples",
            "expected_outcome": "POTENTIAL_NON_COMPLIANCE",
            "expected_violation": "VIOL_PCR_2011_RULE_13",
            "description": "Rice package declared in non-standard non-metric units 'Net Wt. 2 LBS / 32 OZ' violating mandatory metric units under Rule 13 / Sched III.",
        },
        {
            "id": "sample_e",
            "name": "Sample E: Blurry / Insufficient Evidence",
            "brand": "Golden Harvest",
            "category": "Bakery",
            "expected_outcome": "REVIEW_REQUIRED",
            "description": "Severe Gaussian blur causing low OCR confidence. Produces Advisory Review instead of false legal failure.",
        },
    ]


@router.get(
    "/samples/{sample_id}/image",
    summary="Download Sample Label Image",
    description="Returns the raw PNG/JPEG image for the requested sample scenario.",
)
async def get_sample_image(sample_id: str):
    mapping = {
        "sample_a": generate_compliant_label,
        "sample_b": generate_missing_manufacturer_label,
        "sample_c": generate_non_compliant_mrp_label,
        "sample_d": generate_non_metric_quantity_label,
        "sample_e": generate_blurry_review_label,
    }
    if sample_id not in mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample scenario '{sample_id}' not found.",
        )

    img_bytes, meta = mapping[sample_id]()
    media_type = "image/jpeg" if sample_id == "sample_e" else "image/png"
    return Response(content=img_bytes, media_type=media_type)


@router.post(
    "/seed-samples",
    summary="Seed 5 Demo Inspections",
    description="Executes the full real-world pipeline on all 5 sample label packages (ADMIN or OFFICER).",
)
async def seed_demo_samples(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN.value, RoleEnum.ENFORCEMENT_OFFICER.value)),
):
    if not settings.DEMO_DATA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo data seeding is disabled on this environment (DEMO_DATA_ENABLED=false).",
        )

    seeded_records = await demo_seeder_service.seed_demo_inspections(db=db, inspector=current_user)
    return {
        "message": f"Successfully executed full real inspection pipeline for {len(seeded_records)} demonstration packages.",
        "records": seeded_records,
    }
