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
async def test_upload_and_process_endpoint(async_client: AsyncClient):
    img_bytes = create_test_image_bytes(600, 500)
    files = {"file": ("commodity_test.png", img_bytes, "image/png")}
    data = {"engine_name": "mock", "language": "en"}

    resp = await async_client.post(
        "/api/v1/scans/upload-and-process",
        files=files,
        data=data,
    )

    assert resp.status_code == 200
    res_data = resp.json()
    assert "scan_id" in res_data
    assert "image_url" in res_data
    ocr_result = res_data["ocr_result"]
    assert "mock" in ocr_result["ocr_engine"].lower()
    assert ocr_result["confidence_score"] > 0.8

    assert "NET QUANTITY" in ocr_result["full_text"]
    assert len(ocr_result["regions"]) > 0
    assert ocr_result["quality_metrics"]["width"] == 600
    assert ocr_result["quality_metrics"]["height"] == 500
    assert "disclaimer" in res_data

    # Now verify GET /api/v1/scans/{scan_id}/ocr
    scan_id = res_data["scan_id"]
    get_resp = await async_client.get(f"/api/v1/scans/{scan_id}/ocr")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["scan_id"] == scan_id
    assert get_data["full_text"] == ocr_result["full_text"]
    assert len(get_data["regions"]) == len(ocr_result["regions"])


@pytest.mark.asyncio
async def test_analyze_image_quality_endpoint(async_client: AsyncClient):
    img_bytes = create_test_image_bytes(450, 450)
    files = {"file": ("quality_test.png", img_bytes, "image/png")}

    resp = await async_client.post(
        "/api/v1/images/analyze-quality",
        files=files,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["width"] == 450
    assert data["height"] == 450
    assert "sharpness_score" in data
    assert "brightness_mean" in data
    assert "contrast_score" in data
    assert "quality_score" in data
    assert isinstance(data["warnings"], list)


@pytest.mark.asyncio
async def test_upload_empty_file_fails(async_client: AsyncClient):
    files = {"file": ("empty.png", b"", "image/png")}
    resp = await async_client.post(
        "/api/v1/scans/upload-and-process",
        files=files,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_ocr_nonexistent_scan_404(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/scans/nonexistent-uuid-123/ocr")
    assert resp.status_code == 404
