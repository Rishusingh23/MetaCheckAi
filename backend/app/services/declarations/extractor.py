import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.declaration import (
    Declaration,
    DeclarationTypeEnum,
    ExtractionStatusEnum,
)
from app.models.ocr import OCRResult
from app.models.scan import Scan
from app.services.declarations.base import BaseDeclarationExtractor
from app.services.declarations.confidence import calculate_extraction_confidence
from app.services.declarations.models import (
    DeclarationCandidate,
    NormalizedContact,
    NormalizedDate,
    NormalizedPrice,
    NormalizedQuantity,
    NormalizedUSP,
)
from app.services.declarations.normalizer import (
    clean_entity_text,
    normalize_consumer_care,
    normalize_country,
    normalize_date,
    normalize_mrp,
    normalize_net_quantity,
    normalize_usp,
)
from app.services.declarations.patterns import (
    CONSUMER_CARE_KEYWORDS,
    COUNTRY_KEYWORDS,
    GENERIC_NAME_KEYWORDS,
    IMPORTER_ENTITY_KEYWORDS,
    MFD_KEYWORDS,
    MFG_ENTITY_KEYWORDS,
    MRP_KEYWORDS,
    NET_QTY_KEYWORDS,
    PACKER_ENTITY_KEYWORDS,
    PKD_KEYWORDS,
    REGEX_DATE,
    REGEX_EMAIL,
    REGEX_METRIC_QUANTITY,
    REGEX_MRP_AMOUNT,
    REGEX_PHONE,
    REGEX_PINCODE,
    REGEX_USP,
    USP_KEYWORDS,
)
from app.services.ocr.models import BoundingBox, OCRRegion

logger = logging.getLogger(__name__)


