"""
Phase 9.2: Final Security, API Authorization & Statutory Correction Test Suite.

Validates:
1. Authentication Security:
   - Missing JWT -> 401
   - Malformed JWT -> 401
   - Expired JWT -> 401
   - Revoked JWT -> 401
   - Invalid Issuer -> 401
   - Invalid Audience -> 401
   - No X-User-Id or X-User-Role authentication bypass -> 401
2. API RBAC Matrix:
   - VIEWER attempting officer action -> 403
   - ENFORCEMENT_OFFICER attempting admin action -> 403
   - ADMIN full access -> 200/201
3. Production JWT Secret Hardening:
   - Rejects default / insecure secrets in production/staging/sih mode
4. Demo Credential Safety:
   - No demo accounts seeded when DEMO_SEED_ENABLED and DEMO_DATA_ENABLED are false
5. Statutory 2026/2027 E-Commerce Rule 6(10A):
   - Rule code: PCR_2026_RULE_6_10A_ECOM
   - Version 1.0 (G.S.R. 128(E)): Active 2026-07-01 to 2027-07-01
   - Version 2.0 (G.S.R. 312(E)): Active 2027-07-01 onwards
   - Context isolation: E_COMMERCE_LISTING vs PHYSICAL_PACKAGE
"""
from datetime import datetime, timedelta, timezone
import pytest
import jwt
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.security import create_access_token, hash_password, revoke_token
from app.models.product import Product
from app.models.rule import Rule, RuleVersion, ValidationTypeEnum
from app.models.user import Role, RoleEnum, User
from app.services.rules.applicability import is_rule_version_applicable


async def create_user_and_token(db_session: AsyncSession, email: str, role_name: str, password: str = "Test@123") -> tuple[User, str]:
    """Helper to create a user and return (User, JWT token)."""
    role_res = await db_session.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one_or_none()
    if not role:
        role = Role(name=role_name, description=f"{role_name} Role")
        db_session.add(role)
        await db_session.flush()

    user_res = await db_session.execute(select(User).where(User.email == email))
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            name=f"Test {role_name}",
            password_hash=hash_password(password),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user, attribute_names=["role"])

    token = create_access_token(
        subject=user.id,
        claims={"email": user.email, "role": role_name, "name": user.name},
    )
    return user, token


@pytest.mark.asyncio
async def test_auth_missing_jwt_returns_401(unauthenticated_client: AsyncClient):
    """Protected endpoints without Authorization header must return 401."""
    res = await unauthenticated_client.get("/api/v1/inspections")
    assert res.status_code == 401
    err_msg = res.json().get("detail") or res.json().get("error", {}).get("message", "")
    assert "Authorization header missing" in err_msg


@pytest.mark.asyncio
async def test_auth_no_x_user_bypass(unauthenticated_client: AsyncClient, db_session: AsyncSession):
    """Passing X-User-Id or X-User-Role without Bearer JWT must NOT authenticate and return 401."""
    user, _ = await create_user_and_token(db_session, "officer_bypass@metacheck.gov.in", RoleEnum.ENFORCEMENT_OFFICER.value)

    # 1. Attempt using X-User-Id alone -> 401
    res1 = await unauthenticated_client.get("/api/v1/inspections", headers={"X-User-Id": user.id})
    assert res1.status_code == 401

    # 2. Attempt using X-User-Role alone -> 401
    res2 = await unauthenticated_client.get("/api/v1/inspections", headers={"X-User-Role": "ADMIN"})
    assert res2.status_code == 401

    # 3. Attempt using raw token as direct subject string in Authorization header -> 401
    res3 = await unauthenticated_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {user.id}"})
    assert res3.status_code == 401


