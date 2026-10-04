from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr import OCRResult
from app.models.product import ProductImage
from app.models.scan import Scan, ScanStatusEnum
from app.services.ocr.models import ImageQualityMetrics, OCRResultData
from app.services.ocr.pipeline import OCRPipeline
from app.services.storage.base import BaseStorageProvider
from app.services.storage.local import LocalStorageProvider

logger = logging.getLogger(__name__)


class ScanProcessorService:
    """
    Coordinates asynchronous/synchronous scan processing lifecycle:
    Scan -> ProductImage -> OCR Pipeline -> OCRResult DB persistence.
    """

    def __init__(
        self,
        storage_provider: Optional[BaseStorageProvider] = None,
        ocr_pipeline: Optional[OCRPipeline] = None,
    ):
        self.storage = storage_provider or LocalStorageProvider()
        self.ocr_pipeline = ocr_pipeline or OCRPipeline()

    async def process_scan(
        self,
        db: AsyncSession,
        scan_id: str,
        engine_name: Optional[str] = None,
        language: str = "en",
    ) -> Tuple[Scan, OCRResult, ImageQualityMetrics]:
        """
        Execute complete OCR extraction for an existing Scan record.
        """
        # Fetch Scan
        scan_res = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = scan_res.scalar_one_or_none()
        if not scan:
            raise ValueError(f"Scan with ID '{scan_id}' not found.")

        # Resolve storage path from associated ProductImage or direct scan.image_path
        product_image = None
        storage_path = scan.image_path

        if scan.product_image_id:
            img_res = await db.execute(
                select(ProductImage).where(ProductImage.id == scan.product_image_id)
            )
            product_image = img_res.scalar_one_or_none()
            if product_image and product_image.image_url_or_path:
                storage_path = product_image.image_url_or_path

        if not storage_path:
            raise ValueError(f"No valid image path found for Scan ID '{scan_id}'.")

        # Update Scan to PROCESSING state
        scan.processing_status = ScanStatusEnum.PROCESSING
        scan.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(scan)

        try:
            # Read image data from storage provider
            image_bytes = await self.storage.read_file(storage_path)

            # Run OCR & Computer Vision Pipeline
            ocr_data, quality_metrics, pipeline_meta = (
                await self.ocr_pipeline.process_image_bytes(
                    image_bytes=image_bytes,
                    language=language,
                    engine_name=engine_name,
                )
            )

            # Check if OCRResult already exists for this scan (idempotent updates)
            ocr_res_query = await db.execute(
                select(OCRResult).where(OCRResult.scan_id == scan.id)
            )
            existing_ocr_result = ocr_res_query.scalar_one_or_none()

            bounding_boxes_payload = {
                "regions": [r.to_dict() for r in ocr_data.regions],
            }
            processing_metadata_payload = {
                "quality_metrics": quality_metrics.to_dict(),
                "preprocessing": pipeline_meta.get("preprocessing", {}),
                "validation": pipeline_meta.get("validation", {}),
                "processing_time_ms": ocr_data.processing_time_ms,
                "language": ocr_data.language,
                "engine_version": ocr_data.engine_version,
            }

            engine_full_name = f"{ocr_data.engine_name} {ocr_data.engine_version}".strip()

            if existing_ocr_result:
                existing_ocr_result.extracted_text = ocr_data.full_text
                existing_ocr_result.confidence = ocr_data.confidence_score
                existing_ocr_result.bounding_boxes = bounding_boxes_payload
                existing_ocr_result.ocr_engine = engine_full_name
                existing_ocr_result.processing_metadata = processing_metadata_payload
                ocr_result_record = existing_ocr_result
            else:
                ocr_result_record = OCRResult(
                    scan_id=scan.id,
                    extracted_text=ocr_data.full_text,
                    confidence=ocr_data.confidence_score,
                    bounding_boxes=bounding_boxes_payload,
                    ocr_engine=engine_full_name,
                    processing_metadata=processing_metadata_payload,
                )
                db.add(ocr_result_record)

            # Update ProductImage metadata with dimensions and quality
            if product_image:
                existing_meta = dict(product_image.file_metadata or {})
                existing_meta["quality_metrics"] = quality_metrics.to_dict()
                existing_meta["width"] = quality_metrics.width
                existing_meta["height"] = quality_metrics.height
                product_image.file_metadata = existing_meta

            # Update Scan state to COMPLETED
            scan.processing_status = ScanStatusEnum.COMPLETED
            scan.completed_at = datetime.utcnow()
            scan.error_message = None

            await db.commit()
            await db.refresh(scan)
            await db.refresh(ocr_result_record)

            return scan, ocr_result_record, quality_metrics

        except Exception as exc:
            logger.error("Scan OCR processing failed for Scan ID %s: %s", scan.id, exc, exc_info=True)
            scan.processing_status = ScanStatusEnum.FAILED
            scan.error_message = str(exc)
            scan.completed_at = datetime.utcnow()
            await db.commit()
            raise
