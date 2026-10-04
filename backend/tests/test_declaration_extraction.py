import pytest
from app.models.declaration import DeclarationTypeEnum, ExtractionStatusEnum
from app.services.declarations.extractor import DeclarationExtractorService
from app.services.ocr.models import BoundingBox, OCRRegion


def create_sample_regions() -> list[OCRRegion]:
    lines = [
        ("COMMODITY: PREMIUM ORGANIC WHOLE WHEAT ATTA", 0.96, BoundingBox(10, 10, 300, 35)),
        ("NET QUANTITY: 5.0 kg", 0.98, BoundingBox(10, 45, 200, 70)),
        ("MAXIMUM RETAIL PRICE (MRP): Rs. 295.00 (INCL. OF ALL TAXES)", 0.95, BoundingBox(10, 80, 400, 105)),
        ("UNIT SALE PRICE: Rs. 59.00 / kg", 0.94, BoundingBox(10, 115, 250, 140)),
        ("MANUFACTURED & PACKED BY: APEX FOODS INDIA PVT LTD", 0.93, BoundingBox(10, 150, 450, 175)),
        ("PLOT NO. 42, INDUSTRIAL AREA, PHASE II, NEW DELHI - 110020", 0.91, BoundingBox(10, 185, 480, 210)),
        ("DATE OF MANUFACTURE: 02/2026", 0.97, BoundingBox(10, 220, 260, 245)),
        ("CUSTOMER CARE: 1800-111-2222 / SUPPORT@APEXFOODS.IN", 0.94, BoundingBox(10, 255, 420, 280)),
        ("COUNTRY OF ORIGIN: INDIA", 0.98, BoundingBox(10, 290, 220, 315)),
    ]

    return [
        OCRRegion(text=text, confidence=conf, bbox=bbox)
        for text, conf, bbox in lines
    ]


@pytest.mark.asyncio
async def test_extract_declarations_complete_label():
    extractor = DeclarationExtractorService()
    regions = create_sample_regions()
    full_text = "\n".join(r.text for r in regions)

    candidates = await extractor.extract_declarations(full_text=full_text, regions=regions)

    candidate_types = {c.declaration_type for c in candidates}

    # Verify all key declarations are extracted
    assert DeclarationTypeEnum.MRP in candidate_types
    assert DeclarationTypeEnum.NET_QUANTITY in candidate_types
    assert DeclarationTypeEnum.UNIT_SALE_PRICE in candidate_types
    assert DeclarationTypeEnum.DATE_OF_MANUFACTURE in candidate_types
    assert DeclarationTypeEnum.MANUFACTURER_DETAILS in candidate_types
    assert DeclarationTypeEnum.CUSTOMER_CARE if hasattr(DeclarationTypeEnum, "CUSTOMER_CARE") else DeclarationTypeEnum.CONSUMER_CARE in candidate_types
    assert DeclarationTypeEnum.COUNTRY_OF_ORIGIN in candidate_types

    # Find MRP candidate
    mrp_cand = next(c for c in candidates if c.declaration_type == DeclarationTypeEnum.MRP)
    assert mrp_cand.normalized_value == "₹295.00"
    assert mrp_cand.confidence > 0.85
    assert mrp_cand.bounding_box is not None
    assert mrp_cand.bounding_box.x1 == 10

    # Find Net Quantity candidate
    net_cand = next(c for c in candidates if c.declaration_type == DeclarationTypeEnum.NET_QUANTITY)
    assert net_cand.normalized_value == "5 kg"
    assert net_cand.confidence > 0.85


@pytest.mark.asyncio
async def test_extract_declarations_ambiguity_handling():
    extractor = DeclarationExtractorService()
    # Scenario: Two conflicting high-confidence MRP lines on the same package
    regions = [
        OCRRegion(text="MRP: Rs. 120.00 (incl. of taxes)", confidence=0.95, bbox=BoundingBox(10, 10, 200, 30)),
        OCRRegion(text="Special Price MRP: Rs. 140.00", confidence=0.92, bbox=BoundingBox(10, 40, 200, 60)),
    ]
    full_text = "\n".join(r.text for r in regions)

    candidates = await extractor.extract_declarations(full_text=full_text, regions=regions)

    mrp_candidates = [c for c in candidates if c.declaration_type == DeclarationTypeEnum.MRP]
    assert len(mrp_candidates) == 1

    primary_mrp = mrp_candidates[0]
    assert primary_mrp.is_ambiguous is True
    assert primary_mrp.extraction_status == ExtractionStatusEnum.AMBIGUOUS
    assert len(primary_mrp.alternative_candidates) > 0
    assert "Ambiguous" in primary_mrp.confidence_rationale
