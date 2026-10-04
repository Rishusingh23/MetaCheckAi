import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_reports_api(async_client: AsyncClient):
    # Setup Product and Inspection
    prod_resp = await async_client.post(
        "/api/v1/products",
        json={"name": "Tea Pouch 250g", "brand": "ChaiBari", "category": "Beverages"},
    )
    product_id = prod_resp.json()["id"]

    insp_resp = await async_client.post(
        "/api/v1/inspections",
        json={"product_id": product_id},
    )
    inspection_id = insp_resp.json()["id"]

    # Create Report
    rep_payload = {
        "inspection_id": inspection_id,
        "report_type": "INSPECTION_SUMMARY",
        "file_path": "/reports/tea_dossier.pdf",
        "format": "PDF",
        "status": "READY",
    }
    rep_resp = await async_client.post("/api/v1/reports", json=rep_payload)
    assert rep_resp.status_code == 201
    report_id = rep_resp.json()["id"]

    # Get Report
    get_resp = await async_client.get(f"/api/v1/reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["inspection_id"] == inspection_id

    # List Reports
    list_resp = await async_client.get(f"/api/v1/reports?inspection_id={inspection_id}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
