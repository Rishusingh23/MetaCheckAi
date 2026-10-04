"""
Demo Inspection Dataset Seeder for MetaCheck AI.
Executes the full real pipeline on the 5 controlled sample packaged product label images:
  Image -> Storage -> Product -> Inspection -> Scan -> OCR -> Declaration Extraction
  -> Normalization -> Rule Version Selection -> Compliance Evaluation -> Violations & Evidence
"""
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.inspection import Inspection, InspectionStatusEnum
from app.models.product import Product, ProductImage, ImageTypeEnum
from app.models.scan import PanelTypeEnum, Scan, ScanStatusEnum
from app.models.user import User
from app.services.demo.label_generator import (
    generate_blurry_review_label,
    generate_compliant_label,
    generate_missing_manufacturer_label,
    generate_non_compliant_mrp_label,
    generate_non_metric_quantity_label,
)
from app.services.declarations.extractor import DeclarationExtractorService
from app.services.ocr.models import BoundingBox, OCRRegion
from app.services.rules.engine import RuleEngineService
from app.services.scan_processor import ScanProcessorService
from app.services.storage.local import LocalStorageProvider


class DemoSeederService:
    """Service to populate controlled demonstration inspections for SIH 2026."""

    def __init__(self):
        self.storage = LocalStorageProvider(base_directory=settings.UPLOAD_DIR)
        self.scan_processor = ScanProcessorService()
        self.declaration_extractor = DeclarationExtractorService()
        self.rule_engine = RuleEngineService()

    async def seed_demo_inspections(
        self,
        db: AsyncSession,
        inspector: User,
    ) -> List[Dict[str, Any]]:
        """
        Runs all 5 sample packages through the real pipeline.
        Returns detailed summary of created inspections.
        """
        inspector_user_id = str(inspector.id)
        generators = [
            ("Sample A: Compliant Potato Wafers", generate_compliant_label),
            ("Sample B: Missing Manufacturer Address", generate_missing_manufacturer_label),
            ("Sample C: Non-Compliant MRP without Tax Clause", generate_non_compliant_mrp_label),
            ("Sample D: Non-Metric Quantity (Lbs/Oz)", generate_non_metric_quantity_label),
            ("Sample E: Blurry / Insufficient Evidence", generate_blurry_review_label),
        ]

        results = []

        for scenario_name, generator_fn in generators:
            image_bytes, meta = generator_fn()
            filename = f"demo_{meta['brand'].lower().replace(' ', '_')}.png"

            # 1. Save Image to storage
            storage_res = await self.storage.save_file(
                file_bytes=image_bytes,
                filename=filename,
                content_type="image/png" if filename.endswith(".png") else "image/jpeg",
            )
            stored_path = storage_res["storage_path"]

            # 2. Find or Create Product
            prod_query = select(Product).where(Product.barcode_gtin == meta["barcode"])
            prod_res = await db.execute(prod_query)
            product = prod_res.scalar_one_or_none()
            if not product:
                product = Product(
                    name=meta["name"],
                    brand=meta["brand"],
                    category=meta["category"],
                    barcode_gtin=meta["barcode"],
                    description=f"[DEMO / SIMULATION] Sample for Legal Metrology demonstration: {scenario_name}",
                )
                db.add(product)
                await db.flush()

            # 3. Create Product Image
            prod_img = ProductImage(
                product_id=product.id,
                image_url_or_path=stored_path,
                image_type=ImageTypeEnum.FRONT_PDP.value,
            )
            db.add(prod_img)
            await db.flush()

            # 4. Create Inspection
            inspection = Inspection(
                product_id=product.id,
                inspector_id=inspector_user_id,
                status=InspectionStatusEnum.CREATED,
                notes=f"[DEMO / SIMULATION] Scenario: {scenario_name}",
            )
            db.add(inspection)
            await db.flush()

            # 5. Create Scan
            scan = Scan(
                inspection_id=inspection.id,
                product_image_id=prod_img.id,
                image_path=stored_path,
                panel_type=PanelTypeEnum.FRONT_PDP,
                processing_status=ScanStatusEnum.PENDING,
            )
            db.add(scan)
            await db.flush()

            # 6. Process Scan (OCR & image quality metrics)
            scan, ocr_result, quality = await self.scan_processor.process_scan(
                scan_id=scan.id,
                db=db,
                engine_name="mock",
            )

            # 6b. Extract & Normalize Legal Metrology Declarations
            raw_regions = (ocr_result.bounding_boxes or {}).get("regions", []) if ocr_result else []
            ocr_regions = []
            for r in raw_regions:
                bbox_data = r.get("bbox", {})
                bbox = BoundingBox(
                    x1=bbox_data.get("x1", 0),
                    y1=bbox_data.get("y1", 0),
                    x2=bbox_data.get("x2", 0),
                    y2=bbox_data.get("y2", 0),
                )
                ocr_regions.append(
                    OCRRegion(
                        text=r.get("text", ""),
                        confidence=float(r.get("confidence", 0.0)),
                        bbox=bbox,
                        polygon=r.get("polygon"),
                        angle=float(r.get("angle", 0.0)),
                        field_hint=r.get("field_hint"),
                    )
                )

            candidates = await self.declaration_extractor.extract_declarations(
                full_text=ocr_result.extracted_text if ocr_result else "",
                regions=ocr_regions,
            )
            await self.declaration_extractor.persist_declarations_for_scan(
                db=db,
                scan_id=scan.id,
                candidates=candidates,
            )

            # 7. Evaluate Statutory Rules & Flag Potential Violations
            compliance_eval = await self.rule_engine.evaluate_inspection(
                inspection_id=inspection.id,
                db=db,
                user_id=inspector_user_id,
            )

            await db.commit()

            results.append({
                "scenario": scenario_name,
                "product_id": product.id,
                "product_name": product.name,
                "inspection_id": inspection.id,
                "overall_status": compliance_eval.get("overall_status"),
                "pass_count": compliance_eval.get("pass_count"),
                "fail_count": compliance_eval.get("fail_count"),
                "review_count": compliance_eval.get("review_count"),
                "violations_flagged": compliance_eval.get("violations_flagged"),
                "screening_score": compliance_eval.get("screening_score"),
                "expected_result": meta.get("expected_result"),
            })

            logger.info(f"Demo seeded: {scenario_name} -> {compliance_eval.get('overall_status')}")

        return results


demo_seeder_service = DemoSeederService()
