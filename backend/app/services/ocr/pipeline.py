import io
import logging
import time
from typing import Any, Dict, Optional, Tuple
from PIL import Image

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.models import ImageQualityMetrics, OCRResultData
from app.services.ocr.preprocessing import preprocess_image
from app.services.ocr.providers.factory import OCRProviderFactory
from app.services.ocr.quality import assess_image_quality, validate_image_file

logger = logging.getLogger(__name__)


class OCRPipeline:
    """
    Complete OCR & Computer Vision Orchestration Pipeline:
    1. File structural validation & MIME verification
    2. Quantitative image quality analysis (sharpness, blur, lighting, contrast, resolution)
    3. Vision preprocessing (orientation, normalization, contrast enhancement, sharpening)
    4. Text extraction with spatial bounding boxes and confidence scoring
    """

    def __init__(
        self,
        provider: Optional[BaseOCRProvider] = None,
        enable_preprocessing: bool = True,
        enable_quality_check: bool = True,
    ):
        self._provider = provider
        self.enable_preprocessing = enable_preprocessing
        self.enable_quality_check = enable_quality_check

    def _resolve_provider(self, engine_name: Optional[str] = None) -> BaseOCRProvider:
        if self._provider is not None and engine_name is None:
            return self._provider
        return OCRProviderFactory.get_provider(engine_name=engine_name)

    async def process_image_bytes(
        self,
        image_bytes: bytes,
        language: str = "en",
        engine_name: Optional[str] = None,
        enable_binarization: bool = False,
    ) -> Tuple[OCRResultData, ImageQualityMetrics, Dict[str, Any]]:
        """
        Execute full end-to-end OCR processing on raw image byte stream.
        """
        start_time = time.perf_counter()

        # Step 1: Validate image byte integrity and format
        validation = validate_image_file(image_bytes)
        if not validation.is_valid:
            raise ValueError(f"Image validation failed: {validation.error_message}")

        # Step 2: Decode into PIL Image
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            # Load in memory
            pil_image.load()
        except Exception as exc:
            raise ValueError(f"Corrupted image payload: unable to decode image stream ({str(exc)})") from exc

        # Step 3: Compute quantitative quality metrics
        quality_metrics = assess_image_quality(pil_image)

        # Step 4: Preprocessing (orientation, grayscale, contrast, sharpening)
        if self.enable_preprocessing:
            processed_image, prep_meta = preprocess_image(
                pil_image,
                enable_contrast=True,
                enable_sharpening=True,
                enable_threshold=enable_binarization,
            )
        else:
            processed_image = pil_image
            prep_meta = {"steps_applied": ["none_raw_passed"]}

        # Step 5: Text & Bounding Box extraction via active OCR Provider
        provider = self._resolve_provider(engine_name=engine_name)
        ocr_result = await provider.extract_text(
            image=processed_image,
            language=language,
        )

        total_elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = {
            "total_pipeline_time_ms": round(total_elapsed_ms, 2),
            "preprocessing": prep_meta,
            "validation": validation.to_dict(),
            "provider_used": provider.name,
            "engine_version": provider.version,
        }

        return ocr_result, quality_metrics, metadata
