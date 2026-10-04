import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.declaration import Declaration, DeclarationTypeEnum, ExtractionStatusEnum
from app.models.inspection import Inspection, InspectionSourceEnum, InspectionStatusEnum
from app.models.product import Product
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.models.user import Role, User


@pytest.mark.asyncio
async def test_compliance_evaluation_endpoints_workflow(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    # 1. Seed rules baseline
    seed_res = await async_client.post("/api/v1/rules/seed-baseline")
    assert seed_res.status_code == 200
    assert "seeded/verified" in seed_res.json()["message"]

    # 2. Setup product, inspection, scan, and declarations
    role = Role(name="OFFICER_COMPLIANCE", description="Officer")
    db_session.add(role)
    await db_session.flush()

    user = User(
        email="compliance_officer@metacheck.gov.in",
        name="Officer Verma",
        password_hash="hash",
        role_id=role.id,
    )
    db_session.add(user)

    product = Product(
        name="Tata Tea Premium 500g",
        brand="Tata Tea",
        category="Tea & Beverages",
    )
    db_session.add(product)
    await db_session.flush()

    inspection = Inspection(
        product_id=product.id,
        inspector_id=user.id,
        status=InspectionStatusEnum.CREATED,
        source_type=InspectionSourceEnum.PORTAL_UPLOAD,
        inspection_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    await db_session.flush()

    scan = Scan(
        inspection_id=inspection.id,
        image_path="/storage/scans/tea.jpg",
        panel_type=PanelTypeEnum.BACK_DECLARATION,
        processing_status=ScanStatusEnum.COMPLETED,
    )
    db_session.add(scan)
    await db_session.flush()

    decl_qty = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="Net Qty: 500g",
        normalized_value="500 g",
        confidence=0.98,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    decl_mrp = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.MRP,
        raw_value="MRP Rs. 320.00 (Incl. of all taxes)",
        normalized_value="₹ 320.00 (Incl. of all taxes)",
        confidence=0.95,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    db_session.add_all([decl_qty, decl_mrp])
    await db_session.commit()

    # 3. Trigger Evaluation via POST /api/v1/inspections/{id}/evaluate
    eval_res = await async_client.post(
        f"/api/v1/inspections/{inspection.id}/evaluate",
        json={"notes": "Initiated automated statutory screening"},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["inspection_id"] == inspection.id
    assert eval_data["total_rules_evaluated"] >= 8
    assert eval_data["pass_count"] >= 2
    assert "disclaimer" in eval_data

    # 4. Fetch Compliance Dossier via GET /api/v1/inspections/{id}/compliance
    dossier_res = await async_client.get(f"/api/v1/inspections/{inspection.id}/compliance")
    assert dossier_res.status_code == 200
    dossier_data = dossier_res.json()
    assert dossier_data["inspection_id"] == inspection.id
    assert len(dossier_data["checks"]) == eval_data["total_rules_evaluated"]


@pytest.mark.asyncio
async def test_evaluate_nonexistent_inspection_404(async_client: AsyncClient):
    res = await async_client.post("/api/v1/inspections/nonexistent-id-9999/evaluate")
    assert res.status_code == 404

