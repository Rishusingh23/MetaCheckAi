import asyncio
import logging
import time
from typing import List, Optional
import numpy as np
from PIL import Image

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import BoundingBox, OCRRegion, OCRResultData

logger = logging.getLogger(__name__)


class PaddleOCRProvider(BaseOCRProvider):
    """
    OCR provider integrating PaddleOCR (PP-OCRv4) for state-of-the-art multilingual text detection.
    """

    def __init__(self, use_angle_cls: bool = True, lang: str = "en"):
        self._use_angle_cls = use_angle_cls
        self._lang = lang
        self._engine = None
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "paddleocr"

    @property
    def version(self) -> str:
        try:
            import paddleocr  # type: ignore
            return getattr(paddleocr, "__version__", "2.7.0")
        except Exception:
            return "unknown"

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import paddleocr  # type: ignore
            self._available = True
        except ImportError:
            self._available = False
        except Exception:
            self._available = False
        return self._available

    def _get_engine(self):
        if self._engine is None:
            from paddleocr import PaddleOCR  # type: ignore
            self._engine = PaddleOCR(
                use_angle_cls=self._use_angle_cls,
                lang=self._lang,
                show_log=False,
            )
        return self._engine

    async def extract_text(
        self,
        image: Image.Image,
        language: str = "en",
    ) -> OCRResultData:
        if not self.is_available():
            raise RuntimeError(
                "PaddleOCR is not installed in the current environment. "
                "Install with `pip install paddlepaddle paddleocr`."
            )

        start_time = time.perf_counter()
        img_np = np.array(image.convert("RGB"))

        loop = asyncio.get_running_loop()
        engine = self._get_engine()
        results = await loop.run_in_executor(None, lambda: engine.ocr(img_np, cls=self._use_angle_cls))

        regions: List[OCRRegion] = []
        full_text_lines: List[str] = []

        if results and len(results) > 0 and results[0] is not None:
            for line_res in results[0]:
                poly_coords = line_res[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                text_content, conf = line_res[1]

                # Convert 4-point polygon into axis-aligned bounding box
                xs = [int(p[0]) for p in poly_coords]
                ys = [int(p[1]) for p in poly_coords]
                bbox = BoundingBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))

                polygon = [[int(p[0]), int(p[1])] for p in poly_coords]

                regions.append(
                    OCRRegion(
                        text=str(text_content).strip(),
                        confidence=float(conf),
                        bbox=bbox,
                        polygon=polygon,
                    )
                )
                full_text_lines.append(str(text_content).strip())

        full_text = "\n".join(full_text_lines)
        avg_conf = (
            sum(r.confidence for r in regions) / len(regions) if regions else 0.0
        )
        proc_time = (time.perf_counter() - start_time) * 1000.0

        return OCRResultData(
            full_text=full_text,
            confidence_score=avg_conf,
            regions=regions,
            raw_payload={"line_count": len(regions), "engine": "paddleocr"},
            engine_name=self.name,
            engine_version=self.version,
            language=language,
            processing_time_ms=proc_time,
        )
