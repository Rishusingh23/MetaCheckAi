import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.scan import Scan


class ImageTypeEnum(str, Enum):
    FRONT_PDP = "FRONT_PDP"
    BACK_DECLARATION = "BACK_DECLARATION"
    SIDE_PANEL = "SIDE_PANEL"
    BOTTOM_BASE = "BOTTOM_BASE"
    OTHER = "OTHER"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    packer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    importer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    barcode_gtin: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    country_of_origin: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    images: Mapped[List["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    inspections: Mapped[List["Inspection"]] = relationship(
        "Inspection",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

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
    image_url_or_path: Mapped[str] = mapped_column(String(500), nullable=False)
    image_type: Mapped[ImageTypeEnum] = mapped_column(
        String(50),
        default=ImageTypeEnum.FRONT_PDP,
        nullable=False,
    )
    file_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="images")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="product_image")
