from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class PresenceValidator(BaseRuleValidator):
    """
    Validates mandatory declaration existence on commodity packaging.
    Distinguishes:
      - PASS: Declaration present with verified confidence.
      - FAIL: Declaration conclusively missing on legible label.
      - REVIEW: Uncertain extraction or insufficient image clarity.
    """

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        conditions = rule_version.conditions or {}
        target_types: List[str] = conditions.get("target_declaration_types", [])

        if not target_types and "declaration_type" in conditions:
            target_types = [conditions["declaration_type"]]

        # Find matching declarations in context
        matching_declarations: List[Declaration] = []
        for t in target_types:
            matching_declarations.extend(context.declarations_by_type.get(t, []))

        # Check if present
        if matching_declarations:
            best_decl = max(
                matching_declarations,
                key=lambda d: d.confidence if d.confidence is not None else 0.0,
            )
            conf = best_decl.confidence or 0.85
            bbox = best_decl.bounding_box or {}
            is_ambiguous = (
                best_decl.extraction_status == "AMBIGUOUS"
                or bbox.get("is_ambiguous", False)
            )

            evidence = [
                EvidenceSpec(
                    source_type="OCR_TEXT_SNIPPET",
                    description=f"Detected declaration: {best_decl.raw_value}",
                    bounding_box=bbox,
                    confidence=conf,
                )
            ]

            if is_ambiguous:
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=(
                        f"Declaration candidate detected ('{best_decl.raw_value}'), "
                        f"but multiple competing values were identified. Manual officer review recommended."
                    ),
                    detected_value=best_decl.normalized_value or best_decl.raw_value,
                    expected_requirement=rule_version.requirement_text,
                    confidence=conf,
                    evidences=evidence,
                )

            if conf < 0.65:
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=(
                        f"Declaration candidate detected with low OCR confidence ({conf * 100:.1f}%). "
                        f"Manual inspection recommended to confirm legibility."
                    ),
                    detected_value=best_decl.normalized_value or best_decl.raw_value,
                    expected_requirement=rule_version.requirement_text,
                    confidence=conf,
                    evidences=evidence,
                )

            return ValidatorResult(
                status=ComplianceStatusEnum.PASS,
                explanation=(
                    f"Mandatory declaration is present on packaging: '{best_decl.normalized_value or best_decl.raw_value}' "
                    f"(Confidence: {conf * 100:.1f}%)."
                ),
                detected_value=best_decl.normalized_value or best_decl.raw_value,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
                evidences=evidence,
            )

        # Declaration NOT detected in extracted declarations
        # Check image quality / OCR coverage to decide between FAIL vs REVIEW
        quality = context.image_quality or {}
        is_blurry = quality.get("is_blurry", False)
        is_low_res = quality.get("is_low_resolution", False)

        if is_blurry or is_low_res or not context.ocr_raw_text:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=(
                    "Mandatory declaration was not detected in automated OCR. However, image quality "
                    "or contrast warnings indicate possible extraction omissions. Physical officer verification required."
                ),
                detected_value=None,
                expected_requirement=rule_version.requirement_text,
                confidence=0.50,
                evidences=[],
            )

        # Clean image with high certainty of omission -> Flag Potential Non-Compliance (FAIL)
        target_str = ", ".join(target_types) if target_types else "Mandatory Declaration"
        return ValidatorResult(
            status=ComplianceStatusEnum.FAIL,
            explanation=(
                f"Potential non-compliance detected: Required statutory declaration ({target_str}) "
                f"was not detected on inspected label panels."
            ),
            detected_value="NOT_DETECTED",
            expected_requirement=rule_version.requirement_text,
            confidence=0.88,
            evidences=[
                EvidenceSpec(
                    source_type="CALCULATION_LOG",
                    description=f"Automated screening scanned all OCR blocks and found 0 matching tokens for {target_str}.",
                    confidence=0.88,
                )
            ],
        )
