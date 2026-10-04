from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.product import ImageTypeEnum


class ProductImageBase(BaseModel):
    image_url_or_path: str = Field(description="File system path or URL reference to label image")
    image_type: ImageTypeEnum = Field(default=ImageTypeEnum.FRONT_PDP, description="Package display panel")
    file_metadata: Optional[dict] = Field(default=None, description="Image dimensions, format, resolution")


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageRead(ProductImageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    created_at: datetime


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Commodity or product title")
    brand: str = Field(min_length=1, max_length=255, description="Brand name")
    category: str = Field(min_length=1, max_length=100, description="Product category (e.g. Edible Oils, Food, Electronics)")
    manufacturer: Optional[str] = Field(default=None, max_length=255)
    packer: Optional[str] = Field(default=None, max_length=255)
    importer: Optional[str] = Field(default=None, max_length=255)
    barcode_gtin: Optional[str] = Field(default=None, max_length=50, description="GTIN barcode (EAN-13, UPC)")
    country_of_origin: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    brand: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    manufacturer: Optional[str] = None
    packer: Optional[str] = None
    importer: Optional[str] = None
    barcode_gtin: Optional[str] = None
    country_of_origin: Optional[str] = None
    description: Optional[str] = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ProductDetailRead(ProductRead):
    images: List[ProductImageRead] = []


class ProductRepositoryItem(ProductRead):
    """Enriched product item for enforcement repository view."""
    inspection_count: int = 0
    latest_inspection_id: Optional[str] = None
    latest_inspection_status: Optional[str] = None
    latest_compliance_result: Optional[str] = None
    last_inspected_at: Optional[datetime] = None


class ProductDossierInspectionItem(BaseModel):
    id: str
    inspection_date: datetime
    status: str
    overall_result: Optional[str] = None
    inspector_name: Optional[str] = None
    violations_count: int = 0


class ProductDossierViolationItem(BaseModel):
    id: str
    inspection_id: str
    violation_code: str
    description: Optional[str] = None
    severity: str
    status: str
    created_at: datetime


class ProductDossierReportItem(BaseModel):
    id: str
    inspection_id: str
    report_type: str
    format: str
    generated_at: datetime


class ProductDossierRead(BaseModel):
    """Complete Legal Metrology compliance dossier for a packaged commodity."""
    product: ProductDetailRead
    inspections: List[ProductDossierInspectionItem] = []
    latest_inspection: Optional[Dict[str, Any]] = None
    violations: List[ProductDossierViolationItem] = []
    reports: List[ProductDossierReportItem] = []
    audit_history: List[Dict[str, Any]] = []
