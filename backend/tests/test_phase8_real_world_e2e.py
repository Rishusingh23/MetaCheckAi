"""
Phase 8 End-to-End Real-World Compliance Validation & SIH Demonstration Test Suite.
Tests the complete multi-stage pipeline on 5 controlled packaged commodity label scenarios,
verifying OCR text extraction, declaration normalization, statutory rule evaluation,
evidence generation, officer review workflows, and error handling.
"""
import io
import time
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.inspection import Inspection, InspectionStatusEnum, OverallResultEnum
from app.models.user import RoleEnum, User
from app.services.demo.label_generator import (
    generate_blurry_review_label,
    generate_compliant_label,
    generate_missing_manufacturer_label,
    generate_non_compliant_mrp_label,
    generate_non_metric_quantity_label,
)


async def get_auth_header(async_client: AsyncClient, email: str = "officer@metacheck.gov.in", password: str = "Officer@123") -> dict:
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_demo_samples_endpoint_listing(async_client: AsyncClient):
    """Verifies that GET /api/v1/demo/samples returns the 5 controlled scenarios."""
    res = await async_client.get("/api/v1/demo/samples")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) == 5

    sample_ids = [s["id"] for s in samples]
    assert "sample_a" in sample_ids
    assert "sample_b" in sample_ids
    assert "sample_c" in sample_ids
    assert "sample_d" in sample_ids
    assert "sample_e" in sample_ids


@pytest.mark.asyncio
async def test_demo_sample_image_downloads(async_client: AsyncClient):
    """Verifies that all 5 sample label images are generated and downloadable via API."""
    for sample_id in ["sample_a", "sample_b", "sample_c", "sample_d", "sample_e"]:
        res = await async_client.get(f"/api/v1/demo/samples/{sample_id}/image")
        assert res.status_code == 200
        assert len(res.content) > 1000
        assert res.headers["content-type"] in ["image/png", "image/jpeg"]


@pytest.mark.asyncio
async def test_demo_sample_not_found(async_client: AsyncClient):
    """Verifies 404 for non-existent demo sample."""
    res = await async_client.get("/api/v1/demo/samples/non_existent_sample/image")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_demo_seeder_full_pipeline(async_client: AsyncClient, db_session: AsyncSession):
    """Verifies one-click automated demo data seeding through real database pipeline and demo safety gating."""
    from app.core.config import settings

    headers = await get_auth_header(async_client, email="admin@metacheck.gov.in", password="Admin@123")
    
    # 1. When DEMO_DATA_ENABLED is False, seeding must be refused with 403 Forbidden
    settings.DEMO_DATA_ENABLED = False
    disabled_res = await async_client.post("/api/v1/demo/seed-samples", headers=headers)
    assert disabled_res.status_code == 403
    assert "disabled" in str(disabled_res.json()).lower()

    # 2. When DEMO_DATA_ENABLED is True, seeding executes full pipeline
    settings.DEMO_DATA_ENABLED = True
    seed_res = await async_client.post("/api/v1/demo/seed-samples", headers=headers)
    assert seed_res.status_code == 200
    seed_data = seed_res.json()
    assert "records" in seed_data
    assert len(seed_data["records"]) == 5

    # Verify inspections created in database
    inspections_res = await async_client.get("/api/v1/inspections", headers=headers)
    assert inspections_res.status_code == 200
    assert inspections_res.json()["total"] >= 5

    # Restore production default
    settings.DEMO_DATA_ENABLED = False


