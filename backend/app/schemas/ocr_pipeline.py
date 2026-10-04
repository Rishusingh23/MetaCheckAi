from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BoundingBoxSchema(BaseModel):
    x1: int = Field(..., description="Top-left X coordinate")
    y1: int = Field(..., description="Top-left Y coordinate")
    x2: int = Field(..., description="Bottom-right X coordinate")
    y2: int = Field(..., description="Bottom-right Y coordinate")


class OCRRegionSchema(BaseModel):
    text: str = Field(..., description="Recognized text string")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    bbox: BoundingBoxSchema = Field(..., description="Axis-aligned spatial bounding box")
    polygon: Optional[List[List[int]]] = Field(
        default=None, description="Detailed 4-point polygon coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]"
    )
    angle: float = Field(default=0.0, description="Orientation rotation angle in degrees")
    field_hint: Optional[str] = Field(default=None, description="Potential field category hint")


class ImageQualitySchema(BaseModel):
    sharpness_score: float = Field(..., description="Laplacian variance edge sharpness indicator")
    is_blurry: bool = Field(..., description="True if sharpness is below threshold")
    brightness_mean: float = Field(..., description="Average pixel luminance from 0 to 255")
    is_too_dark: bool = Field(..., description="True if underexposed")
    is_too_bright: bool = Field(..., description="True if overexposed or washed out")
    contrast_score: float = Field(..., description="Standard deviation of luminance")
    is_low_contrast: bool = Field(..., description="True if low dynamic range detected")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    is_low_resolution: bool = Field(..., description="True if below recommended resolution")
    quality_score: float = Field(..., description="Composite quality rating from 0 to 100")
    warnings: List[str] = Field(default_factory=list, description="Advisory quality warnings")


class OCRProcessRequest(BaseModel):
    engine_name: Optional[str] = Field(
        default=None, description="Optional engine override ('mock', 'tesseract', 'paddleocr', 'auto')"
    )
    language: str = Field(default="en", description="Target language code (e.g. 'en', 'hi')")


class OCRProcessResponse(BaseModel):
    scan_id: str
    status: str
    full_text: str
    confidence_score: float
    ocr_engine: str
    engine_version: str
    language: str
    processing_time_ms: float
    regions: List[OCRRegionSchema]
    quality_metrics: ImageQualitySchema
    disclaimer: str = (
        "OCR output is extracted text and spatial bounding coordinates. "
        "It does not constitute a legal compliance determination."
    )


class ScanUploadAndProcessResponse(BaseModel):
    scan_id: str
    inspection_id: str
    image_id: str
    image_url: str
    ocr_result: OCRProcessResponse
    disclaimer: str = (
        "OCR output is extracted text and spatial bounding coordinates. "
        "It does not constitute a legal compliance determination."
    )
