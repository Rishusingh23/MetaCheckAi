import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_violations_and_evidence_api(async_client: AsyncClient):
    # 1. Setup Product and Inspection
    prod_resp = await async_client.post(
        "/api/v1/products",
        json={"name": "Packaged Spices 100g", "brand": "DesiMasala", "category": "Food"},
    )
    product_id = prod_resp.json()["id"]

    insp_resp = await async_client.post(
        "/api/v1/inspections",
        json={"product_id": product_id},
    )
    inspection_id = insp_resp.json()["id"]

    # 2. Record Violation
    viol_payload = {
        "inspection_id": inspection_id,
        "violation_code": "VIOL_MISSING_COUNTRY_OF_ORIGIN",
        "description": "Potential non-compliance detected: Country of origin declaration is absent on PDP.",
        "severity": "MAJOR",
        "status": "FLAGGED_FOR_REVIEW",
    }
    create_viol_resp = await async_client.post("/api/v1/violations", json=viol_payload)
    assert create_viol_resp.status_code == 201
    violation_id = create_viol_resp.json()["id"]

    # 3. Attach Evidence to Violation
    ev_payload = {
        "source_type": "LABEL_IMAGE_CROP",
        "image_url_or_path": "/evidence/spice_front.jpg",
        "description": "PDP panel image showing absence of country of origin line",
        "confidence": 0.94,
    }
    ev_resp = await async_client.post(f"/api/v1/violations/{violation_id}/evidences", json=ev_payload)
    assert ev_resp.status_code == 201

    # 4. Get violation with evidence
    get_viol_resp = await async_client.get(f"/api/v1/violations/{violation_id}")
    assert get_viol_resp.status_code == 200
    viol_detail = get_viol_resp.json()
    assert viol_detail["id"] == violation_id
    assert len(viol_detail["evidences"]) == 1

    # 5. Officer confirms violation
    patch_viol_resp = await async_client.patch(
        f"/api/v1/violations/{violation_id}",
        json={"status": "OFFICER_CONFIRMED"},
    )
    assert patch_viol_resp.status_code == 200
    assert patch_viol_resp.json()["status"] == "OFFICER_CONFIRMED"

    # 6. List violations
    list_resp = await async_client.get(f"/api/v1/violations?inspection_id={inspection_id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
