from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.models.declaration import DeclarationTypeEnum, ExtractionStatusEnum
from app.services.ocr.models import BoundingBox


@dataclass
class NormalizedPrice:
    """Normalized monetary price details."""
    amount: float
    currency: str = "INR"
    is_inclusive_of_all_taxes: bool = True
    raw_amount_string: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": self.amount,
            "currency": self.currency,
            "is_inclusive_of_all_taxes": self.is_inclusive_of_all_taxes,
            "raw_amount_string": self.raw_amount_string,
        }


@dataclass
class NormalizedQuantity:
    """Normalized metric net quantity details."""
    value: float
    unit: str
    standard_unit: str  # e.g., 'g', 'kg', 'ml', 'l', 'm', 'piece', 'unit'
    standard_value: float  # Value normalized to base unit
    raw_unit_string: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "standard_unit": self.standard_unit,
            "standard_value": self.standard_value,
            "raw_unit_string": self.raw_unit_string,
        }


@dataclass
class NormalizedUSP:
    """Normalized Unit Sale Price details."""
    unit_price: float
    currency: str
    unit: str
    raw_usp_string: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_price": self.unit_price,
            "currency": self.currency,
            "unit": self.unit,
            "raw_usp_string": self.raw_usp_string,
        }


@dataclass
class NormalizedDate:
    """Normalized date details preserving partial or full dates."""
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
    iso_format: Optional[str] = None
    raw_date_string: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "iso_format": self.iso_format,
            "raw_date_string": self.raw_date_string,
        }


@dataclass
class NormalizedContact:
    """Normalized consumer care details."""
    phones: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    toll_free_numbers: List[str] = field(default_factory=list)
    address: Optional[str] = None
    website: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phones": self.phones,
            "emails": self.emails,
            "toll_free_numbers": self.toll_free_numbers,
            "address": self.address,
            "website": self.website,
        }


@dataclass
class DeclarationCandidate:
    """An extracted declaration candidate with confidence, spatial bounds, and structured metadata."""
    declaration_type: DeclarationTypeEnum
    raw_value: str
    normalized_value: str
    confidence: float
    source_text: str
    bounding_box: Optional[BoundingBox] = None
    extraction_method: str = "PATTERN"
    extraction_status: ExtractionStatusEnum = ExtractionStatusEnum.DETECTED
    confidence_rationale: str = ""
    structured_data: Optional[Dict[str, Any]] = None
    alternative_candidates: List[Dict[str, Any]] = field(default_factory=list)
    is_ambiguous: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "declaration_type": (
                self.declaration_type.value
                if hasattr(self.declaration_type, "value")
                else str(self.declaration_type)
            ),
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "confidence": round(float(self.confidence), 4),
            "source_text": self.source_text,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "extraction_method": self.extraction_method,
            "extraction_status": (
                self.extraction_status.value
                if hasattr(self.extraction_status, "value")
                else str(self.extraction_status)
            ),
            "confidence_rationale": self.confidence_rationale,
            "structured_data": self.structured_data or {},
            "alternative_candidates": self.alternative_candidates,
            "is_ambiguous": self.is_ambiguous,
        }
