import io
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inspection import Inspection, InspectionStatusEnum
from app.models.ocr import OCRResult
from app.models.product import ImageTypeEnum, Product, ProductImage
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.services.ocr.pipeline import OCRPipeline
from app.services.ocr.providers.mock_provider import MockOCRProvider
from app.services.scan_processor import ScanProcessorService
from app.services.storage.local import LocalStorageProvider


def create_test_image_bytes(width: int = 500, height: int = 500) -> bytes:
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_scan_processor_success(db_session: AsyncSession, tmp_path):
    storage = LocalStorageProvider(base_directory=str(tmp_path / "storage"))
    mock_pipeline = OCRPipeline(provider=MockOCRProvider())
    processor = ScanProcessorService(storage_provider=storage, ocr_pipeline=mock_pipeline)

    # 1. Create Product
    product = Product(name="Test Biscuit Pack", brand="Apex", category="Food")
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # 2. Create Inspection
    inspection = Inspection(product_id=product.id, status=InspectionStatusEnum.CREATED)
    db_session.add(inspection)
    await db_session.commit()
    await db_session.refresh(inspection)

    # 3. Save test image in storage
    img_bytes = create_test_image_bytes(600, 400)
    save_info = await storage.save_file(img_bytes, "biscuit_label.png")

    # 4. Create ProductImage
    prod_image = ProductImage(
        product_id=product.id,
        image_url_or_path=save_info["storage_path"],
        image_type=ImageTypeEnum.FRONT_PDP,
        file_metadata={
            "url": save_info["url"],
            "filename": save_info["filename"],
            "file_size_bytes": save_info["file_size_bytes"],
        },
    )
    db_session.add(prod_image)
    await db_session.commit()
    await db_session.refresh(prod_image)

    # 5. Create Scan
    scan = Scan(
        inspection_id=inspection.id,
        product_image_id=prod_image.id,
        image_path=save_info["storage_path"],
        panel_type=PanelTypeEnum.FRONT_PDP,
        processing_status=ScanStatusEnum.PENDING,
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    # 6. Execute Scan Processor
    proc_scan, ocr_res, quality = await processor.process_scan(
        db=db_session,
        scan_id=scan.id,
        engine_name="mock",
    )

    assert proc_scan.processing_status == ScanStatusEnum.COMPLETED
    assert proc_scan.completed_at is not None
    assert proc_scan.error_message is None
    assert ocr_res.confidence > 0.8
    assert "NET QUANTITY" in ocr_res.extracted_text
    assert len(ocr_res.bounding_boxes["regions"]) > 0

    # Query DB directly to verify persistence
    db_ocr = await db_session.execute(select(OCRResult).where(OCRResult.scan_id == scan.id))
    persisted_ocr = db_ocr.scalar_one_or_none()
    assert persisted_ocr is not None
    assert persisted_ocr.extracted_text == ocr_res.extracted_text
    assert persisted_ocr.confidence == ocr_res.confidence


@pytest.mark.asyncio
async def test_scan_processor_corrupted_file_failure(db_session: AsyncSession, tmp_path):
    storage = LocalStorageProvider(base_directory=str(tmp_path / "storage"))
    mock_pipeline = OCRPipeline(provider=MockOCRProvider())
    processor = ScanProcessorService(storage_provider=storage, ocr_pipeline=mock_pipeline)

    product = Product(name="Bad Product", brand="Bad Brand", category="Food")
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    inspection = Inspection(product_id=product.id, status=InspectionStatusEnum.CREATED)
    db_session.add(inspection)
    await db_session.commit()
    await db_session.refresh(inspection)

    # Save invalid text file as image
    save_info = await storage.save_file(b"NOT_A_VALID_IMAGE", "bad.jpg")

    prod_image = ProductImage(
        product_id=product.id,
        image_url_or_path=save_info["storage_path"],
        image_type=ImageTypeEnum.FRONT_PDP,
        file_metadata={"filename": save_info["filename"]},
    )
    db_session.add(prod_image)
    await db_session.commit()
    await db_session.refresh(prod_image)

    scan = Scan(
        inspection_id=inspection.id,
        product_image_id=prod_image.id,
        image_path=save_info["storage_path"],
        panel_type=PanelTypeEnum.FRONT_PDP,
        processing_status=ScanStatusEnum.PENDING,
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    with pytest.raises(ValueError):
        await processor.process_scan(db=db_session, scan_id=scan.id)

    # Verify Scan status transitioned to FAILED
    await db_session.refresh(scan)
    assert scan.processing_status == ScanStatusEnum.FAILED
    assert scan.error_message is not None
