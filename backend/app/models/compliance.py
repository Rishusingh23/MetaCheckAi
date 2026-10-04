import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.rule import RuleVersion, SeverityEnum
    from app.models.violation import Violation


class ComplianceStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

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
    rule_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rule_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ComplianceStatusEnum] = mapped_column(
        String(50),
        default=ComplianceStatusEnum.REVIEW,
        nullable=False,
        index=True,
    )
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_requirement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="compliance_checks")
    rule_version: Mapped["RuleVersion"] = relationship("RuleVersion", back_populates="compliance_checks")
    violations: Mapped[List["Violation"]] = relationship(
        "Violation",
        back_populates="compliance_check",
    )
