"""
Unit and integration tests for Phase 6 Inspection Enforcement Workflow and Review.
Tests RBAC permissions, status transitions, violation officer confirmation/dismissal,
mandatory comments, and audit history logging.
"""
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.user import RoleEnum


@pytest.mark.asyncio
async def test_inspection_status_transitions_and_history(async_client: AsyncClient):
    """Verify inspection lifecycle transitions and audit trail."""
    client = async_client

    # 1. Create product
    prod_res = await client.post(
        "/api/v1/products",
        json={
            "name": "Audit Test Biscuits 200g",
            "brand": "AuditBrand",
            "category": "Food & Beverages",
            "barcode_gtin": "8901234567890",
        },
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # 2. Create inspection
    insp_res = await client.post(
        "/api/v1/inspections",
        json={
            "product_id": prod_id,
            "source_type": "FIELD_SCANNER",
            "notes": "Initial physical audit on site",
        },
    )
    assert insp_res.status_code == 201
    insp_data = insp_res.json()
    insp_id = insp_data["id"]
    assert insp_data["status"] == "CREATED"

    # 3. Transition to PROCESSING
    stat_res = await client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        json={"status": "PROCESSING", "notes": "Scanning and OCR processing started"},
    )
    assert stat_res.status_code == 200
    assert stat_res.json()["status"] == "PROCESSING"

    # 4. Transition to REVIEW_REQUIRED
    stat_res2 = await client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        json={"status": "REVIEW_REQUIRED", "notes": "Automated evaluation detected potential non-compliance"},
    )
    assert stat_res2.status_code == 200
    assert stat_res2.json()["status"] == "REVIEW_REQUIRED"

    # 5. Check audit history trail
    hist_res = await client.get(f"/api/v1/inspections/{insp_id}/history")
    assert hist_res.status_code == 200
    history_items = hist_res.json()
    assert len(history_items) >= 3
    actions = [h["action"] for h in history_items]
    assert "INSPECTION_CREATED" in actions
    assert "STATUS_TRANSITION" in actions


@pytest.mark.asyncio
async def test_violation_review_officer_confirmed_and_dismissed(async_client: AsyncClient):
    """Verify enforcement officer review workflow on flagged violations."""
    client = async_client

    # Create product & inspection
    p_res = await client.post(
        "/api/v1/products",
        json={"name": "Atta Flour 5kg", "brand": "GrainMills", "category": "Grocery"},
    )
    prod_id = p_res.json()["id"]

    i_res = await client.post(
        "/api/v1/inspections",
        json={"product_id": prod_id, "source_type": "FIELD_SCANNER"},
    )
    insp_id = i_res.json()["id"]

    # Create two flagged violations
    v1_res = await client.post(
        "/api/v1/violations",
        json={
            "inspection_id": insp_id,
            "violation_code": "VIOL_MISSING_USP",
            "description": "Missing Unit Sale Price declaration on principal panel.",
            "severity": "MAJOR",
            "status": "FLAGGED_FOR_REVIEW",
        },
    )
    assert v1_res.status_code == 201
    v1_id = v1_res.json()["id"]

    v2_res = await client.post(
        "/api/v1/violations",
        json={
            "inspection_id": insp_id,
            "violation_code": "VIOL_BLURRY_DATE",
            "description": "Ambiguous manufacturing date characters due to glare.",
            "severity": "MINOR",
            "status": "FLAGGED_FOR_REVIEW",
        },
    )
    assert v2_res.status_code == 201
    v2_id = v2_res.json()["id"]

    # 1. Review v1: Confirm with officer rationale
    rev1_res = await client.patch(
        f"/api/v1/violations/{v1_id}/review",
        json={
            "status": "OFFICER_CONFIRMED",
            "comment": "Verified physically: no USP declaration printed anywhere on retail package.",
        },
    )
    assert rev1_res.status_code == 200
    v1_data = rev1_res.json()
    assert v1_data["status"] == "OFFICER_CONFIRMED"
    assert "no USP declaration" in v1_data["officer_comment"]
    assert v1_data["reviewed_by"] is not None
    assert v1_data["reviewed_at"] is not None

    # 2. Review v2: Dismiss with explanation
    rev2_res = await client.patch(
        f"/api/v1/violations/{v2_id}/review",
        json={
            "status": "DISMISSED",
            "comment": "Officer physically inspected packaging under direct lighting; date MFG 08/2026 is legible.",
        },
    )
    assert rev2_res.status_code == 200
    v2_data = rev2_res.json()
    assert v2_data["status"] == "DISMISSED"

    # 3. Check that inspection status automatically transitioned to OFFICER_REVIEWED
    insp_detail = await client.get(f"/api/v1/inspections/{insp_id}")
    assert insp_detail.status_code == 200
    insp_json = insp_detail.json()
    assert insp_json["status"] == "OFFICER_REVIEWED"

    # 4. Check violations list endpoint for inspection
    viols_res = await client.get(f"/api/v1/inspections/{insp_id}/violations")
    assert viols_res.status_code == 200
    viols = viols_res.json()
    assert len(viols) == 2


