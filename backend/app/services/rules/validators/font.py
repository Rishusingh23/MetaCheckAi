from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class FontReadabilityValidator(BaseRuleValidator):
    """
    Evaluates declaration numeral and character height ratios under Rules 7 & 8 / Table 1 of PCR 2011.

    IMPORTANT STATUTORY CALIBRATION STANDARD:
    An uncalibrated digital photograph cannot provide definitive physical millimeter dimensions.
    The validator evaluates estimated pixel character height and relative visual proportions,
    and returns REVIEW for uncalibrated images with an explicit physical verification recommendation.
    """

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        conditions = rule_version.conditions or {}
        target_type = conditions.get("declaration_type", "NET_QUANTITY")

        matching_declarations = context.declarations_by_type.get(target_type, [])
        if not matching_declarations:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=(
                    f"Font size evaluation for {target_type} could not be conducted because no "
                    f"matching declaration bounding coordinates were detected."
                ),
                detected_value="NO_BOUNDING_BOX",
                expected_requirement=rule_version.requirement_text,
                confidence=0.50,
            )

        best_decl = max(
            matching_declarations,
            key=lambda d: d.confidence if d.confidence is not None else 0.0,
        )
        bbox = best_decl.bounding_box or {}
        y1, y2 = bbox.get("y1"), bbox.get("y2")

        if y1 is None or y2 is None:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation="Bounding box coordinate metadata is missing for character height estimation.",
                detected_value="NO_COORDINATES",
                expected_requirement=rule_version.requirement_text,
                confidence=0.50,
            )

        pixel_height = max(1, y2 - y1)
        # Quality check
        quality = context.image_quality or {}
        total_height = quality.get("height", 800)
        relative_ratio = pixel_height / float(total_height) if total_height > 0 else 0.02

        evidence = [
            EvidenceSpec(
                source_type="CALCULATION_LOG",
                description=(
                    f"Estimated bounding box pixel height: {pixel_height}px "
                    f"(relative panel height ratio: {relative_ratio * 100:.2f}%)."
                ),
                bounding_box=bbox,
                confidence=best_decl.confidence or 0.85,
            )
        ]

        # Calibration check: Statutory inspection protocol requires physical verification for uncalibrated imagery
        calibrated_scale = quality.get("calibrated_scale_px_per_mm")
        if not calibrated_scale:
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=(
                    f"Estimated character height (~{pixel_height}px, panel ratio: {relative_ratio * 100:.1f}%) "
                    f"appears visually readable. However, because uncalibrated 2D digital photographs cannot "
                    f"statutorily certify physical millimeter heights under Rule 7 Table I, physical verification "
                    f"with a calibrated scale is recommended."
                ),
                detected_value=f"~{pixel_height} px (Uncalibrated)",
                expected_requirement=rule_version.requirement_text,
                confidence=0.75,
                evidences=evidence,
            )

        # When calibrated scale is present (px per mm)
        mm_height = pixel_height / float(calibrated_scale)
        if mm_height < 1.0:
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation=(
                    f"Potential non-compliance detected: Calibrated character height is {mm_height:.2f} mm, "
                    f"which is below the minimum statutory threshold (1.0 mm) under Rule 7 Table I."
                ),
                detected_value=f"{mm_height:.2f} mm",
                expected_requirement=rule_version.requirement_text,
                confidence=0.90,
                evidences=evidence,
            )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=(
                f"Calibrated character height of {mm_height:.2f} mm satisfies statutory minimum "
                f"height requirements under Rule 7 Table I."
            ),
            detected_value=f"{mm_height:.2f} mm",
            expected_requirement=rule_version.requirement_text,
            confidence=0.90,
            evidences=evidence,
        )
