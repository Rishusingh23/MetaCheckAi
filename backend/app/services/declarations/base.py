from abc import ABC, abstractmethod
from typing import List
from app.services.declarations.models import DeclarationCandidate
from app.services.ocr.models import OCRRegion


class BaseDeclarationExtractor(ABC):
    """
    Abstract interface for Declaration Extractors.
    Allows pluggable rule-based or deep learning KIE models.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Extractor identifier name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Extractor version."""
        pass

    @abstractmethod
    async def extract_declarations(
        self,
        full_text: str,
        regions: List[OCRRegion],
    ) -> List[DeclarationCandidate]:
        """
        Extract structured Legal Metrology declarations from OCR text and bounding regions.
        """
        pass