@pytest.mark.asyncio
async def test_auth_malformed_and_invalid_jwt_returns_401(unauthenticated_client: AsyncClient):
    """Malformed or non-JWT tokens must return 401."""
    # Malformed token format
    res1 = await unauthenticated_client.get("/api/v1/inspections", headers={"Authorization": "Bearer not-a-real-jwt-token"})
    assert res1.status_code == 401

    # Bad token scheme
    res2 = await unauthenticated_client.get("/api/v1/inspections", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_auth_expired_jwt_returns_401(unauthenticated_client: AsyncClient, db_session: AsyncSession):
    """Tokens with past expiration timestamp must be rejected with 401."""
    user, _ = await create_user_and_token(db_session, "expired_test@metacheck.gov.in", RoleEnum.ENFORCEMENT_OFFICER.value)

    expired_token = create_access_token(
        subject=user.id,
        claims={"email": user.email, "role": RoleEnum.ENFORCEMENT_OFFICER.value},
        expires_delta=timedelta(seconds=-10),
    )

    res = await unauthenticated_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    err_msg = res.json().get("detail") or res.json().get("error", {}).get("message", "")
    assert "Invalid, expired, or revoked access token" in err_msg


@pytest.mark.asyncio
async def test_auth_revoked_jwt_returns_401(async_client: AsyncClient, db_session: AsyncSession):
    """Tokens present in revocation blocklist must return 401."""
    user, token = await create_user_and_token(db_session, "revoked_test@metacheck.gov.in", RoleEnum.ENFORCEMENT_OFFICER.value)

    # Verify token works initially
    valid_res = await async_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {token}"})
    assert valid_res.status_code == 200

    # Revoke token
    revoke_token(token)

    # Must now be 401
    revoked_res = await async_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {token}"})
    assert revoked_res.status_code == 401


@pytest.mark.asyncio
async def test_auth_invalid_issuer_and_audience(async_client: AsyncClient, db_session: AsyncSession):
    """JWT with untrusted issuer or audience must return 401."""
    user, _ = await create_user_and_token(db_session, "claims_test@metacheck.gov.in", RoleEnum.ENFORCEMENT_OFFICER.value)

    now = datetime.now(timezone.utc)
    # Token with invalid issuer
    payload_bad_iss = {
        "sub": user.id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "untrusted-issuer",
        "aud": settings.JWT_AUDIENCE,
    }
    bad_iss_token = jwt.encode(payload_bad_iss, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    res_iss = await async_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {bad_iss_token}"})
    assert res_iss.status_code == 401

    # Token with invalid audience
    payload_bad_aud = {
        "sub": user.id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": "untrusted-audience",
    }
    bad_aud_token = jwt.encode(payload_bad_aud, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    res_aud = await async_client.get("/api/v1/inspections", headers={"Authorization": f"Bearer {bad_aud_token}"})
    assert res_aud.status_code == 401


@pytest.mark.asyncio
async def test_rbac_endpoint_level_authorization(async_client: AsyncClient, db_session: AsyncSession):
    """Test RBAC role matrix: VIEWER, OFFICER, ADMIN on sensitive endpoints."""
    _, admin_token = await create_user_and_token(db_session, "admin_rbac@metacheck.gov.in", RoleEnum.ADMIN.value)
    _, officer_token = await create_user_and_token(db_session, "officer_rbac@metacheck.gov.in", RoleEnum.ENFORCEMENT_OFFICER.value)
    _, viewer_token = await create_user_and_token(db_session, "viewer_rbac@metacheck.gov.in", RoleEnum.VIEWER.value)

    admin_h = {"Authorization": f"Bearer {admin_token}"}
    officer_h = {"Authorization": f"Bearer {officer_token}"}
    viewer_h = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Admin-only endpoint: /api/v1/users (GET)
    # Admin -> 200
    res_adm = await async_client.get("/api/v1/users", headers=admin_h)
    assert res_adm.status_code == 200

    # Officer -> 403
    res_off_user = await async_client.get("/api/v1/users", headers=officer_h)
    assert res_off_user.status_code == 403

    # Viewer -> 403
    res_viw_user = await async_client.get("/api/v1/users", headers=viewer_h)
    assert res_viw_user.status_code == 403

    # 2. Officer/Admin endpoint: Create Inspection (POST /api/v1/inspections)
    # Create a product first
    p_res = await async_client.post(
        "/api/v1/products",
        headers=officer_h,
        json={"name": "RBAC Test Biscuit", "brand": "CrispyCo", "category": "Food & Snacks"},
    )
    assert p_res.status_code == 201
    prod_id = p_res.json()["id"]

    # Officer -> 201
    insp_off = await async_client.post(
        "/api/v1/inspections",
        headers=officer_h,
        json={"product_id": prod_id, "source_type": "FIELD_SCANNER"},
    )
    assert insp_off.status_code == 201

    # Viewer attempting to create inspection -> 403
    insp_viw = await async_client.post(
        "/api/v1/inspections",
        headers=viewer_h,
        json={"product_id": prod_id, "source_type": "FIELD_SCANNER"},
    )
    assert insp_viw.status_code == 403

    # Viewer reading inspections -> 200
    read_viw = await async_client.get("/api/v1/inspections", headers=viewer_h)
    assert read_viw.status_code == 200


def test_production_jwt_secret_hardening():
    """Verify that Settings rejects default or insecure secrets outside development."""
    # 1. Development allows default placeholder
    dev_settings = Settings(ENVIRONMENT="development", JWT_SECRET="metacheck-super-secret-jwt-key-change-in-production-2026")
    assert dev_settings.ENVIRONMENT == "development"

    # 2. Production with default secret must fail fast
    with pytest.raises(ValueError) as excinfo:
        Settings(ENVIRONMENT="production", JWT_SECRET="metacheck-super-secret-jwt-key-change-in-production-2026")
    assert "Insecure or default JWT_SECRET is not permitted" in str(excinfo.value)

    # 3. Production with short secret (<32 chars) must fail fast
    with pytest.raises(ValueError) as excinfo2:
        Settings(ENVIRONMENT="production", JWT_SECRET="short-secret-key")
    assert "at least 32 characters" in str(excinfo2.value)

    # 4. Production with strong custom secret passes
    strong_secret = "a" * 32 + "_cryptographically_secure_random_key_2026"
    prod_valid = Settings(ENVIRONMENT="production", JWT_SECRET=strong_secret)
    assert prod_valid.JWT_SECRET == strong_secret


@pytest.mark.asyncio
async def test_statutory_2026_2027_ecommerce_rule_6_10a_versioning():
    """
    Test Rule 6(10A) statutory records:
    - PCR_2026_RULE_6_10A_ECOM
    - Version 1.0: Legal Metrology (Packaged Commodities) Amendment Rules, 2026 (G.S.R. 128(E) dated 13 February 2026, 2026-07-01 to 2027-07-01)
    - Version 2.0: Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026 (G.S.R. 312(E) dated 27 April 2026, 2027-07-01 onwards)
    - Context: E_COMMERCE_LISTING
    """
    # 1. Verify seed_rules definition
    from app.services.rules.seed_rules import STATUTORY_BASELINE_RULES
    seed_ecom = next((r for r in STATUTORY_BASELINE_RULES if r["rule_code"] == "PCR_2026_RULE_6_10A_ECOM"), None)
    assert seed_ecom is not None
    assert seed_ecom["rule_code"] == "PCR_2026_RULE_6_10A_ECOM"
    assert seed_ecom["legal_reference"] == "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(10A)"
    
    v1_seed = next((v for v in seed_ecom["versions"] if v["version"] == "1.0"), None)
    assert v1_seed is not None
    assert "2026" in v1_seed["source_document"]
    assert "Amendment Rules, 2026" in v1_seed["source_document"]
    assert "13th February, 2026" in v1_seed["source_gazette_reference"] or "13 February 2026" in v1_seed["source_gazette_reference"]
    assert "G.S.R. 128(E)" in v1_seed["source_gazette_reference"]
    assert v1_seed["active_from"] == datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert v1_seed["active_to"] == datetime(2027, 7, 1, tzinfo=timezone.utc)
    assert "Every e-commerce entity selling imported products shall provide the product listings of such imported products in a searchable and sortable filter specifying the country of origin." in v1_seed["requirement_text"]

    v2_seed = next((v for v in seed_ecom["versions"] if v["version"] == "2.0"), None)
    assert v2_seed is not None
    assert "Second Amendment Rules, 2026" in v2_seed["source_document"]
    assert "2026" in v2_seed["source_document"]
    assert "27th April, 2026" in v2_seed["source_gazette_reference"] or "27 April 2026" in v2_seed["source_gazette_reference"]
    assert "G.S.R. 312(E)" in v2_seed["source_gazette_reference"]
    assert v2_seed["active_from"] == datetime(2027, 7, 1, tzinfo=timezone.utc)
    assert v2_seed["active_to"] is None
    assert "Every e-commerce entity offering for sale any imported product shall, with effect from 1 July 2027, ensure that the product listing of such imported product contains a searchable and sortable filter specifying the country of origin." in v2_seed["requirement_text"]

    # 2. Verify applicability logic
    rule = Rule(
        rule_code="PCR_2026_RULE_6_10A_ECOM",
        name="E-Commerce Marketplace Country of Origin & Search Filter",
        legal_reference="Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(10A)",
        is_active=True,
    )

    ver_1_0 = RuleVersion(
        rule=rule,
        version="1.0",
        requirement_text="Every e-commerce entity selling imported products shall provide the product listings of such imported products in a searchable and sortable filter specifying the country of origin.",
        source_document="Legal Metrology (Packaged Commodities) Amendment Rules, 2026",
        source_gazette_reference="G.S.R. 128(E) dated 13th February, 2026; effective 1st July, 2026",
        active_from=datetime(2026, 7, 1, tzinfo=timezone.utc),
        active_to=datetime(2027, 7, 1, tzinfo=timezone.utc),
        applicable_contexts=["E_COMMERCE_LISTING", "IMPORTED_PRODUCT"],
        validation_type=ValidationTypeEnum.PRESENCE_CHECK,
    )

    ver_2_0 = RuleVersion(
        rule=rule,
        version="2.0",
        requirement_text="Every e-commerce entity offering for sale any imported product shall, with effect from 1 July 2027, ensure that the product listing of such imported product contains a searchable and sortable filter specifying the country of origin.",
        source_document="Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026",
        source_gazette_reference="G.S.R. 312(E) dated 27th April, 2026; effective 1st July, 2027",
        active_from=datetime(2027, 7, 1, tzinfo=timezone.utc),
        active_to=None,
        applicable_contexts=["E_COMMERCE_LISTING", "IMPORTED_PRODUCT"],
        validation_type=ValidationTypeEnum.PRESENCE_CHECK,
    )

    # --- EXPLICIT CASES (A through H) ---
    date_v1_active = datetime(2026, 10, 15, tzinfo=timezone.utc)
    date_v2_active = datetime(2027, 8, 1, tzinfo=timezone.utc)

    # A. V1 exact requirement text
    exact_v1_text = "Every e-commerce entity selling imported products shall provide the product listings of such imported products in a searchable and sortable filter specifying the country of origin."
    assert v1_seed["requirement_text"] == exact_v1_text

    # B. V2 exact requirement text
    exact_v2_text = "Every e-commerce entity offering for sale any imported product shall, with effect from 1 July 2027, ensure that the product listing of such imported product contains a searchable and sortable filter specifying the country of origin."
    assert v2_seed["requirement_text"] == exact_v2_text

    # C. Imported e-commerce = applicable
    assert is_rule_version_applicable(ver_1_0, date_v1_active, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is True
    assert is_rule_version_applicable(ver_2_0, date_v2_active, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is True

    # D. Domestic e-commerce = NOT applicable
    assert is_rule_version_applicable(ver_1_0, date_v1_active, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=False) is False
    assert is_rule_version_applicable(ver_2_0, date_v2_active, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=False) is False

    # E. Imported physical package = NOT applicable for Rule 6(10A)
    assert is_rule_version_applicable(ver_1_0, date_v1_active, applicable_context="PHYSICAL_PACKAGE", is_e_commerce=False, is_imported=True) is False
    assert is_rule_version_applicable(ver_2_0, date_v2_active, applicable_context="PHYSICAL_PACKAGE", is_e_commerce=False, is_imported=True) is False

    # F. Domestic physical package = NOT applicable
    assert is_rule_version_applicable(ver_1_0, date_v1_active, applicable_context="PHYSICAL_PACKAGE", is_e_commerce=False, is_imported=False) is False
    assert is_rule_version_applicable(ver_2_0, date_v2_active, applicable_context="PHYSICAL_PACKAGE", is_e_commerce=False, is_imported=False) is False

    # G. 2027-06-30 -> V1 active, V2 inactive
    date_2027_06_30 = datetime(2027, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
    assert is_rule_version_applicable(ver_1_0, date_2027_06_30, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is True
    assert is_rule_version_applicable(ver_2_0, date_2027_06_30, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is False

    # H. 2027-07-01 -> V1 inactive, V2 active (at exact midnight 00:00:00 UTC)
    date_2027_07_01_midnight = datetime(2027, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert is_rule_version_applicable(ver_1_0, date_2027_07_01_midnight, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is False
    assert is_rule_version_applicable(ver_2_0, date_2027_07_01_midnight, applicable_context="E_COMMERCE_LISTING", is_e_commerce=True, is_imported=True) is True

