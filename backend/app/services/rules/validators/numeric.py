from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class NumericRangeValidator(BaseRuleValidator):
    """
    Validates numeric quantities or prices against statutory thresholds.
    """

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        conditions = rule_version.conditions or {}
        target_type = conditions.get("declaration_type", "NET_QUANTITY")
        min_val = conditions.get("min_value")
        max_val = conditions.get("max_value")

        declarations = context.declarations_by_type.get(target_type, [])
        if not declarations:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=f"Cannot evaluate numeric range: {target_type} was not detected.",
                detected_value="NOT_DETECTED",
                expected_requirement=rule_version.requirement_text,
                confidence=0.50,
            )

        best_decl = max(
            declarations,
            key=lambda d: d.confidence if d.confidence is not None else 0.0,
        )
        conf = best_decl.confidence or 0.85
        raw_text = best_decl.raw_value
        normalized = best_decl.normalized_value or raw_text

        # Extract numeric magnitude
        val = None
        for part in normalized.replace("₹", "").replace("Rs.", "").split():
            try:
                val = float(part.replace(",", ""))
                break
            except ValueError:
                continue

        if val is None:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=f"Could not parse numeric magnitude from declaration: '{normalized}'.",
                detected_value=normalized,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
            )

        if min_val is not None and val < min_val:
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=f"Potential non-compliance: Value {val} is less than statutory minimum {min_val}.",
                detected_value=str(val),
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
            )

        if max_val is not None and val > max_val:
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=f"Potential non-compliance: Value {val} exceeds statutory maximum {max_val}.",
                detected_value=str(val),
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
            )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=f"Numeric value {val} is within statutory bounds [{min_val or '-inf'}, {max_val or '+inf'}].",
            detected_value=str(val),
            expected_requirement=rule_version.requirement_text,
            confidence=conf,
        )
