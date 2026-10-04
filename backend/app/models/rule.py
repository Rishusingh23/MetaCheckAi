import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.compliance import ComplianceCheck


class ValidationTypeEnum(str, Enum):
    PRESENCE_CHECK = "PRESENCE_CHECK"
    FORMAT_CHECK = "FORMAT_CHECK"
    NUMERIC_RANGE = "NUMERIC_RANGE"
    FONT_HEIGHT_RATIO = "FONT_HEIGHT_RATIO"
    TEXT_PATTERN = "TEXT_PATTERN"


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    ADVISORY = "ADVISORY"


class RuleVerificationStatusEnum(str, Enum):
    VERIFIED_OFFICIAL = "VERIFIED_OFFICIAL"
    NEEDS_LEGAL_REVIEW = "NEEDS_LEGAL_REVIEW"
    DEPRECATED = "DEPRECATED"


class ApplicableContextEnum(str, Enum):
    PHYSICAL_PACKAGE = "PHYSICAL_PACKAGE"
    E_COMMERCE_LISTING = "E_COMMERCE_LISTING"
    IMPORTED_PRODUCT = "IMPORTED_PRODUCT"
    DOMESTIC_PRODUCT = "DOMESTIC_PRODUCT"


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    rule_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legal_reference: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Authoritative statutory source reference, e.g. PCR 2011 Rule 6(1)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
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
    versions: Mapped[List["RuleVersion"]] = relationship(
        "RuleVersion",
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    rule_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    applicable_product_categories: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    applicable_contexts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Contexts where rule applies: PHYSICAL_PACKAGE, E_COMMERCE_LISTING, IMPORTED_PRODUCT, DOMESTIC_PRODUCT",
    )
    validation_type: Mapped[ValidationTypeEnum] = mapped_column(
        String(50),
        default=ValidationTypeEnum.PRESENCE_CHECK,
        nullable=False,
    )
    severity: Mapped[SeverityEnum] = mapped_column(
        String(50),
        default=SeverityEnum.MAJOR,
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50),
        default=RuleVerificationStatusEnum.VERIFIED_OFFICIAL,
        nullable=False,
    )
    evidence_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    source_document: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Official Department of Consumer Affairs statutory source publication",
    )
    source_gazette_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    active_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    rule: Mapped["Rule"] = relationship("Rule", back_populates="versions")
    compliance_checks: Mapped[List["ComplianceCheck"]] = relationship(
        "ComplianceCheck",
        back_populates="rule_version",
    )
