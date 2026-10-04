import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rules_and_versions_api(async_client: AsyncClient):
    # 1. Register a statutory rule
    rule_payload = {
        "rule_code": "PCR_2011_RULE_6_1_E",
        "name": "Maximum Retail Price (MRP) Declaration",
        "description": "Retail sale price inclusive of all taxes must be declared on package.",
        "legal_reference": "The Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(e)",
        "is_active": True,
    }
    create_resp = await async_client.post("/api/v1/rules", json=rule_payload)
    assert create_resp.status_code == 201
    rule_data = create_resp.json()
    rule_id = rule_data["id"]

    # 2. Duplicate rule_code should trigger 409 Conflict
    dup_resp = await async_client.post("/api/v1/rules", json=rule_payload)
    assert dup_resp.status_code == 409

    # 3. Add Rule Version
    v1_payload = {
        "version": "1.0.0",
        "requirement_text": "MRP must state 'Maximum or Max. Retail Price Rs. ... inclusive of all taxes'.",
        "validation_type": "TEXT_PATTERN",
        "severity": "CRITICAL",
        "evidence_required": True,
        "source_gazette_reference": "Official Gazette Notification 2011",
    }
    v1_resp = await async_client.post(f"/api/v1/rules/{rule_id}/versions", json=v1_payload)
    assert v1_resp.status_code == 201
    assert v1_resp.json()["version"] == "1.0.0"

    # 4. Add amended Rule Version (2022 amendment for Unit Sale Price)
    v2_payload = {
        "version": "2022_AMENDMENT",
        "requirement_text": "MRP must be accompanied by Unit Sale Price (USP) per unit or standard metric quantity.",
        "validation_type": "FORMAT_CHECK",
        "severity": "CRITICAL",
        "evidence_required": True,
        "source_gazette_reference": "GSR 779(E) dated 02.11.2021",
    }
    v2_resp = await async_client.post(f"/api/v1/rules/{rule_id}/versions", json=v2_payload)
    assert v2_resp.status_code == 201
    assert v2_resp.json()["version"] == "2022_AMENDMENT"

    # 5. List versions
    ver_list_resp = await async_client.get(f"/api/v1/rules/{rule_id}/versions")
    assert ver_list_resp.status_code == 200
    assert len(ver_list_resp.json()) == 2

    # 6. Get rule detail
    detail_resp = await async_client.get(f"/api/v1/rules/{rule_id}")
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["versions"]) == 2

    # 7. List rules
    list_resp = await async_client.get("/api/v1/rules?is_active=true")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
