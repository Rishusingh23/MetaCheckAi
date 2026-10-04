import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.product import ProductImage
    from app.models.ocr import OCRResult
    from app.models.declaration import Declaration


class ScanStatusEnum(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PanelTypeEnum(str, Enum):
    FRONT_PDP = "FRONT_PDP"
    BACK_DECLARATION = "BACK_DECLARATION"
    SIDE_PANEL = "SIDE_PANEL"
    BOTTOM_BASE = "BOTTOM_BASE"
    OTHER = "OTHER"


class Scan(Base):
    __tablename__ = "scans"

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
    product_image_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("product_images.id", ondelete="SET NULL"),
        nullable=True,
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    panel_type: Mapped[PanelTypeEnum] = mapped_column(
        String(50),
        default=PanelTypeEnum.FRONT_PDP,
        nullable=False,
    )
    processing_status: Mapped[ScanStatusEnum] = mapped_column(
        String(50),
        default=ScanStatusEnum.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="scans")
    product_image: Mapped[Optional["ProductImage"]] = relationship("ProductImage", back_populates="scans")
    ocr_results: Mapped[List["OCRResult"]] = relationship(
        "OCRResult",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
    declarations: Mapped[List["Declaration"]] = relationship(
        "Declaration",
        back_populates="scan",
        cascade="all, delete-orphan",
    )
