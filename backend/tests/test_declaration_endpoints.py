import io
import pytest
from httpx import AsyncClient
from PIL import Image


def create_test_image_bytes(width: int = 500, height: int = 400) -> bytes:
    img = Image.new("RGB", (width, height), color=(230, 230, 230))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_extract_declarations_endpoint_and_lifecycle(async_client: AsyncClient):
    # 1. First upload an image and run OCR to generate a completed scan and OCRResult
    img_bytes = create_test_image_bytes(600, 500)
    files = {"file": ("commodity_sample.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    scan_resp = await async_client.post(
        "/api/v1/scans/upload-and-process",
        files=files,
        data=data,
    )
    assert scan_resp.status_code == 200
    scan_id = scan_resp.json()["scan_id"]

    # 2. Call POST /api/v1/scans/{scan_id}/extract-declarations
    extract_resp = await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    assert extract_resp.status_code == 200
    extract_data = extract_resp.json()
    assert extract_data["scan_id"] == scan_id
    assert extract_data["status"] == "COMPLETED"
    assert extract_data["total_declarations"] > 0
    assert len(extract_data["declarations"]) > 0

    decl_types = [d["declaration_type"] for d in extract_data["declarations"]]
    assert "MRP" in decl_types
    assert "NET_QUANTITY" in decl_types
    assert "MANUFACTURER_DETAILS" in decl_types

    first_decl = extract_data["declarations"][0]
    decl_id = first_decl["id"]

    # 3. Test GET /api/v1/scans/{scan_id}/declarations
    get_resp = await async_client.get(f"/api/v1/scans/{scan_id}/declarations")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["total_declarations"] == extract_data["total_declarations"]

    # 4. Test GET /api/v1/declarations/{declaration_id}
    single_resp = await async_client.get(f"/api/v1/declarations/{decl_id}")
    assert single_resp.status_code == 200
    single_data = single_resp.json()
    assert single_data["id"] == decl_id

    # 5. Test PATCH /api/v1/declarations/{declaration_id} (Manual Officer Correction)
    patch_payload = {
        "normalized_value": "₹300.00",
        "notes": "Verified by officer from physical packaging stamp.",
    }
    patch_resp = await async_client.patch(
        f"/api/v1/declarations/{decl_id}",
        json=patch_payload,
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["normalized_value"] == "₹300.00"
    # Original raw value must be preserved!
    assert patched_data["raw_value"] == first_decl["raw_value"]
    assert patched_data["bounding_box"]["is_manually_edited"] is True
    assert patched_data["bounding_box"]["officer_notes"] == patch_payload["notes"]


@pytest.mark.asyncio
async def test_extract_declarations_idempotency(async_client: AsyncClient):
    # Upload and run OCR
    img_bytes = create_test_image_bytes()
    files = {"file": ("idempotency_test.png", img_bytes, "image/png")}
    scan_resp = await async_client.post(
        "/api/v1/scans/upload-and-process",
        files=files,
        data={"engine_name": "mock"},
    )
    scan_id = scan_resp.json()["scan_id"]

    # Run extraction 1st time
    resp1 = await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    assert resp1.status_code == 200
    total1 = resp1.json()["total_declarations"]

    # Run extraction 2nd time
    resp2 = await async_client.post(f"/api/v1/scans/{scan_id}/extract-declarations")
    assert resp2.status_code == 200
    total2 = resp2.json()["total_declarations"]

    # Total declarations count must be strictly identical without duplicate inflation
    assert total1 == total2


@pytest.mark.asyncio
async def test_extract_declarations_nonexistent_scan_404(async_client: AsyncClient):
    resp = await async_client.post("/api/v1/scans/nonexistent-scan-999/extract-declarations")
    assert resp.status_code == 404
