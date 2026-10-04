import pytest
from PIL import Image

from app.services.ocr.providers.factory import OCRProviderFactory
from app.services.ocr.providers.mock_provider import MockOCRProvider
from app.services.ocr.providers.paddleocr_provider import PaddleOCRProvider
from app.services.ocr.providers.tesseract_provider import TesseractOCRProvider


@pytest.mark.asyncio
async def test_mock_ocr_provider():
    provider = MockOCRProvider()
    assert provider.name == "mock"
    assert provider.is_available() is True

    img = Image.new("RGB", (600, 800), (255, 255, 255))
    result = await provider.extract_text(img)

    assert result.confidence_score > 0.8
    assert len(result.regions) > 0
    assert "NET QUANTITY" in result.full_text
    assert "MRP" in result.full_text

    # Check bounding boxes
    first_region = result.regions[0]
    assert first_region.bbox.x2 > first_region.bbox.x1
    assert first_region.bbox.y2 > first_region.bbox.y1
    assert first_region.confidence > 0.8


def test_ocr_provider_factory_mock():
    prov = OCRProviderFactory.get_provider("mock")
    assert isinstance(prov, MockOCRProvider)


def test_ocr_provider_factory_auto_fallback():
    prov = OCRProviderFactory.get_provider("auto", fallback_to_mock=True)
    assert prov is not None
    assert prov.is_available() is True


def test_ocr_provider_factory_unknown_engine():
    prov = OCRProviderFactory.get_provider("unknown_engine", fallback_to_mock=True)
    assert isinstance(prov, MockOCRProvider)

    with pytest.raises(ValueError):
        OCRProviderFactory.get_provider("unknown_engine", fallback_to_mock=False)


def test_tesseract_provider_availability():
    provider = TesseractOCRProvider()
    # Should safely return boolean without crashing
    avail = provider.is_available()
    assert isinstance(avail, bool)


def test_paddleocr_provider_availability():
    provider = PaddleOCRProvider()
    avail = provider.is_available()
    assert isinstance(avail, bool)
