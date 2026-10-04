import io
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.history import InspectionHistory
from app.models.inspection import Inspection, InspectionStatusEnum, OverallResultEnum
from app.models.product import Product
from app.models.rule import Rule, RuleVersion
from app.models.user import Role, RoleEnum, User


@pytest.mark.asyncio
async def test_auth_login_valid_and_invalid(async_client: AsyncClient, db_session: AsyncSession):
    # Ensure seed users are initialized
    login_payload = {
        "email": "admin@metacheck.gov.in",
        "password": "Admin@123",
    }
    res = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@metacheck.gov.in"
    assert data["user"]["role"] == "ADMIN"
    token = data["access_token"]

    # Test /api/v1/auth/me with token
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@metacheck.gov.in"

    # Test Invalid Password -> 401
    bad_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@metacheck.gov.in", "password": "WrongPassword!"},
    )
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["error"]["message"]

    # Test Unknown User -> 401
    unknown_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@metacheck.gov.in", "password": "AnyPassword"},
    )
    assert unknown_res.status_code == 401


@pytest.mark.asyncio
async def test_auth_token_revocation_and_logout(async_client: AsyncClient):
    # Login as officer
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "officer@metacheck.gov.in", "password": "Officer@123"},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Verify access works
    me_res = await async_client.get("/api/v1/auth/me", headers=auth_header)
    assert me_res.status_code == 200

    # Logout to revoke token
    logout_res = await async_client.post("/api/v1/auth/logout", headers=auth_header)
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Subsequent request with revoked token should fail with 401
    revoked_res = await async_client.get("/api/v1/auth/me", headers=auth_header)
    assert revoked_res.status_code == 401


@pytest.mark.asyncio
async def test_rbac_roles_enforcement(async_client: AsyncClient, db_session: AsyncSession):
    # Login as Admin
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@metacheck.gov.in", "password": "Admin@123"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Login as Officer
    officer_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "officer@metacheck.gov.in", "password": "Officer@123"},
    )
    officer_token = officer_login.json()["access_token"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    # Login as Viewer
    viewer_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@metacheck.gov.in", "password": "Viewer@123"},
    )
    viewer_token = viewer_login.json()["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 1. ADMIN can create a rule
    rule_res = await async_client.post(
        "/api/v1/rules",
        json={
            "rule_code": "PCR_SEC_TEST_001",
            "name": "Security Test Rule",
            "legal_reference": "PCR 2011",
        },
        headers=admin_headers,
    )
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["id"]

    # 2. OFFICER cannot create a rule -> 403 Forbidden
    off_rule = await async_client.post(
        "/api/v1/rules",
        json={"rule_code": "PCR_OFFICER_FAIL", "name": "Fail", "legal_reference": "PCR"},
        headers=officer_headers,
    )
    assert off_rule.status_code == 403

    # 3. VIEWER cannot create a rule -> 403 Forbidden
    view_rule = await async_client.post(
        "/api/v1/rules",
        json={"rule_code": "PCR_VIEWER_FAIL", "name": "Fail", "legal_reference": "PCR"},
        headers=viewer_headers,
    )
    assert view_rule.status_code == 403

    # 4. OFFICER can create a product and inspection
    prod_res = await async_client.post(
        "/api/v1/products",
        json={"name": "Fortified Rice 1kg", "brand": "GrainPlus", "category": "Food Grain", "barcode_gtin": "8901234567890"},
        headers=officer_headers,
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]

    insp_res = await async_client.post(
        "/api/v1/inspections",
        json={"product_id": product_id, "source_type": "PORTAL_UPLOAD"},
        headers=officer_headers,
    )
    assert insp_res.status_code == 201
    insp_id = insp_res.json()["id"]

    # 5. VIEWER can view product and inspection
    v_prod = await async_client.get(f"/api/v1/products/{product_id}", headers=viewer_headers)
    assert v_prod.status_code == 200

    v_insp = await async_client.get(f"/api/v1/inspections/{insp_id}", headers=viewer_headers)
    assert v_insp.status_code == 200

    # 6. VIEWER cannot update inspection status -> 403 Forbidden
    v_update = await async_client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        json={"status": "OFFICER_REVIEWED", "notes": "Viewer attempted update"},
        headers=viewer_headers,
    )
    assert v_update.status_code == 403


