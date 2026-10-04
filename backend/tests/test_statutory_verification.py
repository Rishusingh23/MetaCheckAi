import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration, DeclarationTypeEnum, ExtractionStatusEnum
from app.models.inspection import Inspection, InspectionSourceEnum, InspectionStatusEnum
from app.models.product import Product
from app.models.rule import (
    ApplicableContextEnum,
    Rule,
    RuleVerificationStatusEnum,
    RuleVersion,
    SeverityEnum,
    ValidationTypeEnum,
)
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.models.user import Role, User
from app.services.rules.applicability import (
    is_rule_version_applicable,
    is_rule_version_applicable_to_context,
    is_rule_version_temporally_valid,
)
from app.services.rules.engine import rule_engine
from app.services.rules.evaluator import rule_evaluator
from app.services.rules.models import EvaluationContext
from app.services.rules.seed_rules import STATUTORY_BASELINE_RULES, seed_statutory_baseline_rules
from app.services.rules.validators.font import FontReadabilityValidator
from app.services.rules.validators.mrp import MRPValidator
from app.services.rules.validators.presence import PresenceValidator
from app.services.rules.validators.quantity import QuantityValidator
from app.services.rules.validators.text import TextPatternValidator


@pytest.mark.asyncio
async def test_statutory_baseline_metadata_and_verification_status(db_session: AsyncSession):
    """Verify all statutory baseline rules contain required metadata and VERIFIED_OFFICIAL status."""
    count = await seed_statutory_baseline_rules(db_session)
    assert count >= 8

    for rule_data in STATUTORY_BASELINE_RULES:
        assert "rule_code" in rule_data
        assert "legal_reference" in rule_data
        assert "versions" in rule_data
        assert len(rule_data["versions"]) >= 1

        for v in rule_data["versions"]:
            assert v["verification_status"] == RuleVerificationStatusEnum.VERIFIED_OFFICIAL
            assert "source_document" in v
            assert "source_gazette_reference" in v
            assert "applicable_contexts" in v
            assert "requirement_text" in v
            assert v["active_from"] is not None


