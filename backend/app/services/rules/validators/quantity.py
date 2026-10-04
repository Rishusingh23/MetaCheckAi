import re
from typing import List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, EvidenceSpec, ValidatorResult
from app.services.rules.validators.base import BaseRuleValidator


class QuantityValidator(BaseRuleValidator):
    """
    Validates Net Quantity declaration under Rule 6(1)(c) and Rule 11 / Second Schedule of PCR, 2011:
      1. Presence of Net Quantity declaration.
      2. Valid statutory metric unit of measurement (g, kg, ml, l/L, m, N/units).
      3. Non-standard symbols (e.g. 'gms', 'kilo', 'litres' without standard unit symbol) are flagged.
      4. Positive non-zero numeric magnitude.
    """

    VALID_METRIC_UNITS = {
        # Standard metric units of weight, volume, length
        "g", "kg", "mg", "ml", "l", "m", "cm", "mm",
        # Standard count / number units permitted under Rule 6(1)(c) and Rule 11
        "n", "u", "unit", "units", "piece", "pieces", "pc", "pcs", "no", "nos",
        "tab", "tablets", "capsule", "capsules", "sachet", "sachets", "pair", "pairs", "set", "count",
    }

    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        qty_declarations = context.declarations_by_type.get("NET_QUANTITY", [])

        if not qty_declarations:
            quality = context.image_quality or {}
            if quality.get("is_blurry") or quality.get("is_low_resolution"):
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation="Net quantity declaration was not detected in OCR, but image quality requires physical examination.",
                    detected_value="NOT_DETECTED",
                    expected_requirement=rule_version.requirement_text,
                    confidence=0.55,
                )
            return ValidatorResult(
                status=ComplianceStatusEnum.FAIL,
                explanation="Potential non-compliance: Net quantity declaration is missing on packaging.",
                detected_value="NOT_DETECTED",
                expected_requirement=rule_version.requirement_text,
                confidence=0.92,
                evidences=[
                    EvidenceSpec(
                        source_type="CALCULATION_LOG",
                        description="Screening algorithm verified absence of net quantity declaration.",
                        confidence=0.92,
                    )
                ],
            )

        best_qty = max(
            qty_declarations,
            key=lambda d: d.confidence if d.confidence is not None else 0.0,
        )
        conf = best_qty.confidence or 0.85
        raw_text = best_qty.raw_value
        normalized = best_qty.normalized_value or raw_text
        bbox = best_qty.bounding_box or {}

        evidence = [
            EvidenceSpec(
                source_type="OCR_TEXT_SNIPPET",
                description=f"Extracted Net Quantity evidence: {raw_text}",
                bounding_box=bbox,
                confidence=conf,
            )
        ]

        if best_qty.extraction_status == "AMBIGUOUS" or bbox.get("is_ambiguous", False):
            return ValidatorResult(
                status=ComplianceStatusEnum.REVIEW,
                explanation=(
                    f"Multiple competing quantity candidates detected ('{raw_text}'). "
                    f"Manual officer verification required to confirm genuine declared net weight/volume."
                ),
                detected_value=normalized,
                expected_requirement=rule_version.requirement_text,
                confidence=conf,
                evidences=evidence,
            )

        # Check for valid standardized unit in normalized output (e.g. '500 g', '1 kg', '250 ml')
        parts = normalized.split()
        if len(parts) >= 2:
            magnitude_str, unit_str = parts[0], parts[1].lower()
            try:
                mag_val = float(magnitude_str.replace(",", ""))
                if mag_val <= 0:
                    return ValidatorResult(
                        status=ComplianceStatusEnum.FAIL,
                        explanation=f"Potential non-compliance: Net quantity numeric value '{magnitude_str}' must be greater than zero.",
                        detected_value=normalized,
                        expected_requirement=rule_version.requirement_text,
                        confidence=conf,
                        evidences=evidence,
                    )
            except ValueError:
                pass

            if unit_str not in self.VALID_METRIC_UNITS:
                return ValidatorResult(
                    status=ComplianceStatusEnum.REVIEW,
                    explanation=(
                        f"Net quantity declared unit '{unit_str}' in '{normalized}' requires officer review "
                        f"against Second Schedule metric standards."
                    ),
                    detected_value=normalized,
                    expected_requirement=rule_version.requirement_text,
                    confidence=conf,
                    evidences=evidence,
                )

        return ValidatorResult(
            status=ComplianceStatusEnum.PASS,
            explanation=f"Valid Net Quantity declared in standard metric units: '{normalized}'.",
            detected_value=normalized,
            expected_requirement=rule_version.requirement_text,
            confidence=conf,
            evidences=evidence,
        )
