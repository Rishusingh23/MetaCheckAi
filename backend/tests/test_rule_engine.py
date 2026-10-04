import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration, DeclarationTypeEnum, ExtractionStatusEnum
from app.models.inspection import Inspection, InspectionSourceEnum, InspectionStatusEnum
from app.models.product import Product
from app.models.rule import Rule, RuleVersion, SeverityEnum, ValidationTypeEnum
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.models.user import Role, User
from app.services.rules.applicability import is_rule_version_applicable, is_rule_version_temporally_valid
from app.services.rules.engine import rule_engine
from app.services.rules.models import EvaluationContext
from app.services.rules.seed_rules import seed_statutory_baseline_rules
from app.services.rules.validators.mrp import MRPValidator
from app.services.rules.validators.presence import PresenceValidator
from app.services.rules.validators.quantity import QuantityValidator


@pytest.mark.asyncio
async def test_statutory_baseline_rules_seeding(db_session: AsyncSession):
    count = await seed_statutory_baseline_rules(db_session)
    assert count >= 8

    # Idempotent re-seed should not create duplicates
    recount = await seed_statutory_baseline_rules(db_session)
    assert recount == 0


@pytest.mark.asyncio
async def test_rule_version_temporal_applicability():
    rule = Rule(
        rule_code="PCR_2011_RULE_6_1_EA",
        name="Unit Sale Price",
        legal_reference="Rule 6(1)(ea)",
        is_active=True,
    )
    # Effective from Dec 1, 2022
    version_usp = RuleVersion(
        rule=rule,
        version="1.0",
        requirement_text="Mandatory Unit Sale Price",
        validation_type=ValidationTypeEnum.PRESENCE_CHECK,
        severity=SeverityEnum.MAJOR,
        active_from=datetime(2022, 12, 1, tzinfo=timezone.utc),
    )

    # Date in 2020: should NOT be active
    date_2020 = datetime(2020, 6, 1, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(version_usp, date_2020) is False

    # Date in 2026: should be active
    date_2026 = datetime(2026, 4, 1, tzinfo=timezone.utc)
    assert is_rule_version_temporally_valid(version_usp, date_2026) is True


@pytest.mark.asyncio
async def test_mrp_validator_tax_clause_logic():
    validator = MRPValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="MRP inclusive of all taxes",
        validation_type=ValidationTypeEnum.FORMAT_CHECK,
        severity=SeverityEnum.CRITICAL,
    )

    # Case 1: MRP with proper tax clause -> PASS
    decl_pass = Declaration(
        declaration_type=DeclarationTypeEnum.MRP,
        raw_value="MRP Rs. 250.00 (Incl. of all taxes)",
        normalized_value="₹ 250.00 (Incl. of all taxes)",
        confidence=0.95,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    ctx_pass = EvaluationContext(
        inspection_id="insp-1",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_pass],
        ocr_raw_text="MRP Rs. 250.00 (Incl. of all taxes)",
    )
    res_pass = validator.validate(ctx_pass, rule_ver)
    assert res_pass.status == ComplianceStatusEnum.PASS

    # Case 2: MRP without tax clause -> FAIL
    decl_fail = Declaration(
        declaration_type=DeclarationTypeEnum.MRP,
        raw_value="MRP Rs. 250.00",
        normalized_value="₹ 250.00",
        confidence=0.92,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    ctx_fail = EvaluationContext(
        inspection_id="insp-2",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_fail],
        ocr_raw_text="MRP Rs. 250.00",
    )
    res_fail = validator.validate(ctx_fail, rule_ver)
    assert res_fail.status == ComplianceStatusEnum.FAIL
    assert "inclusive of all taxes" in res_fail.explanation


@pytest.mark.asyncio
async def test_quantity_validator_metric_units():
    validator = QuantityValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="Net quantity in standard metric units",
        validation_type=ValidationTypeEnum.FORMAT_CHECK,
        severity=SeverityEnum.CRITICAL,
    )

    # Case 1: Standard metric unit -> PASS
    decl_valid = Declaration(
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="Net Wt: 500g",
        normalized_value="500 g",
        confidence=0.96,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    ctx_valid = EvaluationContext(
        inspection_id="insp-1",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_valid],
        ocr_raw_text="Net Wt: 500g",
    )
    res_valid = validator.validate(ctx_valid, rule_ver)
    assert res_valid.status == ComplianceStatusEnum.PASS