@pytest.mark.asyncio
async def test_rule_version_selection_historical_vs_current_dates():
    """Verify date-rule version differences for Rule 6(1)(d) (Date of manufacture vs packing)."""
    rule = Rule(
        rule_code="PCR_2011_RULE_6_1_D",
        name="Date of Manufacture / Packing",
        legal_reference="Rule 6(1)(d)",
        is_active=True,
    )
    v1_historical = RuleVersion(
        rule=rule,
        version="1.0",
        requirement_text="Month and year of manufacture or pre-packed or imported",
        active_from=datetime(2011, 4, 1, tzinfo=timezone.utc),
        active_to=datetime(2022, 11, 30, 23, 59, 59, tzinfo=timezone.utc),
    )
    v2_current = RuleVersion(
        rule=rule,
        version="2.0",
        requirement_text="Month and year of manufacture (GSR 779(E))",
        active_from=datetime(2022, 12, 1, tzinfo=timezone.utc),
        active_to=None,
    )

    # Date in 2018: v1.0 is active, v2.0 is not
    date_2018 = datetime(2018, 5, 10, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(v1_historical, date_2018) is True
    assert is_rule_version_temporally_valid(v2_current, date_2018) is False

    # Date in 2024: v1.0 is expired, v2.0 is active
    date_2024 = datetime(2024, 2, 1, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(v1_historical, date_2024) is False
    assert is_rule_version_temporally_valid(v2_current, date_2024) is True


@pytest.mark.asyncio
async def test_mrp_historical_pre_gst_vs_current():
    """Verify historical vs current MRP version applicability across 2017 boundary."""
    rule = Rule(
        rule_code="PCR_2011_RULE_6_1_E",
        name="Maximum Retail Price",
        legal_reference="Rule 6(1)(e)",
        is_active=True,
    )
    v1_pre_gst = RuleVersion(
        rule=rule,
        version="1.0",
        requirement_text="Max. retail price Rs. ... inclusive of all taxes",
        active_from=datetime(2011, 4, 1, tzinfo=timezone.utc),
        active_to=datetime(2017, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
    )
    v2_post_gst = RuleVersion(
        rule=rule,
        version="2.0",
        requirement_text="Maximum Retail Price Rs./₹ ... inclusive of all taxes or MRP Rs./₹ ...",
        active_from=datetime(2017, 7, 1, tzinfo=timezone.utc),
        active_to=None,
    )

    date_2015 = datetime(2015, 1, 15, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(v1_pre_gst, date_2015) is True
    assert is_rule_version_temporally_valid(v2_post_gst, date_2015) is False

    date_2025 = datetime(2025, 8, 1, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(v1_pre_gst, date_2025) is False
    assert is_rule_version_temporally_valid(v2_post_gst, date_2025) is True


@pytest.mark.asyncio
async def test_usp_rule_attribution_and_effective_date():
    """Verify Unit Sale Price (Rule 6(1)(ea) & Rule 6(11)) is gated strictly to effective date (01-12-2022)."""
    rule = Rule(
        rule_code="PCR_2021_RULE_6_1_EA",
        name="Unit Sale Price",
        legal_reference="Rule 6(1)(ea) & Rule 6(11), GSR 779(E)",
        is_active=True,
    )
    v_usp = RuleVersion(
        rule=rule,
        version="1.0",
        requirement_text="Unit sale price in Rs. per g/ml or per kg/L",
        active_from=datetime(2022, 12, 1, tzinfo=timezone.utc),
    )

    ctx_2021 = EvaluationContext(
        inspection_id="insp-hist",
        product=None,
        inspection_date=datetime(2021, 6, 1, tzinfo=timezone.utc),
        declarations=[],
    )
    res_2021 = rule_evaluator.evaluate(v_usp, ctx_2021)
    assert res_2021.status == ComplianceStatusEnum.NOT_APPLICABLE

    ctx_2023 = EvaluationContext(
        inspection_id="insp-curr",
        product=None,
        inspection_date=datetime(2023, 6, 1, tzinfo=timezone.utc),
        declarations=[],
        ocr_raw_text="Packaged commodity label text with generic declarations but no USP.",
        image_quality={"is_blurry": False, "is_low_resolution": False},
    )
    res_2023 = rule_evaluator.evaluate(v_usp, ctx_2023)
    assert res_2023.status == ComplianceStatusEnum.FAIL
    assert "Potential non-compliance detected" in res_2023.explanation


@pytest.mark.asyncio
async def test_country_of_origin_physical_vs_ecommerce_and_2026_rule():
    """
    Verify country of origin distinctions:
      1. Physical domestic package -> Imported origin rule not applicable.
      2. Physical package inspection -> 2026 E-commerce origin rule NOT applied.
      3. E-commerce listing after 1 July 2026 -> 2026 E-commerce origin rule applies.
    """
    rule_imported = Rule(
        rule_code="PCR_2011_RULE_6_1_H",
        name="Imported Commodity Country of Origin",
        legal_reference="Rule 6(1)(h)",
        is_active=True,
    )
    ver_imported = RuleVersion(
        rule=rule_imported,
        version="1.0",
        requirement_text="Country of origin on imported packages",
        applicable_contexts=["IMPORTED_PRODUCT"],
        active_from=datetime(2017, 7, 1, tzinfo=timezone.utc),
    )

    rule_ecom_2026 = Rule(
        rule_code="PCR_2026_RULE_6_10A_ECOM",
        name="E-Commerce Country of Origin Filter Requirement",
        legal_reference="Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(10A)",
        is_active=True,
    )
    ver_ecom_2026_v1 = RuleVersion(
        rule=rule_ecom_2026,
        version="1.0",
        requirement_text="Every e-commerce entity selling imported products shall provide the product listings of such imported products in a searchable and sortable filter specifying the country of origin.",
        source_document="Legal Metrology (Packaged Commodities) Amendment Rules, 2026",
        source_gazette_reference="G.S.R. 128(E) dated 13th February, 2026; effective 1st July, 2026",
        applicable_contexts=["E_COMMERCE_LISTING", "IMPORTED_PRODUCT"],
        active_from=datetime(2026, 7, 1, tzinfo=timezone.utc),
        active_to=datetime(2027, 7, 1, tzinfo=timezone.utc),
    )
    ver_ecom_2026_v2 = RuleVersion(
        rule=rule_ecom_2026,
        version="2.0",
        requirement_text="Every e-commerce entity offering for sale any imported product shall, with effect from 1 July 2027, ensure that the product listing of such imported product contains a searchable and sortable filter specifying the country of origin.",
        source_document="Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026",
        source_gazette_reference="G.S.R. 312(E) dated 27th April, 2026; effective 1st July, 2027",
        applicable_contexts=["E_COMMERCE_LISTING", "IMPORTED_PRODUCT"],
        active_from=datetime(2027, 7, 1, tzinfo=timezone.utc),
        active_to=None,
    )

    # 1. Domestic physical package inspection (2026-08-01)
    target_date = datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert is_rule_version_applicable(
        ver_imported,
        target_date,
        applicable_context="PHYSICAL_PACKAGE",
        is_imported=False,
    ) is False

    # 2. Physical package inspection should NOT apply 2026 E-commerce rule
    assert is_rule_version_applicable(
        ver_ecom_2026_v1,
        target_date,
        applicable_context="PHYSICAL_PACKAGE",
        is_e_commerce=False,
    ) is False
    assert is_rule_version_applicable(
        ver_ecom_2026_v2,
        target_date,
        applicable_context="PHYSICAL_PACKAGE",
        is_e_commerce=False,
    ) is False

    # 3. E-commerce listing prior to 1 July 2026 -> Not applicable
    date_early_2026 = datetime(2026, 3, 1, tzinfo=timezone.utc)
    assert is_rule_version_applicable(
        ver_ecom_2026_v1,
        date_early_2026,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=True,
    ) is False

    # 4. Domestic e-commerce listing (not imported) -> NOT applicable
    assert is_rule_version_applicable(
        ver_ecom_2026_v1,
        target_date,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=False,
    ) is False

    # 5. Imported e-commerce listing during V1 window (2026-08-01) -> V1 Applicable, V2 Inactive
    assert is_rule_version_applicable(
        ver_ecom_2026_v1,
        target_date,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=True,
    ) is True
    assert is_rule_version_applicable(
        ver_ecom_2026_v2,
        target_date,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=True,
    ) is False

    # 6. Imported e-commerce listing during V2 window (2027-08-01) -> V1 Expired, V2 Applicable
    date_v2 = datetime(2027, 8, 1, tzinfo=timezone.utc)
    assert is_rule_version_applicable(
        ver_ecom_2026_v1,
        date_v2,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=True,
    ) is False
    assert is_rule_version_applicable(
        ver_ecom_2026_v2,
        date_v2,
        applicable_context="E_COMMERCE_LISTING",
        is_e_commerce=True,
        is_imported=True,
    ) is True


@pytest.mark.asyncio
async def test_consumer_care_partial_presence_review_vs_fail():
    """Verify consumer care returns REVIEW when partial details are present and FAIL when completely missing."""
    validator = TextPatternValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="Consumer care details with address, phone, email",
        validation_type=ValidationTypeEnum.TEXT_PATTERN,
        severity=SeverityEnum.MAJOR,
        conditions={
            "declaration_type": "CONSUMER_CARE",
            "required_elements": ["phone", "email"],
        },
    )

    # Case 1: Phone present, email missing -> REVIEW (not hard fail)
    decl_partial = Declaration(
        declaration_type=DeclarationTypeEnum.CONSUMER_CARE,
        raw_value="For complaints contact Consumer Executive at 1800-200-9999",
        normalized_value="Contact: 1800-200-9999",
        confidence=0.90,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    ctx_partial = EvaluationContext(
        inspection_id="insp-care-1",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_partial],
    )
    res_partial = validator.validate(ctx_partial, rule_ver)
    assert res_partial.status == ComplianceStatusEnum.REVIEW
    assert "missing: email address" in res_partial.explanation

    # Case 2: Complete phone + email present -> PASS
    decl_full = Declaration(
        declaration_type=DeclarationTypeEnum.CONSUMER_CARE,
        raw_value="Consumer Care: 1800-200-9999 / customercare@brand.in",
        normalized_value="Phone: 1800-200-9999, Email: customercare@brand.in",
        confidence=0.95,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    ctx_full = EvaluationContext(
        inspection_id="insp-care-2",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_full],
    )
    res_full = validator.validate(ctx_full, rule_ver)
    assert res_full.status == ComplianceStatusEnum.PASS

    # Case 3: Completely missing on clean image -> FAIL
    ctx_none = EvaluationContext(
        inspection_id="insp-care-3",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[],
        ocr_raw_text="No customer care here",
        image_quality={"is_blurry": False, "is_low_resolution": False},
    )
    res_none = validator.validate(ctx_none, rule_ver)
    assert res_none.status == ComplianceStatusEnum.FAIL
    assert "Potential non-compliance" in res_none.explanation


@pytest.mark.asyncio
async def test_font_measurement_uncalibrated_review_state():
    """Verify that uncalibrated digital photos yield REVIEW rather than false certified mm millimeter precision."""
    validator = FontReadabilityValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="Minimum font height per Rule 7 Table I",
        validation_type=ValidationTypeEnum.FONT_HEIGHT_RATIO,
        severity=SeverityEnum.MINOR,
        conditions={"declaration_type": "NET_QUANTITY"},
    )

    decl = Declaration(
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="500 g",
        bounding_box={"x1": 50, "y1": 100, "x2": 150, "y2": 130},
        confidence=0.92,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )

    # 1. Uncalibrated image -> returns REVIEW with calibration disclaimer
    ctx_uncalibrated = EvaluationContext(
        inspection_id="insp-font-1",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl],
        image_quality={"height": 1000, "width": 800},  # No calibrated_scale_px_per_mm
    )
    res_uncalibrated = validator.validate(ctx_uncalibrated, rule_ver)
    assert res_uncalibrated.status == ComplianceStatusEnum.REVIEW
    assert "uncalibrated" in res_uncalibrated.explanation.lower()
    assert "Rule 7 Table I" in res_uncalibrated.explanation

    # 2. Calibrated image (e.g. 10 px per mm -> 30px = 3.0 mm >= 1.0mm) -> PASS
    ctx_calibrated = EvaluationContext(
        inspection_id="insp-font-2",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl],
        image_quality={"height": 1000, "width": 800, "calibrated_scale_px_per_mm": 10.0},
    )
    res_calibrated = validator.validate(ctx_calibrated, rule_ver)
    assert res_calibrated.status == ComplianceStatusEnum.PASS
    assert "3.00 mm" in res_calibrated.detected_value


@pytest.mark.asyncio
async def test_quantity_validator_count_and_number_declarations():
    """Verify packages sold by number/units (e.g. 10 N, 50 units, 100 pcs) pass net quantity validation."""
    validator = QuantityValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="Net quantity in standard metric units or number",
        validation_type=ValidationTypeEnum.FORMAT_CHECK,
        severity=SeverityEnum.CRITICAL,
    )

    for test_qty, test_norm in [
        ("Net Qty: 10 N", "10 N"),
        ("Quantity: 50 Units", "50 units"),
        ("Pack of 100 Pcs", "100 pcs"),
        ("12 Pieces", "12 pieces"),
        ("1 Set", "1 set"),
    ]:
        decl = Declaration(
            declaration_type=DeclarationTypeEnum.NET_QUANTITY,
            raw_value=test_qty,
            normalized_value=test_norm,
            confidence=0.95,
            extraction_status=ExtractionStatusEnum.DETECTED,
        )
        ctx = EvaluationContext(
            inspection_id="insp-qty-count",
            product=None,
            inspection_date=datetime.now(timezone.utc),
            declarations=[decl],
        )
        res = validator.validate(ctx, rule_ver)
        assert res.status == ComplianceStatusEnum.PASS, f"Failed for {test_norm}: {res.explanation}"