@pytest.mark.asyncio
async def test_product_repository_search_and_dossier(async_client: AsyncClient, db_session: AsyncSession):
    # Register products with multiple fields
    p1 = Product(
        name="Organic Almond Milk 1L",
        brand="NutriFarm",
        category="Beverages",
        manufacturer="NutriFarm Agro Pvt Ltd",
        barcode_gtin="8901112223334",
    )
    p2 = Product(
        name="Basmati Rice Gold 5kg",
        brand="RoyalGrain",
        category="Staples",
        manufacturer="Royal Agrotech",
        barcode_gtin="8905556667778",
    )
    db_session.add_all([p1, p2])
    await db_session.flush()

    insp = Inspection(
        product_id=p1.id,
        status=InspectionStatusEnum.COMPLETED,
        overall_result_placeholder=OverallResultEnum.COMPLIANT,
    )
    db_session.add(insp)
    await db_session.commit()

    # 1. Search by name
    res_name = await async_client.get("/api/v1/products?search=Almond")
    assert res_name.status_code == 200
    assert res_name.json()["total"] >= 1
    assert any("Almond" in p["name"] for p in res_name.json()["items"])

    # 2. Search by brand
    res_brand = await async_client.get("/api/v1/products?brand=RoyalGrain")
    assert res_brand.status_code == 200
    assert any(p["brand"] == "RoyalGrain" for p in res_brand.json()["items"])

    # 3. Search by barcode
    res_gtin = await async_client.get("/api/v1/products?barcode_gtin=8901112223334")
    assert res_gtin.status_code == 200
    items = res_gtin.json()["items"]
    assert len(items) >= 1
    assert items[0]["inspection_count"] >= 1
    assert items[0]["latest_inspection_status"] == "COMPLETED"
    assert items[0]["latest_compliance_result"] == "COMPLIANT"

    # 4. Fetch complete product dossier
    dossier_res = await async_client.get(f"/api/v1/products/{p1.id}/dossier")
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()
    assert dossier["product"]["id"] == p1.id
    assert len(dossier["inspections"]) >= 1
    assert dossier["latest_inspection"] is not None


@pytest.mark.asyncio
async def test_rule_version_immutability(async_client: AsyncClient, db_session: AsyncSession):
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@metacheck.gov.in", "password": "Admin@123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # Create rule
    r_res = await async_client.post(
        "/api/v1/rules",
        json={"rule_code": "PCR_IMMUTABLE_TEST", "name": "Immutable Rule", "legal_reference": "PCR"},
        headers=admin_headers,
    )
    rule_id = r_res.json()["id"]

    # Create version 1.0.0
    v1_res = await async_client.post(
        f"/api/v1/rules/{rule_id}/versions",
        json={
            "version": "1.0.0",
            "requirement_text": "Original statutory text requirement.",
            "validation_type": "PRESENCE_CHECK",
            "severity": "CRITICAL",
        },
        headers=admin_headers,
    )
    assert v1_res.status_code == 201
    v1_id = v1_res.json()["id"]

    # Attempting to publish duplicate version 1.0.0 should trigger 409 Conflict
    v1_dup = await async_client.post(
        f"/api/v1/rules/{rule_id}/versions",
        json={
            "version": "1.0.0",
            "requirement_text": "Mutated text attempt.",
            "validation_type": "FORMAT_CHECK",
            "severity": "MAJOR",
        },
        headers=admin_headers,
    )
    assert v1_dup.status_code == 409

    # Update version temporal lifecycle
    patch_res = await async_client.patch(
        f"/api/v1/rules/{rule_id}/versions/{v1_id}/status",
        json={"source_gazette_reference": "G.S.R. 777(E)"},
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["source_gazette_reference"] == "G.S.R. 777(E)"


@pytest.mark.asyncio
async def test_security_upload_size_limit(async_client: AsyncClient):
    # Try uploading file > 10MB
    oversized_data = b"0" * (11 * 1024 * 1024)  # 11MB
    files = {"file": ("huge_label.jpg", io.BytesIO(oversized_data), "image/jpeg")}

    res = await async_client.post(
        "/api/v1/scans/upload-and-process",
        files=files,
    )
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_health_and_observability(async_client: AsyncClient):
    from unittest.mock import patch
    with patch("app.api.v1.endpoints.health.check_db_health", return_value=True):
        res = await async_client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["project_name"] == "MetaCheck AI"
        assert data["version"] == "1.0.0"
        assert data["database_connected"] is True
        assert "storage" in data["services"]
        assert "ocr_engine" in data["services"]

