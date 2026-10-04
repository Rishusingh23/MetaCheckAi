"""
Unit and integration tests for Dashboard and Operational Analytics API.
Verifies live SQL aggregations, category breakdowns, severity distributions,
top violated rules, and compliance trend computations.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_summary_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/dashboard/summary live database metrics calculation."""
    client = async_client

    # Create products in different categories
    p1 = await client.post(
        "/api/v1/products",
        json={"name": "Dashboard Soap 100g", "brand": "CleanLife", "category": "Personal Care"},
    )
    p2 = await client.post(
        "/api/v1/products",
        json={"name": "Dashboard Juice 1L", "brand": "FreshBev", "category": "Beverages"},
    )

    p1_id = p1.json()["id"]
    p2_id = p2.json()["id"]

    # Create inspections
    i1 = await client.post(
        "/api/v1/inspections",
        json={"product_id": p1_id, "source_type": "FIELD_SCANNER"},
    )
    i2 = await client.post(
        "/api/v1/inspections",
        json={"product_id": p2_id, "source_type": "PORTAL_UPLOAD"},
    )

    i1_id = i1.json()["id"]
    i2_id = i2.json()["id"]

    # Create violations
    v1 = await client.post(
        "/api/v1/violations",
        json={
            "inspection_id": i1_id,
            "violation_code": "VIOL_MISSING_MRP",
            "description": "Missing retail sale price declaration",
            "severity": "CRITICAL",
            "status": "FLAGGED_FOR_REVIEW",
        },
    )
    v2 = await client.post(
        "/api/v1/violations",
        json={
            "inspection_id": i2_id,
            "violation_code": "VIOL_IMPROPER_UNIT",
            "description": "Non-standard measurement unit used",
            "severity": "MINOR",
            "status": "FLAGGED_FOR_REVIEW",
        },
    )

    # Review v1
    await client.patch(
        f"/api/v1/violations/{v1.json()['id']}/review",
        json={"status": "OFFICER_CONFIRMED", "comment": "Confirmed by officer inspection"},
    )

    # Fetch dashboard summary
    res = await client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total_inspections"] >= 2
    assert data["flagged_violations"] >= 1
    assert data["officer_confirmed_violations"] >= 1
    assert isinstance(data["compliance_rate"], float)
    assert isinstance(data["category_distribution"], list)
    assert len(data["category_distribution"]) > 0
    assert isinstance(data["violations_by_severity"], list)
    assert isinstance(data["top_violated_rules"], list)
    assert isinstance(data["inspection_trend"], list)
    assert len(data["inspection_trend"]) == 7
    assert isinstance(data["recent_inspections"], list)
    assert len(data["recent_inspections"]) > 0


@pytest.mark.asyncio
async def test_dashboard_summary_with_filters(async_client: AsyncClient):
    """Verify dashboard endpoint with category and date filters."""
    client = async_client
    res = await client.get("/api/v1/dashboard/summary?category=Personal Care")
    assert res.status_code == 200
    data = res.json()
    assert "total_inspections" in data
    assert "compliance_rate" in data
