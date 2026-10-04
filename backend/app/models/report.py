import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.user import User


class ReportTypeEnum(str, Enum):
    INSPECTION_SUMMARY = "INSPECTION_SUMMARY"
    OFFICIAL_ADVISORY_DOSSIER = "OFFICIAL_ADVISORY_DOSSIER"
    LEGAL_NOTICE_DRAFT = "LEGAL_NOTICE_DRAFT"


class ReportFormatEnum(str, Enum):
    PDF = "PDF"
    JSON = "JSON"
    CSV = "CSV"


class ReportStatusEnum(str, Enum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class Report(Base):
    __tablename__ = "reports"

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
    report_type: Mapped[ReportTypeEnum] = mapped_column(
        String(50),
        default=ReportTypeEnum.INSPECTION_SUMMARY,
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    format: Mapped[ReportFormatEnum] = mapped_column(
        String(20),
        default=ReportFormatEnum.PDF,
        nullable=False,
    )
    generated_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    status: Mapped[ReportStatusEnum] = mapped_column(
        String(50),
        default=ReportStatusEnum.READY,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="reports")
    generator: Mapped[Optional["User"]] = relationship("User", back_populates="generated_reports")
