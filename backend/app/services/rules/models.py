from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.models.compliance import ComplianceStatusEnum
from app.models.declaration import Declaration
from app.models.product import Product
from app.models.rule import RuleVersion, SeverityEnum, ValidationTypeEnum


@dataclass
class EvidenceSpec:
    """Specification for evidence to be persisted for a compliance check."""
    source_type: str  # e.g. "OCR_TEXT_SNIPPET", "LABEL_IMAGE_CROP", "CALCULATION_LOG"
    description: str
    bounding_box: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    image_url_or_path: Optional[str] = None


@dataclass
class ValidatorResult:
    """Structured result returned by any rule validator."""
    status: ComplianceStatusEnum
    explanation: str
    detected_value: Optional[str] = None
    expected_requirement: Optional[str] = None
    confidence: float = 0.90
    evidences: List[EvidenceSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationContext:
    """Full operational context passed into the rule evaluation engine."""
    inspection_id: str
    product: Optional[Product]
    inspection_date: datetime
    declarations: List[Declaration]
    declarations_by_type: Dict[str, List[Declaration]] = field(default_factory=dict)
    ocr_raw_text: Optional[str] = None
    image_quality: Optional[Dict[str, Any]] = None
    applicable_context: str = "PHYSICAL_PACKAGE"  # e.g. PHYSICAL_PACKAGE, E_COMMERCE_LISTING
    is_imported: bool = False
    is_e_commerce: bool = False

    def __post_init__(self):
        if not self.declarations_by_type and self.declarations:
            by_type: Dict[str, List[Declaration]] = {}
            for d in self.declarations:
                t_str = d.declaration_type.value if hasattr(d.declaration_type, "value") else str(d.declaration_type)
                by_type.setdefault(t_str, []).append(d)
            self.declarations_by_type = by_type


@dataclass
class FindingRecord:
    """Single evaluated finding connecting RuleVersion with evaluated outcome."""
    rule_version: RuleVersion
    rule_code: str
    rule_name: str
    legal_reference: str
    status: ComplianceStatusEnum
    severity: SeverityEnum
    explanation: str
    detected_value: Optional[str]
    expected_requirement: Optional[str]
    confidence: float
    evidences: List[EvidenceSpec]
    is_violation: bool = False
