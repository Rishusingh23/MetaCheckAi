import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.scan import Scan


class DeclarationTypeEnum(str, Enum):
    PRODUCT_NAME = "PRODUCT_NAME"
    NET_QUANTITY = "NET_QUANTITY"
    MRP = "MRP"
    UNIT_SALE_PRICE = "UNIT_SALE_PRICE"
    DATE_OF_MANUFACTURE = "DATE_OF_MANUFACTURE"
    DATE_OF_PACKING = "DATE_OF_PACKING"
    MANUFACTURER_DETAILS = "MANUFACTURER_DETAILS"
    PACKER_DETAILS = "PACKER_DETAILS"
    IMPORTER_DETAILS = "IMPORTER_DETAILS"
    COUNTRY_OF_ORIGIN = "COUNTRY_OF_ORIGIN"
    CONSUMER_CARE = "CONSUMER_CARE"
    GENERIC_NAME = "GENERIC_NAME"
    OTHER = "OTHER"


class ExtractionStatusEnum(str, Enum):
    DETECTED = "DETECTED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"
    UNVERIFIED = "UNVERIFIED"


class Declaration(Base):
    __tablename__ = "declarations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    scan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    declaration_type: Mapped[DeclarationTypeEnum] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    extraction_status: Mapped[ExtractionStatusEnum] = mapped_column(
        String(50),
        default=ExtractionStatusEnum.DETECTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="declarations")
