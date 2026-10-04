import re
from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class TextPatternValidator(BaseRuleValidator):
    """
    Validates specific mandatory textual declarations (e.g. Consumer Care multi-modal contact, Manufacturer street address).
    """

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        conditions = rule_version.conditions or {}
        target_type = conditions.get("declaration_type", "CONSUMER_CARE")
        required_elements = conditions.get("required_elements", [])  # e.g. ["phone", "email"]

        declarations = context.declarations_by_type.get(target_type, [])
        if not declarations:
            quality = context.image_quality or {}
            if quality.get("is_blurry") or quality.get("is_low_resolution"):
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=f"{target_type} details not detected; image quality requires physical examination.",
                    detected_value="NOT_DETECTED",
                    expected_requirement=rule_version.requirement_text,
                    confidence=0.55,
                )
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=f"Potential non-compliance: Required statutory declaration '{target_type}' is missing.",
                detected_value="NOT_DETECTED",
                expected_requirement=rule_version.requirement_text,
                confidence=0.88,
            )

        best_decl = max(
            declarations,
            key=lambda d: d.confidence if d.confidence is not None else 0.0,
        )
        conf = best_decl.confidence or 0.85
        raw_text = best_decl.raw_value
        normalized = best_decl.normalized_value or raw_text
        bbox = best_decl.bounding_box or {}

        evidence = [
            EvidenceSpec(
                source_type="OCR_TEXT_SNIPPET",
                description=f"Extracted {target_type} evidence: {raw_text}",
                bounding_box=bbox,
                confidence=conf,
            )
        ]

        if best_decl.extraction_status == "AMBIGUOUS" or bbox.get("is_ambiguous", False):
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=f"Conflicting candidates for {target_type}. Manual officer verification recommended.",
                detected_value=normalized,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
                evidences=evidence,
            )

        # If required sub-elements are specified (e.g. phone/email in consumer care)
        if target_type == "CONSUMER_CARE" and required_elements:
            missing_elements = []
            if "phone" in required_elements and not re.search(
                r"(?:1800|1860|\+?91)[\s\-]?[0-9]{3,4}[\s\-]?[0-9]{3,4}|\b[0-9]{3,5}[\s\-]?[0-9]{6,8}\b|\b[0-9]{10,11}\b",
                raw_text,
            ):
                missing_elements.append("telephone/toll-free number")
            if "email" in required_elements and "@" not in raw_text:
                missing_elements.append("email address")

            if missing_elements:
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=(
                        f"Consumer care details partially detected ('{normalized}'), but missing: "
                        f"{', '.join(missing_elements)}. Manual verification recommended under Rule 6(1)(g)."
                    ),
                    detected_value=normalized,
                    expected_requirement=rule_version.requirement_text,
                    confidence=conf,
                    evidences=evidence,
                )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=f"Statutory text requirements satisfied: '{normalized}'.",
            detected_value=normalized,
            expected_requirement=rule_version.requirement_text,
            confidence=conf,
            evidences=evidence,
        )
