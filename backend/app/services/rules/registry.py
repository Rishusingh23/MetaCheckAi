from typing import Dict, Optional
from app.models.rule import RuleVersion, ValidationTypeEnum
from app.services.rules.validators.base import BaseRuleValidator
from app.services.rules.validators.font import FontReadabilityValidator
from app.services.rules.validators.format import FormatValidator
from app.services.rules.validators.mrp import MRPValidator
from app.services.rules.validators.numeric import NumericRangeValidator
from app.services.rules.validators.presence import PresenceValidator
from app.services.rules.validators.quantity import QuantityValidator
from app.services.rules.validators.text import TextPatternValidator


class RuleValidatorRegistry:
    """Registry maintaining active validator implementations for Rule evaluation."""

    def __init__(self):
        self._presence_validator = PresenceValidator()
        self._format_validator = FormatValidator()
        self._numeric_validator = NumericRangeValidator()
        self._text_validator = TextPatternValidator()
        self._font_validator = FontReadabilityValidator()
        self._mrp_validator = MRPValidator()
        self._quantity_validator = QuantityValidator()

    def get_validator_for_rule(self, rule_version: RuleVersion) -> BaseRuleValidator:
        """
        Resolve the most appropriate validator based on validation_type and domain conditions.
        """
        conditions = rule_version.conditions or {}
        val_type = rule_version.validation_type

        # Check domain-specific validator overrides
        validator_name = conditions.get("validator")
        if validator_name == "mrp_validator" or conditions.get("declaration_type") == "MRP" and val_type == ValidationTypeEnum.FORMAT_CHECK:
            return self._mrp_validator
        if validator_name == "quantity_validator" or conditions.get("declaration_type") == "NET_QUANTITY" and val_type == ValidationTypeEnum.FORMAT_CHECK:
            return self._quantity_validator

        # Standard ValidationTypeEnum mapping
        if val_type == ValidationTypeEnum.PRESENCE_CHECK:
            return self._presence_validator
        elif val_type == ValidationTypeEnum.FORMAT_CHECK:
            return self._format_validator
        elif val_type == ValidationTypeEnum.NUMERIC_RANGE:
            return self._numeric_validator
        elif val_type == ValidationTypeEnum.TEXT_PATTERN:
            return self._text_validator
        elif val_type == ValidationTypeEnum.FONT_HEIGHT_RATIO:
            return self._font_validator

        # Fallback to presence validator
        return self._presence_validator


# Global singleton instance
validator_registry = RuleValidatorRegistry()
