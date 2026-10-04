import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Role,
    RoleEnum,
    User,
    Product,
    ProductImage,
    ImageTypeEnum,
    Inspection,
    InspectionStatusEnum,
    InspectionSourceEnum,
    OverallResultEnum,
    Scan,
    ScanStatusEnum,
    PanelTypeEnum,
    OCRResult,
    Declaration,
    DeclarationTypeEnum,
    ExtractionStatusEnum,
    Rule,
    RuleVersion,
    ValidationTypeEnum,
    SeverityEnum,
    ComplianceCheck,
    ComplianceStatusEnum,
    Violation,
    ViolationStatusEnum,
    ViolationSeverityEnum,
    Evidence,
    EvidenceSourceTypeEnum,
    Report,
    ReportTypeEnum,
    ReportFormatEnum,
    ReportStatusEnum,
    InspectionHistory,
)


@pytest.mark.asyncio
async def test_full_model_hierarchy(db_session: AsyncSession):
    # 1. Role & User
    role = Role(name="MODEL_TEST_ADMIN", description="System Administrator")
    db_session.add(role)
    await db_session.flush()

    user = User(
        name="Officer Rajesh Kumar",
        email="rajesh.k@gov.in",
        password_hash="hashed_secret_123",
        role_id=role.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # 2. Product & ProductImage
    product = Product(
        name="Fortified Sunflower Oil 1L",
        brand="SunPure Agro",
        category="Edible Oils",
        manufacturer="SunPure Refineries Ltd",
        packer="SunPure Agro Foods",
        barcode_gtin="8901234567890",
        country_of_origin="India",
        description="Packaged pouch commodity",
    )
    db_session.add(product)
    await db_session.flush()

    image = ProductImage(
        product_id=product.id,
        image_url_or_path="/uploads/products/oil_pdp.jpg",
        image_type=ImageTypeEnum.FRONT_PDP,
        file_metadata={"width": 1920, "height": 1080},
    )
    db_session.add(image)
    await db_session.flush()

    # 3. Inspection
    inspection = Inspection(
        product_id=product.id,
        inspector_id=user.id,
        status=InspectionStatusEnum.PROCESSING,
        source_type=InspectionSourceEnum.PORTAL_UPLOAD,
        overall_result_placeholder=OverallResultEnum.PENDING_VERIFICATION,
        notes="Field sample collected from Delhi central retail market.",
    )
    db_session.add(inspection)
    await db_session.flush()

    # 4. Scan & OCRResult
    scan = Scan(
        inspection_id=inspection.id,
        product_image_id=image.id,
        image_path="/uploads/scans/scan_001.jpg",
        panel_type=PanelTypeEnum.FRONT_PDP,
        processing_status=ScanStatusEnum.COMPLETED,
    )
    db_session.add(scan)
    await db_session.flush()

    ocr = OCRResult(
        scan_id=scan.id,
        extracted_text="SunPure Fortified Sunflower Oil Net Qty: 1 L MRP Rs. 145.00",
        confidence=0.95,
        bounding_boxes={"boxes": [[10, 10, 100, 50]]},
        ocr_engine="Tesseract OCR v5",
    )
    db_session.add(ocr)
    await db_session.flush()

    # 5. Declaration
    declaration = Declaration(
        scan_id=scan.id,
        declaration_type=DeclarationTypeEnum.NET_QUANTITY,
        raw_value="1 L",
        normalized_value="1000 ml",
        confidence=0.98,
        source_text="Net Qty: 1 L",
        bounding_box={"x": 50, "y": 120, "w": 80, "h": 20},
        extraction_status=ExtractionStatusEnum.DETECTED,
    )
    db_session.add(declaration)
    await db_session.flush()

    # 6. Rule & RuleVersion
    rule = Rule(
        rule_code="PCR_2011_RULE_6_1_C",
        name="Net Quantity Declaration",
        description="Mandatory declaration of net quantity in standard metric units.",
        legal_reference="The Legal Metrology (Packaged Commodities) Rules, 2011, Rule 6(1)(c)",
        is_active=True,
    )
    db_session.add(rule)
    await db_session.flush()

    rule_version = RuleVersion(
        rule_id=rule.id,
        version="1.0.0",
        requirement_text="Net quantity must be declared in metric units with minimum prescribed font height.",
        validation_type=ValidationTypeEnum.PRESENCE_CHECK,
        severity=SeverityEnum.CRITICAL,
        evidence_required=True,
        source_gazette_reference="GSR 202(E) 2011",
    )
    db_session.add(rule_version)
    await db_session.flush()

    # 7. ComplianceCheck & Violation
    check = ComplianceCheck(
        inspection_id=inspection.id,
        rule_version_id=rule_version.id,
        status=ComplianceStatusEnum.PASS,
        explanation="Net quantity '1 L' detected with valid metric symbol.",
        detected_value="1 L",
        expected_requirement="Metric volume declaration (L / ml)",
        confidence=0.98,
    )
    db_session.add(check)
    await db_session.flush()

    violation = Violation(
        inspection_id=inspection.id,
        compliance_check_id=check.id,
        violation_code="VIOL_USP_RATIO_DEFICIENT",
        description="Potential non-compliance detected: USP font height ratio appears deficient.",
        severity=ViolationSeverityEnum.MAJOR,
        status=ViolationStatusEnum.FLAGGED_FOR_REVIEW,
    )
    db_session.add(violation)
    await db_session.flush()

    # 8. Evidence
    evidence = Evidence(
        inspection_id=inspection.id,
        violation_id=violation.id,
        source_type=EvidenceSourceTypeEnum.LABEL_IMAGE_CROP,
        image_url_or_path="/evidence/crop_usp_001.jpg",
        description="Cropped bounding box around Unit Sale Price declaration",
        confidence=0.92,
    )
    db_session.add(evidence)
    await db_session.flush()

    # 9. Report & InspectionHistory
    report = Report(
        inspection_id=inspection.id,
        report_type=ReportTypeEnum.INSPECTION_SUMMARY,
        file_path="/reports/INS_001_SUMMARY.pdf",
        format=ReportFormatEnum.PDF,
        generated_by=user.id,
        status=ReportStatusEnum.READY,
    )
    db_session.add(report)
    await db_session.flush()

    history = InspectionHistory(
        inspection_id=inspection.id,
        user_id=user.id,
        action="OFFICER_REVIEW_COMPLETED",
        previous_status=InspectionStatusEnum.CREATED.value,
        new_status=InspectionStatusEnum.PROCESSING.value,
        change_metadata={"note": "Initial screening completed"},
    )
    db_session.add(history)
    await db_session.commit()

    # Verify query and assertions
    query = select(Inspection).where(Inspection.id == inspection.id)
    result = await db_session.execute(query)
    saved_inspection = result.scalar_one()

    assert saved_inspection.id == inspection.id
    assert saved_inspection.product_id == product.id
    assert saved_inspection.inspector_id == user.id