@pytest.mark.asyncio
async def test_historical_inspection_reproducibility(db_session: AsyncSession):
    """Verify that an inspection record from 2015 is evaluated reproducibly against 2015 statutory rules."""
    await seed_statutory_baseline_rules(db_session)

    # Historical inspection in 2015
    role = Role(name="HIST_OFFICER", description="Officer")
    db_session.add(role)
    await db_session.flush()

    user = User(
        email="historical@metacheck.gov.in",
        name="Officer 2015",
        password_hash="pwd",
        role_id=role.id,
    )
    db_session.add(user)

    product = Product(
        name="Vintage Biscuit Pack 2015",
        brand="Britannia",
        category="Food",
    )
    db_session.add(product)
    await db_session.flush()

    inspection = Inspection(
        product_id=product.id,
        inspector_id=user.id,
        status=InspectionStatusEnum.PROCESSING,
        source_type=InspectionSourceEnum.PORTAL_UPLOAD,
        inspection_date=datetime(2015, 6, 15, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    await db_session.flush()

    scan = Scan(
        inspection_id=inspection.id,
        image_path="/storage/scans/vintage_2015.jpg",
        panel_type=PanelTypeEnum.BACK_DECLARATION,
        processing_status=ScanStatusEnum.COMPLETED,
    )
    db_session.add(scan)
    await db_session.flush()

    # Pre-GST MRP & Pre-2022 Packing Date
    decl_mrp = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.MRP,
        raw_value="Max. Retail Price Rs. 50.00 inclusive of all taxes",
        normalized_value="₹ 50.00 (Incl. of all taxes)",
        confidence=0.95,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    decl_date = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.DATE_OF_PACKING,
        raw_value="Pkd: 05/2015",
        normalized_value="05/2015",
        confidence=0.95,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    decl_qty = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="Net Wt: 200g",
        normalized_value="200 g",
        confidence=0.96,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    db_session.add_all([decl_mrp, decl_date, decl_qty])
    await db_session.commit()

    eval_result = await rule_engine.evaluate_inspection(
        inspection_id=inspection.id,
        db=db_session,
    )

    # Pre-2022 rules evaluated: USP rule is not triggered as violation
    checks = eval_result["checks"]
    usp_checks = [c for c in checks if "EA" in (c.rule_version.rule.rule_code if c.rule_version and c.rule_version.rule else "")]
    if usp_checks:
        assert usp_checks[0].status == ComplianceStatusEnum.NOT_APPLICABLE
