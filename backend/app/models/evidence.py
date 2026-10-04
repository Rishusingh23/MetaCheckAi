import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.violation import Violation


class EvidenceSourceTypeEnum(str, Enum):
    LABEL_IMAGE_CROP = "LABEL_IMAGE_CROP"
    OCR_TEXT_SNIPPET = "OCR_TEXT_SNIPPET"
    CALCULATION_LOG = "CALCULATION_LOG"
    OTHER = "OTHER"


class Evidence(Base):
    __tablename__ = "evidences"

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
    violation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("violations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[EvidenceSourceTypeEnum] = mapped_column(
        String(50),
        default=EvidenceSourceTypeEnum.LABEL_IMAGE_CROP,
        nullable=False,
    )
    image_url_or_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="evidences")
    violation: Mapped[Optional["Violation"]] = relationship("Violation", back_populates="evidences")
