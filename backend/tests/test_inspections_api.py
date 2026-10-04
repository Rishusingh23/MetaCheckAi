import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_inspection_workflow_and_audit_history(async_client: AsyncClient):
    # 1. First create a product
    prod_resp = await async_client.post(
        "/api/v1/products",
        json={
            "name": "Natural Mineral Water 500ml",
            "brand": "AquaFresh Valley",
            "category": "Beverages",
            "barcode_gtin": "8901050734567",
        },
    )
    product_id = prod_resp.json()["id"]

    # 2. Initiate inspection
    insp_payload = {
        "product_id": product_id,
        "source_type": "PORTAL_UPLOAD",
        "notes": "Field surveillance sample.",
    }
    create_resp = await async_client.post("/api/v1/inspections", json=insp_payload)
    assert create_resp.status_code == 201
    inspection_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "CREATED"

    # 3. Attach a scan
    scan_payload = {
        "inspection_id": inspection_id,
        "image_path": "/uploads/scans/water_label.jpg",
        "panel_type": "FRONT_PDP",
        "processing_status": "PENDING",
    }
    scan_resp = await async_client.post(f"/api/v1/inspections/{inspection_id}/scans", json=scan_payload)
    assert scan_resp.status_code == 201

    # 4. Transition status to PROCESSING
    status_update_payload = {
        "status": "PROCESSING",
        "notes": "Automated OCR screening pipeline initiated.",
    }
    patch_resp = await async_client.patch(
        f"/api/v1/inspections/{inspection_id}/status",
        json=status_update_payload,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "PROCESSING"

    # 5. Transition status to REVIEW_REQUIRED
    status_update_payload2 = {
        "status": "REVIEW_REQUIRED",
        "notes": "Potential discrepancy identified in declaration font ratio.",
    }
    patch_resp2 = await async_client.patch(
        f"/api/v1/inspections/{inspection_id}/status",
        json=status_update_payload2,
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["status"] == "REVIEW_REQUIRED"

    # 6. Verify audit history logs
    hist_resp = await async_client.get(f"/api/v1/inspections/{inspection_id}/history")
    assert hist_resp.status_code == 200
    history_logs = hist_resp.json()
    assert len(history_logs) >= 3  # CREATED + 2 transitions

    # 7. Get full inspection detail
    detail_resp = await async_client.get(f"/api/v1/inspections/{inspection_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == inspection_id
    assert len(detail["scans"]) == 1
    assert len(detail["history_logs"]) >= 3

    # 8. List inspections with filter
    list_resp = await async_client.get("/api/v1/inspections?status=REVIEW_REQUIRED")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
