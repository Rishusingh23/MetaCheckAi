import re
from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class FormatValidator(BaseRuleValidator):
    """
    Validates structural formatting patterns for dates, USP, emails, phones, and registrations.
    """

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        conditions = rule_version.conditions or {}
        target_type = conditions.get("declaration_type", "DATE_OF_PACKING")
        expected_pattern_str = conditions.get("expected_regex")

        declarations = context.declarations_by_type.get(target_type, [])
        if not declarations:
            # If date of packing or manufacture is checked, check both
            if target_type in ("DATE_OF_PACKING", "DATE_OF_MANUFACTURE"):
                declarations = context.declarations_by_type.get(
                    "DATE_OF_PACKING", []
                ) + context.declarations_by_type.get("DATE_OF_MANUFACTURE", [])

        if not declarations:
            quality = context.image_quality or {}
            if quality.get("is_blurry") or quality.get("is_low_resolution"):
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=f"{target_type} was not detected; image quality requires physical examination.",
                    detected_value="NOT_DETECTED",
                    expected_requirement=rule_version.requirement_text,
                    confidence=0.55,
                )
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=f"Potential non-compliance: Mandatory declaration '{target_type}' is missing on packaging.",
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
                explanation=f"Multiple conflicting format candidates detected for {target_type}. Manual officer review required.",
                detected_value=normalized,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
                evidences=evidence,
            )

        # Regex format test
        if expected_pattern_str:
            regex = re.compile(expected_pattern_str, re.IGNORECASE)
            if not regex.search(normalized) and not regex.search(raw_text):
                return ValidatorResult(
                    status=ComplianceStatusEnum.FAIL,
                    explanation=(
                        f"Potential non-compliance: Extracted format '{normalized}' does not match "
                        f"statutory format requirement per {rule_version.rule.name if rule_version.rule else 'rule'}."
                    ),
                    detected_value=normalized,
                    expected_requirement=rule_version.requirement_text,
                    confidence=conf,
                    evidences=evidence,
                )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=f"Declaration '{normalized}' matches statutory format specification.",
            detected_value=normalized,
            expected_requirement=rule_version.requirement_text,
            confidence=conf,
            evidences=evidence,
        )
