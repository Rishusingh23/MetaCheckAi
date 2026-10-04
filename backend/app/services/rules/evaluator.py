from app.models.compliance import ComplianceStatusEnum
from app.models.rule import RuleVersion, SeverityEnum
from app.services.rules.applicability import is_rule_version_applicable
from app.services.rules.models import EvaluationContext, FindingRecord, ValidatorResult
from app.services.rules.registry import validator_registry


class RuleEvaluator:
    """Evaluates a single RuleVersion against the inspection context."""

    def evaluate(
        self,
        rule_version: RuleVersion,
        context: EvaluationContext,
    ) -> FindingRecord:
        rule = rule_version.rule
        rule_code = rule.rule_code if rule else "UNKNOWN_RULE"
        rule_name = rule.name if rule else "Unknown Rule"
        legal_ref = rule.legal_reference if rule else "Statutory Reference Unavailable"
        severity = rule_version.severity or SeverityEnum.MAJOR

        # 1. Applicability Check
        if not is_rule_version_applicable(
            rule_version,
            context.inspection_date,
            context.product,
            applicable_context=context.applicable_context,
            is_imported=context.is_imported,
            is_e_commerce=context.is_e_commerce,
        ):
            return FindingRecord(
                rule_version=rule_version,
                rule_code=rule_code,
                rule_name=rule_name,
                legal_reference=legal_ref,
                status=ComplianceStatusEnum.NOT_APPLICABLE,
                severity=severity,
                explanation=f"Rule {rule_code} (v{rule_version.version}) is not applicable to this inspection context, product category, or effective date.",
                detected_value=None,
                expected_requirement=rule_version.requirement_text,
                confidence=1.0,
                evidences=[],
                is_violation=False,
            )

        # 2. Resolve Validator
        validator = validator_registry.get_validator_for_rule(rule_version)

        # 3. Execute Validation
        res: ValidatorResult = validator.validate(context, rule_version)

        is_violation = res.status == ComplianceStatusEnum.FAIL

        return FindingRecord(
            rule_version=rule_version,
            rule_code=rule_code,
            rule_name=rule_name,
            legal_reference=legal_ref,
            status=res.status,
            severity=severity,
            explanation=res.explanation,
            detected_value=res.detected_value,
            expected_requirement=res.expected_requirement or rule_version.requirement_text,
            confidence=res.confidence,
            evidences=res.evidences,
            is_violation=is_violation,
        )


rule_evaluator = RuleEvaluator()
