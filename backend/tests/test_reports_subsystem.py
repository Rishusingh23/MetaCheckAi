"""
Unit and integration tests for Report Generation Subsystem.
Verifies PDF, JSON, and CSV report creation, file downloading, and audit trail updates.
"""
import json
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_and_download_pdf_report(async_client: AsyncClient):
    """Verify PDF advisory report compilation and binary file download."""
    client = async_client

    # Create product, inspection, violation
    p = await client.post(
        "/api/v1/products",
        json={
            "name": "Organic Honey 500g",
            "brand": "PureNature",
            "category": "Food & Beverages",
            "country_of_origin": "India",
            "manufacturer": "PureNature Foods Pvt Ltd, Bangalore",
        },
    )
    prod_id = p.json()["id"]

    i = await client.post(
        "/api/v1/inspections",
        json={"product_id": prod_id, "source_type": "FIELD_SCANNER"},
    )
    insp_id = i.json()["id"]

    # Run compliance evaluation
    await client.post(f"/api/v1/inspections/{insp_id}/evaluate")

    # 1. Generate PDF Report
    pdf_gen_res = await client.post(
        f"/api/v1/reports/inspections/{insp_id}/generate?format=PDF&report_type=INSPECTION_SUMMARY"
    )
    assert pdf_gen_res.status_code == 201
    report_data = pdf_gen_res.json()
    report_id = report_data["id"]
    assert report_data["format"] == "PDF"
    assert report_data["status"] == "READY"

    # 2. Download PDF file
    dl_res = await client.get(f"/api/v1/reports/{report_id}/download")
    assert dl_res.status_code == 200
    assert "application/pdf" in dl_res.headers["content-type"]
    assert dl_res.content.startswith(b"%PDF-1.4")
    assert b"%%EOF" in dl_res.content

    # 3. List reports for inspection
    list_res = await client.get(f"/api/v1/reports/inspections/{insp_id}/list")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_generate_and_download_json_and_csv_reports(async_client: AsyncClient):
    """Verify JSON and CSV export generation and contents."""
    client = async_client

    p = await client.post(
        "/api/v1/products",
        json={"name": "Almond Milk 1L", "brand": "NutriLife", "category": "Dairy Alternatives"},
    )
    i = await client.post(
        "/api/v1/inspections",
        json={"product_id": p.json()["id"]},
    )
    insp_id = i.json()["id"]

    # 1. JSON Report
    json_gen = await client.post(
        f"/api/v1/reports/inspections/{insp_id}/generate?format=JSON"
    )
    assert json_gen.status_code == 201
    json_rep_id = json_gen.json()["id"]

    dl_json = await client.get(f"/api/v1/reports/{json_rep_id}/download")
    assert dl_json.status_code == 200
    assert dl_json.headers["content-type"] == "application/json"
    parsed_dossier = json.loads(dl_json.content.decode("utf-8"))
    assert "inspection" in parsed_dossier
    assert "compliance_checks" in parsed_dossier
    assert "legal_disclaimer" in parsed_dossier

    # 2. CSV Report
    csv_gen = await client.post(
        f"/api/v1/reports/inspections/{insp_id}/generate?format=CSV"
    )
    assert csv_gen.status_code == 201
    csv_rep_id = csv_gen.json()["id"]

    dl_csv = await client.get(f"/api/v1/reports/{csv_rep_id}/download")
    assert dl_csv.status_code == 200
    assert "text/csv" in dl_csv.headers["content-type"]
    csv_text = dl_csv.content.decode("utf-8")
    assert "Inspection ID" in csv_text
    assert "Product Name" in csv_text
    assert "Statutory Reference" in csv_text
