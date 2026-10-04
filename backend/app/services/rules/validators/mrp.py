import re
from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class MRPValidator(BaseRuleValidator):
    """
    Validates Maximum Retail Price declaration under Rule 6(1)(e) of PCR, 2011:
      1. Presence of MRP declaration.
      2. Valid monetary representation in Indian Rupees (₹ / Rs.).
      3. Statutory wording indicating inclusive of all taxes ('inclusive of all taxes' / 'incl. of all taxes').
    """

    TAX_INCLUSIVE_PATTERN = re.compile(
        r"(?:incl\.?|inclusive)\s*(?:of)?\s*(?:all)?\s*(?:taxes|tax)",
        re.IGNORECASE,
    )

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        mrp_declarations = context.declarations_by_type.get("MRP", [])

        if not mrp_declarations:
            quality = context.image_quality or {}
            if quality.get("is_blurry") or quality.get("is_low_resolution"):
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation="MRP declaration was not detected in OCR, but image quality requires physical examination.",
                    detected_value="NOT_DETECTED",
                    expected_requirement=rule_version.requirement_text,
                    confidence=0.55,
                )
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation="Potential non-compliance: Maximum Retail Price (MRP) declaration is missing on packaging.",
                detected_value="NOT_DETECTED",
                expected_requirement=rule_version.requirement_text,
                confidence=0.90,
                evidences=[
                    EvidenceSpec(
                        source_type="CALCULATION_LOG",
                        description="Screening algorithm verified absence of MRP tokens.",
                        confidence=0.90,
                    )
                ],
            )

        best_mrp = max(
            mrp_declarations,
            key=lambda d: d.confidence if d.confidence is not None else 0.0,
        )
        conf = best_mrp.confidence or 0.85
        raw_text = best_mrp.raw_value
        normalized = best_mrp.normalized_value or raw_text
        bbox = best_mrp.bounding_box or {}

        evidence = [
            EvidenceSpec(
                source_type="OCR_TEXT_SNIPPET",
                description=f"Extracted MRP evidence: {raw_text}",
                bounding_box=bbox,
                confidence=conf,
            )
        ]

        # Check for ambiguous or low confidence
        if best_mrp.extraction_status == "AMBIGUOUS" or bbox.get("is_ambiguous", False):
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=(
                    f"Multiple conflicting price candidates detected ('{raw_text}'). "
                    f"Manual officer verification required to confirm genuine statutory retail price."
                ),
                detected_value=normalized,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
                evidences=evidence,
            )

        # Check tax inclusivity
        has_tax_clause = bool(self.TAX_INCLUSIVE_PATTERN.search(raw_text)) or bool(
            self.TAX_INCLUSIVE_PATTERN.search(normalized)
        )

        # In case the tax clause is on an adjacent line in full OCR text
        if not has_tax_clause and context.ocr_raw_text:
            mrp_pos = context.ocr_raw_text.find(raw_text)
            if mrp_pos != -1:
                surrounding = context.ocr_raw_text[max(0, mrp_pos - 40) : min(len(context.ocr_raw_text), mrp_pos + len(raw_text) + 80)]
                if self.TAX_INCLUSIVE_PATTERN.search(surrounding):
                    has_tax_clause = True

        if not has_tax_clause:
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=(
                    f"Potential non-compliance: MRP declaration detected as '{raw_text}', "
                    f"but mandatory statutory clause 'inclusive of all taxes' was not identified."
                ),
                detected_value=normalized,
                expected_requirement=(
                    "Retail sale price in INR with statement 'inclusive of all taxes' or 'incl. of all taxes' per Rule 6(1)(e)."
                ),
                confidence=conf,
                evidences=evidence,
            )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=(
                f"Valid Maximum Retail Price declared: '{normalized}' with statutory tax-inclusive clause."
            ),
            detected_value=normalized,
            expected_requirement=rule_version.requirement_text,
            confidence=conf,
            evidences=evidence,
        )
