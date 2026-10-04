import asyncio
import logging
import shutil
import time
from typing import List, Optional
from PIL import Image

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import BoundingBox, OCRRegion, OCRResultData

logger = logging.getLogger(__name__)


class TesseractOCRProvider(BaseOCRProvider):
    """
    OCR provider integrating Google's Tesseract engine via pytesseract.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self._tesseract_cmd = tesseract_cmd
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def version(self) -> str:
        try:
            import pytesseract
            return str(pytesseract.get_tesseract_version())
        except Exception:
            return "unknown"

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import pytesseract
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
            # Check if binary is in PATH
            cmd = shutil.which(pytesseract.pytesseract.tesseract_cmd)
            self._available = cmd is not None
        except Exception:
            self._available = False
        return self._available

    async def extract_text(
        self,
        image: Image.Image,
        language: str = "eng",
    ) -> OCRResultData:
        import pytesseract
        from pytesseract import Output

        if not self.is_available():
            raise RuntimeError(
                "Tesseract binary is not installed or not found in system PATH. "
                "Install tesseract (e.g. `brew install tesseract` or `apt-get install tesseract-ocr`)."
            )

        start_time = time.perf_counter()

        # Run pytesseract in a worker thread to avoid blocking the asyncio loop
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            None,
            lambda: pytesseract.image_to_data(
                image,
                lang=language,
                output_type=Output.DICT,
            ),
        )

        n_boxes = len(data["text"])
        regions: List[OCRRegion] = []
        full_text_lines: List[str] = []
        current_line_tokens: List[str] = []
        current_line_num = -1

        for i in range(n_boxes):
            raw_text = data["text"][i].strip()
            conf_val = float(data["conf"][i])
            line_num = data["line_num"][i]

            # Tesseract gives conf = -1 for structure/empty blocks
            if not raw_text or conf_val < 0:
                continue

            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]

            scaled_conf = max(0.0, min(1.0, conf_val / 100.0))
            bbox = BoundingBox(x1=x, y1=y, x2=x + w, y2=y + h)
            polygon = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

            regions.append(
                OCRRegion(
                    text=raw_text,
                    confidence=scaled_conf,
                    bbox=bbox,
                    polygon=polygon,
                )
            )

            if line_num != current_line_num:
                if current_line_tokens:
                    full_text_lines.append(" ".join(current_line_tokens))
                    current_line_tokens = []
                current_line_num = line_num

            current_line_tokens.append(raw_text)

        if current_line_tokens:
            full_text_lines.append(" ".join(current_line_tokens))

        full_text = "\n".join(full_text_lines)
        avg_conf = (
            sum(r.confidence for r in regions) / len(regions) if regions else 0.0
        )
        proc_time = (time.perf_counter() - start_time) * 1000.0

        return OCRResultData(
            full_text=full_text,
            confidence_score=avg_conf,
            regions=regions,
            raw_payload={"token_count": len(regions), "engine": "tesseract"},
            engine_name=self.name,
            engine_version=self.version,
            language=language,
            processing_time_ms=proc_time,
        )
