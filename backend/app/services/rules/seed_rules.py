from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rule import (
    ApplicableContextEnum,
    Rule,
    RuleVerificationStatusEnum,
    RuleVersion,
    SeverityEnum,
    ValidationTypeEnum,
)

# Authoritative Statutory Rules grounded in Legal Metrology (Packaged Commodities) Rules, 2011
# Source: Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution, Govt of India
# Official Portal: https://consumeraffairs.gov.in/pages/legal-metrology-act
STATUTORY_BASELINE_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "PCR_2011_RULE_6_1_A",
        "name": "Manufacturer, Packer, or Importer Identification",
        "description": "Mandates complete name and address of the manufacturer, or where manufacturer is not the packer, the manufacturer and packer, or for imported goods the importer.",
        "legal_reference": "Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The name and complete address of the manufacturer, or where the manufacturer is not the packer, the name and address of the manufacturer and packer, or for imported goods the importer.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011, Ministry of Consumer Affairs",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011 & GSR 592(E) dated 23rd June, 2017",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": [
                        "MANUFACTURER_DETAILS",
                        "PACKER_DETAILS",
                        "IMPORTER_DETAILS",
                    ]
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_B",
        "name": "Generic or Common Name of Commodity",
        "description": "Mandates declaration of the common or generic names of the commodity contained in the package on the principal display panel.",
        "legal_reference": "Rule 6(1)(b), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The common or generic names of the commodity contained in the package shall be declared on the principal display panel.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": ["GENERIC_NAME", "PRODUCT_NAME"]
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_C",
        "name": "Net Quantity in Standard Units of Weight, Measure or Number",
        "description": "Mandates declaration of net quantity in terms of standard unit of weight, measure or number per Second Schedule.",
        "legal_reference": "Rule 6(1)(c) & Rule 11 / Second Schedule, Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The net quantity, in terms of the standard unit of weight or measure, of the commodity contained in the package or where the commodity is packed or sold by number, the number of the commodity contained in the package shall be mentioned on the package.",
                "validation_type": ValidationTypeEnum.FORMAT_CHECK,
                "severity": SeverityEnum.CRITICAL,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "NET_QUANTITY",
                    "validator": "quantity_validator",
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_D",
        "name": "Month and Year of Manufacture / Packing / Import",
        "description": "Mandates declaration of the month and year of manufacture, packing or import on the package.",
        "legal_reference": "Rule 6(1)(d), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The month and year in which the commodity is manufactured or pre-packed or imported shall be clearly indicated (Historical baseline prior to Dec 2022).",
                "validation_type": ValidationTypeEnum.FORMAT_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011 (Pre-2021 Amendment)",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": datetime(2022, 11, 30, 23, 59, 59, tzinfo=timezone.utc),
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "DATE_OF_PACKING",
                    "expected_regex": r"\b(0[1-9]|1[0-2]|[a-zA-Z]{3,9})[-/.\s]+(?:20)?[0-9]{2}\b",
                },
            },
            {
                "version": "2.0",
                "requirement_text": "The month and year in which the commodity is manufactured (or month and year of import for imported commodities, or month and year of pre-packing where packed by an entity other than the manufacturer) shall be clearly declared.",
                "validation_type": ValidationTypeEnum.FORMAT_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021 (GSR 779(E))",
                "source_gazette_reference": "GSR 779(E) dated 2nd November, 2021; effective 1st December, 2022 per GSR 758(E)",
                "active_from": datetime(2022, 12, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "DATE_OF_MANUFACTURE",
                    "expected_regex": r"\b(0[1-9]|1[0-2]|[a-zA-Z]{3,9})[-/.\s]+(?:20)?[0-9]{2}\b",
                },
            },
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_E",
        "name": "Maximum Retail Price (MRP) Inclusive of All Taxes",
        "description": "Mandates retail sale price clearly stated as Maximum Retail Price inclusive of all taxes.",
        "legal_reference": "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The retail sale price of the package shall clearly indicate Maximum or Max. retail price Rs. ... / ₹ ... inclusive of all taxes (Pre-GST wording).",
                "validation_type": ValidationTypeEnum.FORMAT_CHECK,
                "severity": SeverityEnum.CRITICAL,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": datetime(2017, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "MRP",
                    "validator": "mrp_validator",
                },
            },
            {
                "version": "2.0",
                "requirement_text": "The retail sale price of the package shall clearly indicate Maximum or Max. Retail Price Rs./₹ ... inclusive of all taxes or MRP Rs./₹ ... (inclusive of all taxes).",
                "validation_type": ValidationTypeEnum.FORMAT_CHECK,
                "severity": SeverityEnum.CRITICAL,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Amendment Rules, 2017 & 2021",
                "source_gazette_reference": "GSR 592(E) dated 23rd June, 2017 & GSR 779(E) dated 2nd November, 2021",
                "active_from": datetime(2017, 7, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "MRP",
                    "validator": "mrp_validator",
                },
            },
        ],
    },
    {
        "rule_code": "PCR_2021_RULE_6_1_EA",
        "name": "Unit Sale Price (USP) Declaration",
        "description": "Mandates Unit Sale Price in Rupees per g/ml (for <= 1kg/1L) or per kg/L (for > 1kg/1L) or per number, except standard 1-unit packages.",
        "legal_reference": "Rule 6(1)(ea) & Rule 6(11), Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The unit sale price shall be declared on every package where net quantity is more than 1 kg / 1 L in terms of Rs. per kg / per L, or where net quantity is less than 1 kg / 1 L in terms of Rs. per g / per ml, or where sold by number in terms of Rs. per number/piece; except where net quantity is exactly 1 kg, 1 L, 1 m, or 1 number.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021 (GSR 779(E))",
                "source_gazette_reference": "GSR 779(E) dated 2nd November, 2021; enforced w.e.f. 1st December, 2022 per GSR 758(E)",
                "active_from": datetime(2022, 12, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": ["UNIT_SALE_PRICE"]
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_G",
        "name": "Consumer Care Details",
        "description": "Mandates telephone number, email address, and postal contact for consumer feedback and grievance redressal.",
        "legal_reference": "Rule 6(1)(g), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "Name, address, telephone number and e-mail address of the person or office who can be contacted in case of consumer complaints shall be declared on the package.",
                "validation_type": ValidationTypeEnum.TEXT_PATTERN,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                    "E_COMMERCE_LISTING",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "CONSUMER_CARE",
                    "required_elements": ["phone", "email"],
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_6_1_H",
        "name": "Country of Origin for Imported Commodities",
        "description": "Mandates declaration of the country of origin or manufacture or assembly on imported packages.",
        "legal_reference": "Rule 6(1)(h) & Rule 6(10), Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "The name of the country of origin or manufacture or assembly in case of imported products shall be mentioned on the package.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) (Amendment) Rules, 2017 (GSR 592(E))",
                "source_gazette_reference": "GSR 592(E) dated 23rd June, 2017",
                "active_from": datetime(2017, 7, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "IMPORTED_PRODUCT",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": ["COUNTRY_OF_ORIGIN"]
                },
            }
        ],
    },
    {
        "rule_code": "PCR_2026_RULE_6_10A_ECOM",
        "name": "E-Commerce Marketplace Country of Origin & Search Filter",
        "description": "Mandates country of origin declaration and consumer search filter on marketplace e-commerce entities under Rule 6(10A).",
        "legal_reference": "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(10A)",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "Every e-commerce entity selling imported products shall provide the product listings of such imported products in a searchable and sortable filter specifying the country of origin.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Amendment Rules, 2026",
                "source_gazette_reference": "G.S.R. 128(E) dated 13th February, 2026; effective 1st July, 2026",
                "active_from": datetime(2026, 7, 1, tzinfo=timezone.utc),
                "active_to": datetime(2027, 7, 1, tzinfo=timezone.utc),
                "applicable_contexts": [
                    "E_COMMERCE_LISTING",
                    "IMPORTED_PRODUCT",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": ["COUNTRY_OF_ORIGIN"]
                },
            },
            {
                "version": "2.0",
                "requirement_text": "Every e-commerce entity offering for sale any imported product shall, with effect from 1 July 2027, ensure that the product listing of such imported product contains a searchable and sortable filter specifying the country of origin.",
                "validation_type": ValidationTypeEnum.PRESENCE_CHECK,
                "severity": SeverityEnum.MAJOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026",
                "source_gazette_reference": "G.S.R. 312(E) dated 27th April, 2026; effective 1st July, 2027",
                "active_from": datetime(2027, 7, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "E_COMMERCE_LISTING",
                    "IMPORTED_PRODUCT",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "target_declaration_types": ["COUNTRY_OF_ORIGIN"]
                },
            },
        ],
    },
    {
        "rule_code": "PCR_2011_RULE_7_8",
        "name": "Font Height and Prominence on Display Panel",
        "description": "Prescribes numeral and letter height ratio based on area of principal display panel (Table I). Uncalibrated digital photos are flagged for physical review.",
        "legal_reference": "Rules 7 & 8, Table I, Legal Metrology (Packaged Commodities) Rules, 2011",
        "versions": [
            {
                "version": "1.0",
                "requirement_text": "Declarations shall be prominent, legible, and maintain minimum numeral and character heights (1.0 mm to 6.0 mm) relative to principal display panel area as prescribed in Table I. On uncalibrated digital imagery, character height is estimated and flagged for physical verification.",
                "validation_type": ValidationTypeEnum.FONT_HEIGHT_RATIO,
                "severity": SeverityEnum.MINOR,
                "verification_status": RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
                "source_document": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "source_gazette_reference": "GSR 202(E) dated 7th March, 2011",
                "active_from": datetime(2011, 4, 1, tzinfo=timezone.utc),
                "active_to": None,
                "applicable_contexts": [
                    "PHYSICAL_PACKAGE",
                    "DOMESTIC_PRODUCT",
                    "IMPORTED_PRODUCT",
                ],
                "applicable_product_categories": ["*"],
                "conditions": {
                    "declaration_type": "NET_QUANTITY"
                },
            }
        ],
    },
]


