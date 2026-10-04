from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image

from app.services.ocr.models import OCRResultData


class BaseOCRProvider(ABC):
    """Abstract base interface for OCR extraction providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the OCR provider engine."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the OCR engine."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider dependencies and system binaries are present."""
        pass

    @abstractmethod
    async def extract_text(
        self,
        image: Image.Image,
        language: str = "en",
    ) -> OCRResultData:
        """
        Extract text, spatial bounding boxes, and confidence scores from a PIL Image.
        """
        pass