@pytest.mark.asyncio
async def test_violation_review_validation_errors(async_client: AsyncClient):
    """Verify validation when reviewing violations (empty comments, invalid status)."""
    client = async_client

    # Create product & inspection
    p_res = await client.post("/api/v1/products", json={"name": "Snack Chips", "brand": "Crispy", "category": "Snacks"})
    prod_id = p_res.json()["id"]

    i_res = await client.post("/api/v1/inspections", json={"product_id": prod_id, "source_type": "PORTAL_UPLOAD"})
    insp_id = i_res.json()["id"]

    v_res = await client.post(
        "/api/v1/violations",
        json={
            "inspection_id": insp_id,
            "violation_code": "VIOL_TEST",
            "description": "Test violation",
        },
    )
    v_id = v_res.json()["id"]

    # Empty comment should fail with 400 or 422
    bad_comment_res = await client.patch(
        f"/api/v1/violations/{v_id}/review",
        json={"status": "OFFICER_CONFIRMED", "comment": "  "},
    )
    assert bad_comment_res.status_code in (400, 422)

    # Invalid target status (e.g. FLAGGED_FOR_REVIEW) should fail with 400
    bad_status_res = await client.patch(
        f"/api/v1/violations/{v_id}/review",
        json={"status": "FLAGGED_FOR_REVIEW", "comment": "Valid comment but bad status"},
    )
    assert bad_status_res.status_code == 400


@pytest.mark.asyncio
async def test_rbac_authorization(async_client: AsyncClient):
    """Verify that VIEWER role is rejected (403) from updating inspection status or reviewing violations."""
    client = async_client

    # 1. Create a viewer user
    role_res = await client.post(
        "/api/v1/roles",
        json={"name": "VIEWER", "description": "Read only viewer"},
    )
    role_id = role_res.json()["id"] if role_res.status_code == 201 else None
    if not role_id:
        roles_list = await client.get("/api/v1/roles")
        for r in roles_list.json():
            if r["name"] == "VIEWER":
                role_id = r["id"]
                break

    viewer_res = await client.post(
        "/api/v1/users",
        json={
            "email": "viewer_audit@metacheck.gov.in",
            "name": "Audit Read-Only User",
            "password": "secretpassword",
            "role_id": role_id,
        },
    )
    assert viewer_res.status_code == 201
    viewer_id = viewer_res.json()["id"]

    viewer_token = create_access_token(
        subject=viewer_id,
        claims={"email": "viewer_audit@metacheck.gov.in", "role": RoleEnum.VIEWER.value, "name": "Audit Read-Only User"},
    )
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Create product, inspection & violation
    p = await client.post("/api/v1/products", json={"name": "RBAC Test Item", "brand": "BrandX", "category": "General"})
    i = await client.post("/api/v1/inspections", json={"product_id": p.json()["id"], "source_type": "PORTAL_UPLOAD"})
    insp_id = i.json()["id"]

    v = await client.post(
        "/api/v1/violations",
        json={"inspection_id": insp_id, "violation_code": "VIOL_RBAC", "description": "Test"},
    )
    viol_id = v.json()["id"]

    # 2. Attempt review using VIEWER headers -> Should be 403 Forbidden
    unauth_review = await client.patch(
        f"/api/v1/violations/{viol_id}/review",
        json={"status": "OFFICER_CONFIRMED", "comment": "Attempt by viewer"},
        headers=viewer_headers,
    )
    assert unauth_review.status_code == 403

    # 3. Attempt status update using VIEWER headers -> Should be 403 Forbidden
    unauth_status = await client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        json={"status": "OFFICER_REVIEWED", "notes": "Viewer attempt"},
        headers=viewer_headers,
    )
    assert unauth_status.status_code == 403