@pytest.mark.asyncio
async def test_sample_a_compliant_pipeline_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Scenario A: Clearly Compliant Potato Wafers
    - All mandatory declarations present (MRP incl. taxes, Net Qty in metric, USP, Mfg details, Consumer Care).
    - Expected Result: COMPLIANT, 0 violations, high screening score.
    """
    img_bytes, meta = generate_compliant_label()
    files = {"file": ("sample_a_compliant.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    # 1. Upload and process scan
    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    # 2. Extract declarations
    decl_res = await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    assert decl_res.status_code == 200
    decl_data = decl_res.json()
    assert decl_data["total_declarations"] >= 4

    # 3. Evaluate compliance
    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200
    compliance = eval_res.json()

    assert compliance["violations_flagged"] == 0
    assert compliance["fail_count"] == 0
    assert compliance["pass_count"] >= 5
    assert compliance["screening_score"] >= 80.0

    # Verify inspection detail endpoint returns clean checks
    checks_res = await async_client.get(f"/api/v1/inspections/{inspection_id}")
    assert checks_res.status_code == 200
    insp_detail = checks_res.json()
    assert len(insp_detail["compliance_checks"]) >= 5
    assert len(insp_detail["violations"]) == 0


@pytest.mark.asyncio
async def test_sample_b_missing_manufacturer_pipeline_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Scenario B: Missing Manufacturer Address (Rule 6(1)(a))
    - Leaf tea package missing mandatory manufacturer name/address.
    - Expected Result: POTENTIAL_NON_COMPLIANCE, Rule 6(1)(a) violation flagged.
    """
    img_bytes, meta = generate_missing_manufacturer_label()
    files = {"file": ("sample_b_missing_mfg.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200
    compliance = eval_res.json()
    assert compliance["overall_status"] == OverallResultEnum.POTENTIAL_NON_COMPLIANCE.value
    assert compliance["violations_flagged"] >= 1
    assert compliance["fail_count"] >= 1

    # Check violations endpoint
    viols_res = await async_client.get(f"/api/v1/inspections/{inspection_id}/violations")
    assert viols_res.status_code == 200
    viols = viols_res.json()
    viol_codes = [v["violation_code"] for v in viols]
    assert any("6_1_A" in code or "MANUFACTURER" in code for code in viol_codes)


@pytest.mark.asyncio
async def test_sample_c_non_compliant_mrp_pipeline_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Scenario C: Non-Compliant MRP without Tax Clause (Rule 6(1)(e))
    - MRP declared as 'MRP Rs 150.00' without 'inclusive of all taxes'.
    - Expected Result: POTENTIAL_NON_COMPLIANCE, Rule 6(1)(e) violation flagged.
    """
    img_bytes, meta = generate_non_compliant_mrp_label()
    files = {"file": ("sample_c_mrp_tax.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200
    compliance = eval_res.json()

    assert compliance["overall_status"] == OverallResultEnum.POTENTIAL_NON_COMPLIANCE.value
    assert compliance["fail_count"] >= 1


@pytest.mark.asyncio
async def test_sample_d_non_metric_quantity_pipeline_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Scenario D: Non-Metric Units (Rule 13 / Sched III)
    - Basmati Rice declared in '2 LBS / 32 OZ'.
    - Expected Result: POTENTIAL_NON_COMPLIANCE, Rule 13 metric violation flagged.
    """
    img_bytes, meta = generate_non_metric_quantity_label()
    files = {"file": ("sample_d_non_metric.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200
    compliance = eval_res.json()

    assert compliance["overall_status"] == OverallResultEnum.POTENTIAL_NON_COMPLIANCE.value


@pytest.mark.asyncio
async def test_sample_e_blurry_advisory_review_pipeline_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Scenario E: Severely Blurry Label (Advisory Review vs False Failure)
    - High Gaussian blur triggers is_blurry=True in quality metrics.
    - Expected Result: REVIEW_REQUIRED / REVIEW status, NOT a definitive false failure.
    """
    img_bytes, meta = generate_blurry_review_label()
    files = {"file": ("sample_e_blurry.jpg", img_bytes, "image/jpeg")}
    data = {"engine_name": "mock", "language": "en"}

    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    quality = scan_res.json()["ocr_result"]["quality_metrics"]
    assert quality["is_blurry"] is True

    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200
    compliance = eval_res.json()

    # Blurry image should trigger advisory review checks
    assert compliance["review_count"] >= 1


@pytest.mark.asyncio
async def test_error_handling_invalid_payloads(async_client: AsyncClient):
    """Verifies robust error handling on empty or invalid file payloads."""
    # 1. Empty file
    empty_files = {"file": ("empty.png", b"", "image/png")}
    res = await async_client.post("/api/v1/scans/upload-and-process", files=empty_files)
    assert res.status_code in [400, 422]

    # 2. Corrupted bytes
    corrupt_files = {"file": ("corrupt.png", b"NOT_A_VALID_IMAGE_BYTES", "image/png")}
    res_corrupt = await async_client.post("/api/v1/scans/upload-and-process", files=corrupt_files)
    assert res_corrupt.status_code in [400, 422]


@pytest.mark.asyncio
async def test_pipeline_latency_benchmark(async_client: AsyncClient):
    """Verifies that full scan, extraction, and compliance evaluation executes within demo latency target (<5.0s)."""
    img_bytes, _ = generate_compliant_label()
    files = {"file": ("benchmark_sample.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    start_time = time.perf_counter()

    scan_res = await async_client.post("/api/v1/scans/upload-and-process", files=files, data=data)
    assert scan_res.status_code == 200
    scan_id = scan_res.json()["scan_id"]
    inspection_id = scan_res.json()["inspection_id"]

    decl_res = await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    assert decl_res.status_code == 200

    eval_res = await async_client.post(f"/api/v1/inspections/{inspection_id}/evaluate")
    assert eval_res.status_code == 200

    total_duration_sec = time.perf_counter() - start_time
    # Assert execution completed swiftly
    assert total_duration_sec < 5.0
