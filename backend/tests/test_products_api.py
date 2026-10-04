import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_product_crud_and_search(async_client: AsyncClient):
    # 1. Create product
    payload = {
        "name": "Almond Crunch Cookies 200g",
        "brand": "NutriBites Ltd",
        "category": "Confectionery",
        "manufacturer": "NutriBites Foods Pvt Ltd",
        "packer": "NutriBites Foods Pvt Ltd",
        "barcode_gtin": "8901030912345",
        "country_of_origin": "India",
        "description": "Crispy roasted almond cookies",
    }
    response = await async_client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    product_id = data["id"]
    assert data["name"] == payload["name"]
    assert data["brand"] == payload["brand"]
    assert data["barcode_gtin"] == payload["barcode_gtin"]

    # 2. Add product image
    image_payload = {
        "image_url_or_path": "/images/pdp_front.jpg",
        "image_type": "FRONT_PDP",
        "file_metadata": {"resolution": "300dpi"},
    }
    img_resp = await async_client.post(f"/api/v1/products/{product_id}/images", json=image_payload)
    assert img_resp.status_code == 201
    img_data = img_resp.json()
    assert img_data["product_id"] == product_id

    # 3. Get product by ID (detail view)
    get_resp = await async_client.get(f"/api/v1/products/{product_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == product_id
    assert len(detail["images"]) == 1

    # 4. Search and filter
    search_resp = await async_client.get("/api/v1/products?search=NutriBites")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["id"] == product_id

    # 5. Filter by category
    cat_resp = await async_client.get("/api/v1/products?category=Confectionery")
    assert cat_resp.status_code == 200
    assert cat_resp.json()["total"] == 1

    # Filter with non-matching category
    empty_resp = await async_client.get("/api/v1/products?category=Automotive")
    assert empty_resp.status_code == 200
    assert empty_resp.json()["total"] == 0

    # 6. Update product
    update_payload = {"brand": "NutriBites Premium"}
    put_resp = await async_client.put(f"/api/v1/products/{product_id}", json=update_payload)
    assert put_resp.status_code == 200
    assert put_resp.json()["brand"] == "NutriBites Premium"

    # 7. Delete product
    del_resp = await async_client.delete(f"/api/v1/products/{product_id}")
    assert del_resp.status_code == 200

    # Verify not found
    get_del_resp = await async_client.get(f"/api/v1/products/{product_id}")
    assert get_del_resp.status_code == 404
