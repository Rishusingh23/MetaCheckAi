import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_roles_and_users_api(async_client: AsyncClient):
    # 1. Fetch existing roles
    roles_list = await async_client.get("/api/v1/roles")
    assert roles_list.status_code == 200
    roles = roles_list.json()
    officer_role = next((r for r in roles if r["name"] == "ENFORCEMENT_OFFICER"), None)
    
    if not officer_role:
        role_resp = await async_client.post(
            "/api/v1/roles",
            json={"name": "ENFORCEMENT_OFFICER", "description": "Legal Metrology Field Officer"},
        )
        assert role_resp.status_code == 201
        role_id = role_resp.json()["id"]
    else:
        role_id = officer_role["id"]
        # Duplicate role creation triggers 409 Conflict
        dup_role = await async_client.post(
            "/api/v1/roles",
            json={"name": "ENFORCEMENT_OFFICER", "description": "Duplicate Role"},
        )
        assert dup_role.status_code == 409

    # 3. Create User
    user_payload = {
        "name": "Inspector S. Verma",
        "email": "s.verma@gov.in",
        "password": "SecurePassword123!",
        "role_id": role_id,
        "is_active": True,
    }
    user_resp = await async_client.post("/api/v1/users", json=user_payload)
    assert user_resp.status_code == 201
    user_data = user_resp.json()
    user_id = user_data["id"]

    # Ensure password_hash is NEVER exposed in the API response
    assert "password_hash" not in user_data
    assert "password" not in user_data
    assert user_data["email"] == "s.verma@gov.in"
    assert user_data["role"]["name"] == "ENFORCEMENT_OFFICER"

    # 4. Duplicate email triggers 409
    dup_user = await async_client.post("/api/v1/users", json=user_payload)
    assert dup_user.status_code == 409

    # 5. Get user profile
    get_user_resp = await async_client.get(f"/api/v1/users/{user_id}")
    assert get_user_resp.status_code == 200
    assert get_user_resp.json()["id"] == user_id
    assert "password_hash" not in get_user_resp.json()

    # 6. List users
    list_resp = await async_client.get("/api/v1/users")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    assert any(u["id"] == user_id for u in list_resp.json()["items"])

