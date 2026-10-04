import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.compliance import ComplianceCheck
    from app.models.evidence import Evidence
    from app.models.user import User


class ViolationStatusEnum(str, Enum):
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"
    OFFICER_CONFIRMED = "OFFICER_CONFIRMED"
    DISMISSED = "DISMISSED"
    NOTICE_ISSUED = "NOTICE_ISSUED"


class ViolationSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    inspection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    compliance_check_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("compliance_checks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    violation_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[ViolationSeverityEnum] = mapped_column(
        String(50),
        default=ViolationSeverityEnum.MAJOR,
        nullable=False,
    )
    status: Mapped[ViolationStatusEnum] = mapped_column(
        String(50),
        default=ViolationStatusEnum.FLAGGED_FOR_REVIEW,
        nullable=False,
        index=True,
    )
    officer_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="violations")
    compliance_check: Mapped[Optional["ComplianceCheck"]] = relationship("ComplianceCheck", back_populates="violations")
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="violation",
        cascade="all, delete-orphan",
    )