async def seed_statutory_baseline_rules(db: AsyncSession) -> int:
    """
    Seed or update the statutory Legal Metrology baseline rules into the database.
    Returns the count of seeded/updated rules.
    """
    seeded_count = 0
    for rule_data in STATUTORY_BASELINE_RULES:
        rule_code = rule_data["rule_code"]
        existing_q = select(Rule).where(Rule.rule_code == rule_code)
        res = await db.execute(existing_q)
        rule = res.scalar_one_or_none()

        if not rule:
            rule = Rule(
                rule_code=rule_code,
                name=rule_data["name"],
                description=rule_data["description"],
                legal_reference=rule_data["legal_reference"],
                is_active=True,
            )
            db.add(rule)
            await db.flush()
            seeded_count += 1
        else:
            rule.name = rule_data["name"]
            rule.description = rule_data["description"]
            rule.legal_reference = rule_data["legal_reference"]

        # Ensure versions exist
        for v_data in rule_data["versions"]:
            ver_str = v_data["version"]
            ver_q = select(RuleVersion).where(
                RuleVersion.rule_id == rule.id,
                RuleVersion.version == ver_str,
            )
            ver_res = await db.execute(ver_q)
            ver = ver_res.scalar_one_or_none()

            if not ver:
                ver = RuleVersion(
                    rule_id=rule.id,
                    version=ver_str,
                    requirement_text=v_data["requirement_text"],
                    validation_type=v_data["validation_type"],
                    severity=v_data["severity"],
                    verification_status=v_data.get("verification_status", RuleVerificationStatusEnum.VERIFIED_OFFICIAL),
                    source_document=v_data.get("source_document"),
                    source_gazette_reference=v_data.get("source_gazette_reference"),
                    applicable_contexts=v_data.get("applicable_contexts"),
                    conditions=v_data.get("conditions"),
                    applicable_product_categories=v_data.get("applicable_product_categories"),
                    active_from=v_data.get("active_from"),
                    active_to=v_data.get("active_to"),
                )
                db.add(ver)
            else:
                ver.requirement_text = v_data["requirement_text"]
                ver.validation_type = v_data["validation_type"]
                ver.severity = v_data["severity"]
                ver.verification_status = v_data.get("verification_status", RuleVerificationStatusEnum.VERIFIED_OFFICIAL)
                ver.source_document = v_data.get("source_document")
                ver.source_gazette_reference = v_data.get("source_gazette_reference")
                ver.applicable_contexts = v_data.get("applicable_contexts")
                ver.conditions = v_data.get("conditions")
                ver.applicable_product_categories = v_data.get("applicable_product_categories")
                ver.active_from = v_data.get("active_from")
                ver.active_to = v_data.get("active_to")

    await db.commit()
    return seeded_count

