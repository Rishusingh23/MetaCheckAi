import logging
from typing import Dict, Optional, Type

from app.core.config import settings
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.providers.mock_provider import MockOCRProvider
from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.providers.tesseract_provider import TesseractOCRProvider

logger = logging.getLogger(__name__)


class OCRProviderFactory:
    """
    Factory resolving the appropriate OCR Provider based on configuration,
    explicit request, or available system engines.
    """

    _providers: Dict[str, Type[BaseOCRProvider]] = {
        "mock": MockOCRProvider,
        "tesseract": TesseractOCRProvider,
        "paddleocr": PaddleOCRProvider,
    }

    @classmethod
    def get_provider(
        cls,
        engine_name: Optional[str] = None,
        fallback_to_mock: bool = True,
    ) -> BaseOCRProvider:
        # Determine engine from parameter or global settings
        engine = (engine_name or getattr(settings, "OCR_ENGINE", "auto")).lower().strip()

        if engine in cls._providers:
            provider = cls._providers[engine]()
            if provider.is_available() or engine == "mock":
                return provider
            if not fallback_to_mock:
                raise RuntimeError(
                    f"Requested OCR provider '{engine}' is not available in the current environment."
                )
            logger.warning(
                "Requested OCR provider '%s' is unavailable. Falling back to MockOCRProvider.",
                engine,
            )
            return MockOCRProvider()

        if engine == "auto":
            # 1. Try PaddleOCR
            paddle = PaddleOCRProvider()
            if paddle.is_available():
                return paddle

            # 2. Try Tesseract
            tesseract = TesseractOCRProvider()
            if tesseract.is_available():
                return tesseract

            # 3. Development / CI Fallback
            if fallback_to_mock:
                logger.info("No system OCR binary found. Using MockOCRProvider for inspection testing.")
                return MockOCRProvider()

            raise RuntimeError(
                "No OCR engine is available. Please install Tesseract (`brew install tesseract`) or PaddleOCR."
            )

        # Unknown engine name
        if fallback_to_mock:
            logger.warning("Unknown OCR engine '%s'. Defaulting to MockOCRProvider.", engine)
            return MockOCRProvider()

        raise ValueError(f"Unknown OCR engine: '{engine}'. Supported engines: mock, tesseract, paddleocr, auto.")