@pytest.mark.asyncio
async def test_presence_validator_ambiguous_and_missing():
    validator = PresenceValidator()
    rule_ver = RuleVersion(
        version="1.0",
        requirement_text="Mandatory Consumer Care",
        validation_type=ValidationTypeEnum.PRESENCE_CHECK,
        severity=SeverityEnum.MAJOR,
        conditions={"target_declaration_types": ["CONSUMER_CARE"]},
    )

    # Case 1: Ambiguous candidate -> REVIEW
    decl_ambiguous = Declaration(
        declaration_type=DeclarationTypeEnum.CONSUMER_CARE,
        raw_value="Call: 1800-111 / 1800-222",
        confidence=0.70,
        extraction_status=ExtractionStatusEnum.AMBIGUOUS,
        bounding_box={"is_ambiguous": True},
    )
    ctx_ambiguous = EvaluationContext(
        inspection_id="insp-1",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[decl_ambiguous],
        ocr_raw_text="Call: 1800-111 / 1800-222",
    )
    res_ambiguous = validator.validate(ctx_ambiguous, rule_ver)
    assert res_ambiguous.status == ComplianceStatusEnum.REVIEW

    # Case 2: Missing on clean image -> FAIL
    ctx_missing = EvaluationContext(
        inspection_id="insp-2",
        product=None,
        inspection_date=datetime.now(timezone.utc),
        declarations=[],
        ocr_raw_text="Only generic text without any consumer care contact.",
        image_quality={"is_blurry": False, "is_low_resolution": False},
    )
    res_missing = validator.validate(ctx_missing, rule_ver)
    assert res_missing.status == ComplianceStatusEnum.FAIL


@pytest.mark.asyncio
async def test_full_inspection_compliance_evaluation_workflow(db_session: AsyncSession):
    # Setup test entities
    role = Role(name="OFFICER_EVAL", description="Enforcement Officer")
    db_session.add(role)
    await db_session.flush()

    user = User(
        email="officer_rules@metacheck.gov.in",
        name="Inspector Sharma",
        password_hash="hash",
        role_id=role.id,
    )
    db_session.add(user)

    product = Product(
        name="Sunfeast Dark Fantasy 300g",
        brand="Sunfeast",
        category="Biscuits & Confectionery",
        barcode_gtin="8901030112233",
    )
    db_session.add(product)
    await db_session.flush()

    inspection = Inspection(
        product_id=product.id,
        inspector_id=user.id,
        status=InspectionStatusEnum.PROCESSING,
        source_type=InspectionSourceEnum.PORTAL_UPLOAD,
        inspection_date=datetime(2026, 3, 15, tzinfo=timezone.utc),
    )
    db_session.add(inspection)
    await db_session.flush()

    scan = Scan(
        inspection_id=inspection.id,
        image_path="/storage/scans/sample.jpg",
        panel_type=PanelTypeEnum.BACK_DECLARATION,
        processing_status=ScanStatusEnum.COMPLETED,
    )
    db_session.add(scan)
    await db_session.flush()

    # Add Declarations (Compliant Net Qty, Compliant MRP, Missing Consumer Care)
    decl_qty = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="Net Weight: 300g",
        normalized_value="300 g",
        confidence=0.96,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    decl_mrp = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.MRP,
        raw_value="MRP Rs. 150.00 (Incl. of all taxes)",
        normalized_value="₹ 150.00 (Incl. of all taxes)",
        confidence=0.94,
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    db_session.add_all([decl_qty, decl_mrp])
    await db_session.commit()

    # Execute Compliance Evaluation
    eval_result = await rule_engine.evaluate_inspection(
        inspection_id=inspection.id,
        db=db_session,
        user_id=user.id,
    )

    assert eval_result["inspection_id"] == inspection.id
    assert eval_result["total_rules_evaluated"] >= 8
    assert eval_result["pass_count"] >= 2
    assert "POTENTIAL_NON_COMPLIANCE" in eval_result["overall_status"] or "REVIEW_REQUIRED" in eval_result["overall_status"]
    assert eval_result["violations_flagged"] >= 1

    # Verify Idempotency: Re-evaluating does not create uncontrolled duplicates
    re_eval = await rule_engine.evaluate_inspection(
        inspection_id=inspection.id,
        db=db_session,
        user_id=user.id,
    )
    assert re_eval["total_rules_evaluated"] == eval_result["total_rules_evaluated"]
    assert re_eval["violations_flagged"] == eval_result["violations_flagged"]