class DeclarationExtractorService(BaseDeclarationExtractor):
    """
    Core Legal Metrology Declaration Extraction Engine:
    Inspects OCR tokens and lines, extracts entities across all 13 declaration types,
    normalizes values, computes transparent confidence, and resolves candidate ambiguity.
    """

    @property
    def name(self) -> str:
        return "pattern_heuristic_extractor"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _matches_any_keyword(self, text: str, keywords: List[str]) -> bool:
        pattern = r"\b(?:" + "|".join(keywords) + r")\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _find_region_for_text(self, target_text: str, regions: List[OCRRegion]) -> Tuple[Optional[BoundingBox], float]:
        """Find the matching OCR region bounding box and token confidence."""
        target_lower = target_text.lower().strip()
        for r in regions:
            r_text_lower = r.text.lower().strip()
            if target_lower in r_text_lower or r_text_lower in target_lower:
                return r.bbox, r.confidence

        # Fallback: token intersection
        best_bbox = None
        best_conf = 0.85
        max_overlap = 0
        target_words = set(re.findall(r"\w+", target_lower))

        for r in regions:
            r_words = set(re.findall(r"\w+", r.text.lower()))
            overlap = len(target_words.intersection(r_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_bbox = r.bbox
                best_conf = r.confidence

        return best_bbox, best_conf

    async def extract_declarations(
        self,
        full_text: str,
        regions: List[OCRRegion],
    ) -> List[DeclarationCandidate]:
        """
        Execute comprehensive extraction across all 13 Legal Metrology declaration types.
        """
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        candidates_by_type: Dict[DeclarationTypeEnum, List[DeclarationCandidate]] = {
            t: [] for t in DeclarationTypeEnum
        }

        # -------------------------------------------------------------
        # 1. Line-by-Line & Token Analysis
        # -------------------------------------------------------------
        for line_idx, line in enumerate(lines):
            line_bbox, line_conf = self._find_region_for_text(line, regions)

            # --- A. MRP Extraction ---
            has_mrp_kw = self._matches_any_keyword(line, MRP_KEYWORDS)
            if has_mrp_kw or ("₹" in line or "rs" in line.lower()) and "usp" not in line.lower() and "unit" not in line.lower():
                mrp_match = REGEX_MRP_AMOUNT.search(line)
                if mrp_match:
                    formatted, norm_price = normalize_mrp(line)
                    if norm_price:
                        conf, rationale = calculate_extraction_confidence(
                            ocr_confidence=line_conf,
                            has_explicit_keyword=has_mrp_kw,
                            has_valid_format=True,
                            has_contextual_indicators=norm_price.is_inclusive_of_all_taxes,
                        )
                        candidates_by_type[DeclarationTypeEnum.MRP].append(
                            DeclarationCandidate(
                                declaration_type=DeclarationTypeEnum.MRP,
                                raw_value=line,
                                normalized_value=formatted,
                                confidence=conf,
                                source_text=line,
                                bounding_box=line_bbox,
                                confidence_rationale=rationale,
                                structured_data=norm_price.to_dict(),
                            )
                        )

            # --- B. Net Quantity Extraction ---
            has_net_kw = self._matches_any_keyword(line, NET_QTY_KEYWORDS)
            qty_match = REGEX_METRIC_QUANTITY.search(line)
            if qty_match and "usp" not in line.lower() and "per" not in line.lower() and "/ " not in line:
                formatted_qty, norm_qty = normalize_net_quantity(line)
                if norm_qty:
                    conf, rationale = calculate_extraction_confidence(
                        ocr_confidence=line_conf,
                        has_explicit_keyword=has_net_kw,
                        has_valid_format=True,
                        has_contextual_indicators=bool(has_net_kw),
                    )
                    candidates_by_type[DeclarationTypeEnum.NET_QUANTITY].append(
                        DeclarationCandidate(
                            declaration_type=DeclarationTypeEnum.NET_QUANTITY,
                            raw_value=line,
                            normalized_value=formatted_qty,
                            confidence=conf,
                            source_text=line,
                            bounding_box=line_bbox,
                            confidence_rationale=rationale,
                            structured_data=norm_qty.to_dict(),
                        )
                    )

            # --- C. Unit Sale Price (USP) Extraction ---
            has_usp_kw = self._matches_any_keyword(line, USP_KEYWORDS)
            usp_match = REGEX_USP.search(line)
            if has_usp_kw or (usp_match and ("per" in line.lower() or "/" in line)):
                formatted_usp, norm_usp = normalize_usp(line)
                if norm_usp:
                    conf, rationale = calculate_extraction_confidence(
                        ocr_confidence=line_conf,
                        has_explicit_keyword=has_usp_kw,
                        has_valid_format=True,
                        has_contextual_indicators=True,
                    )
                    candidates_by_type[DeclarationTypeEnum.UNIT_SALE_PRICE].append(
                        DeclarationCandidate(
                            declaration_type=DeclarationTypeEnum.UNIT_SALE_PRICE,
                            raw_value=line,
                            normalized_value=formatted_usp,
                            confidence=conf,
                            source_text=line,
                            bounding_box=line_bbox,
                            confidence_rationale=rationale,
                            structured_data=norm_usp.to_dict(),
                        )
                    )

            # --- D. Date of Manufacture vs Date of Packing ---
            has_mfd_kw = self._matches_any_keyword(line, MFD_KEYWORDS)
            has_pkd_kw = self._matches_any_keyword(line, PKD_KEYWORDS)
            date_match = REGEX_DATE.search(line)

            if date_match:
                formatted_date, norm_date = normalize_date(line)
                if norm_date:
                    if has_mfd_kw:
                        conf, rationale = calculate_extraction_confidence(
                            ocr_confidence=line_conf,
                            has_explicit_keyword=True,
                            has_valid_format=True,
                            has_contextual_indicators=True,
                        )
                        candidates_by_type[DeclarationTypeEnum.DATE_OF_MANUFACTURE].append(
                            DeclarationCandidate(
                                declaration_type=DeclarationTypeEnum.DATE_OF_MANUFACTURE,
                                raw_value=line,
                                normalized_value=formatted_date,
                                confidence=conf,
                                source_text=line,
                                bounding_box=line_bbox,
                                confidence_rationale=rationale,
                                structured_data=norm_date.to_dict(),
                            )
                        )
                    elif has_pkd_kw or not has_mfd_kw:
                        conf, rationale = calculate_extraction_confidence(
                            ocr_confidence=line_conf,
                            has_explicit_keyword=has_pkd_kw,
                            has_valid_format=True,
                            has_contextual_indicators=False,
                        )
                        target_type = (
                            DeclarationTypeEnum.DATE_OF_PACKING
                            if has_pkd_kw
                            else DeclarationTypeEnum.DATE_OF_MANUFACTURE
                        )
                        candidates_by_type[target_type].append(
                            DeclarationCandidate(
                                declaration_type=target_type,
                                raw_value=line,
                                normalized_value=formatted_date,
                                confidence=conf,
                                source_text=line,
                                bounding_box=line_bbox,
                                confidence_rationale=rationale,
                                structured_data=norm_date.to_dict(),
                            )
                        )

            # --- E. Manufacturer Details ---
            has_mfg_entity_kw = self._matches_any_keyword(line, MFG_ENTITY_KEYWORDS)
            if has_mfg_entity_kw:
                # Group with next line if address continues
                entity_text = line
                if line_idx + 1 < len(lines):
                    next_line = lines[line_idx + 1]
                    if REGEX_PINCODE.search(next_line) or "plot" in next_line.lower() or "area" in next_line.lower():
                        entity_text = f"{line}, {next_line}"

                cleaned_entity = clean_entity_text(entity_text, MFG_ENTITY_KEYWORDS)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=True,
                    has_valid_format=bool(len(cleaned_entity) > 5),
                    has_contextual_indicators=bool(REGEX_PINCODE.search(entity_text)),
                )
                candidates_by_type[DeclarationTypeEnum.MANUFACTURER_DETAILS].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.MANUFACTURER_DETAILS,
                        raw_value=entity_text,
                        normalized_value=cleaned_entity,
                        confidence=conf,
                        source_text=entity_text,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                        structured_data={"raw_entity": entity_text, "clean_entity": cleaned_entity},
                    )
                )

            # --- F. Packer Details ---
            has_packer_kw = self._matches_any_keyword(line, PACKER_ENTITY_KEYWORDS)
            if has_packer_kw and not has_mfg_entity_kw:
                cleaned_packer = clean_entity_text(line, PACKER_ENTITY_KEYWORDS)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=True,
                    has_valid_format=bool(len(cleaned_packer) > 4),
                    has_contextual_indicators=bool(REGEX_PINCODE.search(line)),
                )
                candidates_by_type[DeclarationTypeEnum.PACKER_DETAILS].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.PACKER_DETAILS,
                        raw_value=line,
                        normalized_value=cleaned_packer,
                        confidence=conf,
                        source_text=line,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                    )
                )

            # --- G. Importer Details ---
            has_importer_kw = self._matches_any_keyword(line, IMPORTER_ENTITY_KEYWORDS)
            if has_importer_kw:
                cleaned_imp = clean_entity_text(line, IMPORTER_ENTITY_KEYWORDS)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=True,
                    has_valid_format=bool(len(cleaned_imp) > 4),
                )
                candidates_by_type[DeclarationTypeEnum.IMPORTER_DETAILS].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.IMPORTER_DETAILS,
                        raw_value=line,
                        normalized_value=cleaned_imp,
                        confidence=conf,
                        source_text=line,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                    )
                )

            # --- H. Country of Origin ---
            has_country_kw = self._matches_any_keyword(line, COUNTRY_KEYWORDS)
            if has_country_kw or "made in" in line.lower():
                country_clean, _ = normalize_country(line)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=True,
                    has_valid_format=bool(country_clean),
                    has_contextual_indicators=True,
                )
                candidates_by_type[DeclarationTypeEnum.COUNTRY_OF_ORIGIN].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.COUNTRY_OF_ORIGIN,
                        raw_value=line,
                        normalized_value=country_clean,
                        confidence=conf,
                        source_text=line,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                    )
                )

            # --- I. Consumer Care Details ---
            has_care_kw = self._matches_any_keyword(line, CONSUMER_CARE_KEYWORDS)
            has_email_or_toll = bool(REGEX_PHONE.search(line) or REGEX_EMAIL.search(line))
            if has_care_kw or (has_email_or_toll and ("care" in line.lower() or "1800" in line or "@" in line)):
                formatted_contact, norm_contact = normalize_consumer_care(line)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=has_care_kw,
                    has_valid_format=bool(norm_contact and (norm_contact.phones or norm_contact.emails)),
                    has_contextual_indicators=bool(norm_contact and norm_contact.emails),
                )
                candidates_by_type[DeclarationTypeEnum.CONSUMER_CARE].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.CONSUMER_CARE,
                        raw_value=line,
                        normalized_value=formatted_contact,
                        confidence=conf,
                        source_text=line,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                        structured_data=norm_contact.to_dict() if norm_contact else {},
                    )
                )

            # --- J. Commodity / Generic / Product Name ---
            has_generic_kw = self._matches_any_keyword(line, GENERIC_NAME_KEYWORDS)
            if has_generic_kw:
                cleaned_name = clean_entity_text(line, GENERIC_NAME_KEYWORDS)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=line_conf,
                    has_explicit_keyword=True,
                    has_valid_format=bool(len(cleaned_name) > 3),
                )
                candidates_by_type[DeclarationTypeEnum.GENERIC_NAME].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.GENERIC_NAME,
                        raw_value=line,
                        normalized_value=cleaned_name,
                        confidence=conf,
                        source_text=line,
                        bounding_box=line_bbox,
                        confidence_rationale=rationale,
                    )
                )

        # -------------------------------------------------------------
        # 2. Product Name Fallback Heuristic
        # -------------------------------------------------------------
        if not candidates_by_type[DeclarationTypeEnum.PRODUCT_NAME]:
            # If explicit generic name found, also assign to PRODUCT_NAME if missing
            if candidates_by_type[DeclarationTypeEnum.GENERIC_NAME]:
                top_gen = candidates_by_type[DeclarationTypeEnum.GENERIC_NAME][0]
                candidates_by_type[DeclarationTypeEnum.PRODUCT_NAME].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.PRODUCT_NAME,
                        raw_value=top_gen.raw_value,
                        normalized_value=top_gen.normalized_value,
                        confidence=top_gen.confidence,
                        source_text=top_gen.source_text,
                        bounding_box=top_gen.bounding_box,
                        confidence_rationale=top_gen.confidence_rationale,
                    )
                )
            elif lines:
                # Use first non-declaration prominent headline as Product Name candidate
                first_line = lines[0]
                fl_bbox, fl_conf = self._find_region_for_text(first_line, regions)
                conf, rationale = calculate_extraction_confidence(
                    ocr_confidence=fl_conf,
                    has_explicit_keyword=False,
                    has_valid_format=bool(len(first_line) > 3),
                )
                candidates_by_type[DeclarationTypeEnum.PRODUCT_NAME].append(
                    DeclarationCandidate(
                        declaration_type=DeclarationTypeEnum.PRODUCT_NAME,
                        raw_value=first_line,
                        normalized_value=first_line,
                        confidence=conf * 0.85,
                        source_text=first_line,
                        bounding_box=fl_bbox,
                        confidence_rationale="Moderate: Top headline label heuristic.",
                    )
                )

        # -------------------------------------------------------------
        # 3. Disambiguation & Ambiguity Resolution
        # -------------------------------------------------------------
        final_results: List[DeclarationCandidate] = []

        for decl_type, candidates in candidates_by_type.items():
            if not candidates:
                continue

            # Sort by confidence descending
            candidates.sort(key=lambda c: c.confidence, reverse=True)

            if len(candidates) == 1:
                final_results.append(candidates[0])
            else:
                primary = candidates[0]
                # Check if second candidate has a distinct value and high confidence
                distinct_values = set(c.normalized_value.lower() for c in candidates)

                if len(distinct_values) > 1 and candidates[1].confidence >= 0.70:
                    # Ambiguity detected
                    primary.is_ambiguous = True
                    primary.extraction_status = ExtractionStatusEnum.AMBIGUOUS
                    primary.confidence = round(primary.confidence * 0.85, 4)
                    primary.confidence_rationale = (
                        f"Ambiguous: {len(candidates)} competing candidates detected ({', '.join(distinct_values)})."
                    )
                    primary.alternative_candidates = [
                        c.to_dict() for c in candidates[1:]
                    ]

                final_results.append(primary)

        return final_results

    async def persist_declarations_for_scan(
        self,
        db: AsyncSession,
        scan_id: str,
        candidates: List[DeclarationCandidate],
    ) -> List[Declaration]:
        """
        Persist extracted declaration candidates to the database for a scan.
        Idempotent: removes previous automated declarations for this scan before storing fresh ones.
        """
        # 1. Clean existing declarations for this scan to avoid uncontrolled duplicate inflation
        await db.execute(delete(Declaration).where(Declaration.scan_id == scan_id))

        persisted_records: List[Declaration] = []

        for c in candidates:
            # Prepare bounding box JSON with coordinates and extraction method
            bbox_payload = None
            if c.bounding_box:
                bbox_payload = {
                    **c.bounding_box.to_dict(),
                    "extraction_method": c.extraction_method,
                    "confidence_rationale": c.confidence_rationale,
                    "is_ambiguous": c.is_ambiguous,
                    "structured_data": c.structured_data or {},
                    "alternative_candidates": c.alternative_candidates,
                }

            record = Declaration(
                scan_id=scan_id,
                declaration_type=c.declaration_type,
                raw_value=c.raw_value,
                normalized_value=c.normalized_value,
                confidence=c.confidence,
                source_text=c.source_text,
                bounding_box=bbox_payload,
                extraction_status=c.extraction_status,
            )
            db.add(record)
            persisted_records.append(record)

        await db.commit()

        # Refresh all records
        for r in persisted_records:
            await db.refresh(r)

        return persisted_records
