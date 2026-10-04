import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.scan import Scan
    from app.models.compliance import ComplianceCheck
    from app.models.violation import Violation
    from app.models.evidence import Evidence
    from app.models.report import Report
    from app.models.history import InspectionHistory


class InspectionStatusEnum(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    OFFICER_REVIEWED = "OFFICER_REVIEWED"
    FAILED = "FAILED"


class InspectionSourceEnum(str, Enum):
    MOBILE_CAMERA = "MOBILE_CAMERA"
    FIELD_SCANNER = "FIELD_SCANNER"
    PORTAL_UPLOAD = "PORTAL_UPLOAD"
    API_INGESTION = "API_INGESTION"


class OverallResultEnum(str, Enum):
    COMPLIANT = "COMPLIANT"
    POTENTIAL_NON_COMPLIANCE = "POTENTIAL_NON_COMPLIANCE"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    product_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inspector_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[InspectionStatusEnum] = mapped_column(
        String(50),
        default=InspectionStatusEnum.CREATED,
        nullable=False,
        index=True,
    )
    source_type: Mapped[InspectionSourceEnum] = mapped_column(
        String(50),
        default=InspectionSourceEnum.PORTAL_UPLOAD,
        nullable=False,
    )
    overall_result_placeholder: Mapped[OverallResultEnum] = mapped_column(
        String(50),
        default=OverallResultEnum.PENDING_VERIFICATION,
        nullable=False,
        index=True,
    )
    inspection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="inspections")
    inspector: Mapped[Optional["User"]] = relationship("User", back_populates="inspections")
    scans: Mapped[List["Scan"]] = relationship(
        "Scan",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    compliance_checks: Mapped[List["ComplianceCheck"]] = relationship(
        "ComplianceCheck",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    violations: Mapped[List["Violation"]] = relationship(
        "Violation",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
    history_logs: Mapped[List["InspectionHistory"]] = relationship(
        "InspectionHistory",
        back_populates="inspection",
        cascade="all, delete-orphan",
    )
