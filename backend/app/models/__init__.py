"""
SQLAlchemy ORM Models Package.
Exports all models for Alembic migrations and application services.
"""
from app.db.base import Base
from app.models.user import Role, User, RoleEnum
from app.models.product import Product, ProductImage, ImageTypeEnum
from app.models.inspection import (
    Inspection,
    InspectionStatusEnum,
    InspectionSourceEnum,
    OverallResultEnum,
)
from app.models.scan import Scan, ScanStatusEnum, PanelTypeEnum
from app.models.ocr import OCRResult
from app.models.declaration import (
    Declaration,
    DeclarationTypeEnum,
    ExtractionStatusEnum,
)
from app.models.rule import (
    Rule,
    RuleVersion,
    ValidationTypeEnum,
    SeverityEnum,
)
from app.models.compliance import ComplianceCheck, ComplianceStatusEnum
from app.models.violation import (
    Violation,
    ViolationStatusEnum,
    ViolationSeverityEnum,
)
from app.models.evidence import Evidence, EvidenceSourceTypeEnum
from app.models.report import (
    Report,
    ReportTypeEnum,
    ReportFormatEnum,
    ReportStatusEnum,
)
from app.models.history import InspectionHistory

__all__ = [
    "Base",
    # User & Role
    "Role",
    "User",
    "RoleEnum",
    # Product
    "Product",
    "ProductImage",
    "ImageTypeEnum",
    # Inspection
    "Inspection",
    "InspectionStatusEnum",
    "InspectionSourceEnum",
    "OverallResultEnum",
    # Scan & OCR
    "Scan",
    "ScanStatusEnum",
    "PanelTypeEnum",
    "OCRResult",
    # Declaration
    "Declaration",
    "DeclarationTypeEnum",
    "ExtractionStatusEnum",
    # Rule
    "Rule",
    "RuleVersion",
    "ValidationTypeEnum",
    "SeverityEnum",
    # Compliance & Violations
    "ComplianceCheck",
    "ComplianceStatusEnum",
    "Violation",
    "ViolationStatusEnum",
    "ViolationSeverityEnum",
    "Evidence",
    "EvidenceSourceTypeEnum",
    # Report & History
    "Report",
    "ReportTypeEnum",
    "ReportFormatEnum",
    "ReportStatusEnum",
    "InspectionHistory",
]
