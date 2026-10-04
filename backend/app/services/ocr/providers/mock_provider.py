import time
from typing import List, Optional
from PIL import Image

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import BoundingBox, OCRRegion, OCRResultData


class MockOCRProvider(BaseOCRProvider):
    """
    Deterministic Mock OCR Provider for unit testing, CI/CD pipelines,
    and fallback operation when external C++ OCR binaries are not installed.
    """

    def __init__(self, custom_lines: Optional[List[str]] = None, default_confidence: float = 0.95):
        self._custom_lines = custom_lines
        self._default_confidence = default_confidence

    @property
    def name(self) -> str:
        return "mock"

    @property
    def version(self) -> str:
        return "1.0.0"

    def is_available(self) -> bool:
        return True

    async def extract_text(
        self,
        image: Image.Image,
        language: str = "en",
    ) -> OCRResultData:
        start_time = time.perf_counter()
        width, height = image.size

        # Support dynamic label text passed via PNG text metadata chunks
        custom_lines = self._custom_lines
        if not custom_lines and getattr(image, "info", None) and "label_text" in image.info:
            raw_info = image.info["label_text"]
            custom_lines = [l.strip() for l in raw_info.split("\n") if l.strip()]

        lines = custom_lines or [
            "COMMODITY: PREMIUM ORGANIC WHOLE WHEAT ATTA",
            "NET QUANTITY: 5.0 kg",
            "MAXIMUM RETAIL PRICE (MRP): Rs. 295.00 (INCL. OF ALL TAXES)",
            "UNIT SALE PRICE: Rs. 59.00 / kg",
            "MANUFACTURED & PACKED BY: APEX FOODS INDIA PVT LTD",
            "PLOT NO. 42, INDUSTRIAL AREA, PHASE II, NEW DELHI - 110020",
            "DATE OF MANUFACTURE: 02/2026",
            "BEST BEFORE: 6 MONTHS FROM PACKAGING",
            "CUSTOMER CARE: 1800-111-2222 / SUPPORT@APEXFOODS.IN",
            "COUNTRY OF ORIGIN: INDIA",
        ]

        regions: List[OCRRegion] = []
        num_lines = len(lines)
        line_height = max(24, int(height / (num_lines + 4)))
        padding_top = max(20, int(height * 0.05))

        for idx, line in enumerate(lines):
            y1 = padding_top + (idx * (line_height + 8))
            y2 = min(height - 5, y1 + line_height)
            x1 = max(10, int(width * 0.08))
            x2 = min(width - 10, int(width * 0.92))

            # Introduce small realistic confidence variance (0.92 - 0.99)
            conf = min(0.99, max(0.85, self._default_confidence - (idx * 0.005)))

            bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
            polygon = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

            regions.append(
                OCRRegion(
                    text=line,
                    confidence=conf,
                    bbox=bbox,
                    polygon=polygon,
                    angle=0.0,
                )
            )

        full_text = "\n".join(lines)
        avg_conf = sum(r.confidence for r in regions) / max(1, len(regions))
        proc_time = (time.perf_counter() - start_time) * 1000.0

        return OCRResultData(
            full_text=full_text,
            confidence_score=avg_conf,
            regions=regions,
            raw_payload={"line_count": len(regions), "mode": "mock_synthetic"},
            engine_name=self.name,
            engine_version=self.version,
            language=language,
            processing_time_ms=proc_time,
        )
