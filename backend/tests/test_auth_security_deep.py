"""
Comprehensive Phase 7.1 Authentication & Cryptographic Security Tests.
Verifies bcrypt password hashing, independent salt generation, non-plaintext storage,
JWT signing, issuer/audience validation, revocation blocklist, and absence of secret leakage.
"""
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
)
from app.main import app
from app.models.user import Role, RoleEnum, User
from app.schemas.auth import TokenResponse, UserAuthRead
from app.schemas.user import UserRead


@pytest.mark.asyncio
async def test_password_not_stored_as_plaintext():
    """Verify that hashed password differs completely from plaintext."""
    raw_password = "SecureOfficerPassword@2026"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert raw_password not in hashed
    assert len(hashed) >= 50


@pytest.mark.asyncio
async def test_password_hash_is_not_simple_sha256():
    """Verify that password hash uses Modular Crypt Format ($2b$) and is not a 64-char hex SHA-256."""
    raw_password = "InspectorPassword#789"
    hashed = hash_password(raw_password)

    # Standard bcrypt prefix
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    # SHA-256 hex is exactly 64 characters without $ markers
    assert len(hashed) == 60
    assert "$" in hashed


@pytest.mark.asyncio
async def test_password_verification_succeeds_and_fails():
    """Verify that verify_password accepts exact password and rejects wrong password."""
    raw_password = "ValidMetrologyPass@123"
    hashed = hash_password(raw_password)

    # Correct password succeeds
    assert verify_password(raw_password, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword@123", hashed) is False
    assert verify_password("validmetrologypass@123", hashed) is False  # Case sensitive
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "") is False


@pytest.mark.asyncio
async def test_independent_salts_for_identical_passwords():
    """Verify that hashing identical passwords twice produces distinct hashes due to random salting."""
    password = "CommonPassword@123"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


@pytest.mark.asyncio
async def test_empty_password_rejection():
    """Verify that empty passwords raise ValueError on hashing."""
    with pytest.raises(ValueError):
        hash_password("")


@pytest.mark.asyncio
async def test_jwt_token_claims_and_issuer_audience():
    """Verify JWT payload contains expected claims, issuer, audience, and subject."""
    sub_id = "officer-uuid-456"
    custom_claims = {"role": "ENFORCEMENT_OFFICER", "email": "officer@metacheck.gov.in"}

    token = create_access_token(subject=sub_id, claims=custom_claims)
    decoded = decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == sub_id
    assert decoded["role"] == "ENFORCEMENT_OFFICER"
    assert decoded["email"] == "officer@metacheck.gov.in"
    assert decoded["iss"] == settings.JWT_ISSUER
    assert decoded["aud"] == settings.JWT_AUDIENCE
    assert "exp" in decoded
    assert "iat" in decoded


@pytest.mark.asyncio
async def test_jwt_expired_token_rejected():
    """Verify that expired JWT access tokens are rejected."""
    token = create_access_token(
        subject="user-123",
        expires_delta=timedelta(seconds=-10),  # Expired in past
    )
    decoded = decode_access_token(token)
    assert decoded is None


@pytest.mark.asyncio
async def test_jwt_wrong_issuer_or_audience_rejected():
    """Verify tokens signed with wrong issuer/audience are rejected by decode_access_token."""
    # Token with wrong issuer
    wrong_payload = {
        "sub": "user-123",
        "iss": "untrusted-issuer",
        "aud": settings.JWT_AUDIENCE,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
    }
    bad_token = jwt.encode(wrong_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    assert decode_access_token(bad_token) is None

    # Token with wrong secret (32 bytes long)
    bad_secret_token = jwt.encode(
        {"sub": "user-123", "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE},
        "wrong-secret-key-that-is-at-least-32-bytes-long!",
        algorithm="HS256",
    )
    assert decode_access_token(bad_secret_token) is None


@pytest.mark.asyncio
async def test_jwt_revocation_lifecycle():
    """Verify that revoked tokens cannot be decoded and are rejected."""
    token = create_access_token(subject="user-revocation-test")
    assert is_token_revoked(token) is False
    assert decode_access_token(token) is not None

    revoke_token(token)
    assert is_token_revoked(token) is True
    assert decode_access_token(token) is None


@pytest.mark.asyncio
async def test_schemas_do_not_expose_password_hash():
    """Verify that UserRead and UserAuthRead schemas do not contain password or password_hash fields."""
    user_read_fields = UserRead.model_fields.keys()
    assert "password" not in user_read_fields
    assert "password_hash" not in user_read_fields

    auth_read_fields = UserAuthRead.model_fields.keys()
    assert "password" not in auth_read_fields
    assert "password_hash" not in auth_read_fields


@pytest.mark.asyncio
async def test_login_flow_with_bcrypt_and_revocation(async_client: AsyncClient):
    """Integration test: login with bcrypt, access /auth/me, logout, verify revocation."""
    # Login with seed admin credentials
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@metacheck.gov.in", "password": "Admin@123"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    token = token_data["access_token"]
    assert token is not None

    # Authenticate with Bearer token
    me_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@metacheck.gov.in"
    assert me_res.json()["role"] == "ADMIN"
    assert "password" not in me_res.json()
    assert "password_hash" not in me_res.json()

    # Logout / Revoke token
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Re-accessing with revoked token must fail with 401
    post_logout_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_logout_res.status_code == 401

