from abc import ABC, abstractmethod
from app.models.rule import RuleVersion
from app.services.rules.models import EvaluationContext, ValidatorResult


class BaseRuleValidator(ABC):
    """Abstract base validator interface for all Legal Metrology rules."""

    @abstractmethod
    def validate(
        self,
        context: EvaluationContext,
        rule_version: RuleVersion,
    ) -> ValidatorResult:
        """
        Evaluate a specific RuleVersion against the inspection context declarations.
        Must return a structured ValidatorResult.
        """
        pass
