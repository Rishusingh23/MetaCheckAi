"""
Export and report management service for JSON, CSV, and PDF formats.
Manages immutable report generation, filesystem persistence, and sanitized export streams.
"""
import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance import ComplianceCheck
from app.models.declaration import Declaration
from app.models.history import InspectionHistory
from app.models.inspection import Inspection
from app.models.report import Report, ReportFormatEnum, ReportStatusEnum, ReportTypeEnum
from app.models.rule import RuleVersion
from app.models.scan import Scan
from app.models.user import User
from app.models.violation import Violation
from app.services.reports.pdf_builder import pdf_builder


class ReportExportService:
    """Service handling report rendering, database persistence, and document delivery."""

    def __init__(self, storage_dir: str = "storage/reports"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    async def gather_inspection_dossier(
        self,
        inspection_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Fetch complete hydrated inspection entity hierarchy for report compilation."""
        q = (
            select(Inspection)
            .options(
                selectinload(Inspection.product),
                selectinload(Inspection.inspector).selectinload(User.role),
                selectinload(Inspection.scans).selectinload(Scan.declarations),
                selectinload(Inspection.compliance_checks).selectinload(ComplianceCheck.rule_version).selectinload(RuleVersion.rule),
                selectinload(Inspection.violations).selectinload(Violation.evidences),
                selectinload(Inspection.history_logs).selectinload(InspectionHistory.user),
            )
            .where(Inspection.id == inspection_id)
        )
        res = await db.execute(q)
        inspection = res.scalar_one_or_none()
        if not inspection:
            raise ValueError(f"Inspection with ID '{inspection_id}' not found.")

        # Product data
        prod = inspection.product
        product_data = {
            "id": prod.id if prod else None,
            "name": prod.name if prod else "Packaged Commodity",
            "brand": prod.brand if prod else "N/A",
            "category": prod.category if prod else "General",
            "barcode_gtin": prod.barcode_gtin if prod else None,
            "country_of_origin": prod.country_of_origin if prod else None,
            "manufacturer": prod.manufacturer if prod else None,
            "packer": prod.packer if prod else None,
            "importer": prod.importer if prod else None,
        }

        # Declarations
        all_declarations = []
        for s in inspection.scans:
            for d in s.declarations:
                all_declarations.append({
                    "id": d.id,
                    "declaration_type": d.declaration_type.value if hasattr(d.declaration_type, "value") else str(d.declaration_type),
                    "raw_value": d.raw_value,
                    "normalized_value": d.normalized_value,
                    "confidence": d.confidence or 0.85,
                    "extraction_status": d.extraction_status.value if hasattr(d.extraction_status, "value") else str(d.extraction_status),
                    "bounding_box": d.bounding_box,
                })

        # Compliance checks
        checks_data = []
        for c in inspection.compliance_checks:
            r_code = c.rule_version.rule.rule_code if c.rule_version and c.rule_version.rule else "RULE"
            r_name = c.rule_version.rule.name if c.rule_version and c.rule_version.rule else "Statutory Rule"
            l_ref = c.rule_version.rule.legal_reference if c.rule_version and c.rule_version.rule else "PCR 2011"
            checks_data.append({
                "id": c.id,
                "rule_code": r_code,
                "rule_name": r_name,
                "legal_reference": l_ref,
                "version": c.rule_version.version if c.rule_version else "1.0",
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "severity": c.severity,
                "explanation": c.explanation,
                "detected_value": c.detected_value,
                "expected_requirement": c.expected_requirement,
                "confidence": c.confidence,
            })

        # Violations
        violations_data = []
        for v in inspection.violations:
            violations_data.append({
                "id": v.id,
                "violation_code": v.violation_code,
                "description": v.description,
                "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                "status": v.status.value if hasattr(v.status, "value") else str(v.status),
                "officer_comment": v.officer_comment,
                "reviewed_by": v.reviewed_by,
                "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
                "evidences": [
                    {
                        "source_type": e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type),
                        "description": e.description,
                        "bounding_box": e.bounding_box,
                        "confidence": e.confidence,
                    }
                    for e in v.evidences
                ],
            })

        # History logs
        history_data = []
        for h in sorted(inspection.history_logs, key=lambda x: x.timestamp):
            history_data.append({
                "id": h.id,
                "action": h.action,
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "timestamp": h.timestamp.isoformat(),
                "user_name": h.user.name if h.user else "System",
                "change_metadata": h.change_metadata,
            })

        return {
            "inspection": {
                "id": inspection.id,
                "status": inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status),
                "overall_result_placeholder": inspection.overall_result_placeholder.value if hasattr(inspection.overall_result_placeholder, "value") else str(inspection.overall_result_placeholder),
                "source_type": inspection.source_type.value if hasattr(inspection.source_type, "value") else str(inspection.source_type),
                "inspection_date": inspection.inspection_date.isoformat(),
                "created_at": inspection.created_at.isoformat(),
                "notes": inspection.notes,
                "inspector_name": inspection.inspector.name if inspection.inspector else "Unassigned",
                "product_name": product_data["name"],
                "brand": product_data["brand"],
                "category": product_data["category"],
            },
            "product": product_data,
            "declarations": all_declarations,
            "compliance_checks": checks_data,
            "violations": violations_data,
            "history_logs": history_data,
            "document_title": "AI-Assisted Legal Metrology Inspection Report",
            "document_classification": "Advisory / Screening Document — Not an Official Government Enforcement Order",
            "legal_disclaimer": (
                "Advisory / Screening Document — Not an Official Government Enforcement Order. "
                "MetaCheck AI operates as an automated AI screening assistant. Output findings represent "
                "potential advisory observations. Final legal compliance determinations rest exclusively with authorized "
                "Legal Metrology Officers pursuant to The Legal Metrology Act, 2009 and PCR 2011."
            ),
        }

    async def generate_and_save_report(
        self,
        inspection_id: str,
        report_type: ReportTypeEnum,
        report_format: ReportFormatEnum,
        generated_by_user_id: Optional[str],
        db: AsyncSession,
    ) -> Report:
        """Create and persist an immutable report record."""
        dossier = await self.gather_inspection_dossier(inspection_id, db)

        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{inspection_id[:8]}_{timestamp_str}.{report_format.value.lower()}"
        file_path = os.path.join(self.storage_dir, filename)

        if report_format == ReportFormatEnum.PDF:
            pdf_bytes = pdf_builder.generate_advisory_report(
                inspection_data=dossier["inspection"],
                checks_data=dossier["compliance_checks"],
                violations_data=dossier["violations"],
                declarations_data=dossier["declarations"],
                history_data=dossier["history_logs"],
            )
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)

        elif report_format == ReportFormatEnum.JSON:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(dossier, f, indent=2, ensure_ascii=False)

        elif report_format == ReportFormatEnum.CSV:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Inspection ID",
                    "Product Name",
                    "Brand",
                    "Category",
                    "Inspection Date",
                    "Rule Code",
                    "Statutory Reference",
                    "Finding Status",
                    "Severity",
                    "Detected Value",
                    "Explanation",
                    "Violation Code",
                    "Violation Status",
                    "Officer Comment",
                ])

                insp = dossier["inspection"]
                checks = dossier["compliance_checks"]
                violations_map = {v.get("violation_code"): v for v in dossier["violations"]}

                for c in checks:
                    r_code = c["rule_code"]
                    viol_key = f"VIOL_{r_code}"
                    viol = violations_map.get(viol_key, {})
                    writer.writerow([
                        insp["id"],
                        insp["product_name"],
                        insp["brand"],
                        insp["category"],
                        insp["inspection_date"],
                        c["rule_code"],
                        c["legal_reference"],
                        c["status"],
                        c["severity"],
                        c["detected_value"] or "",
                        c["explanation"],
                        viol.get("violation_code", ""),
                        viol.get("status", ""),
                        viol.get("officer_comment", ""),
                    ])

        # Create immutable Report entity
        report = Report(
            inspection_id=inspection_id,
            report_type=report_type,
            format=report_format,
            file_path=file_path,
            generated_by=generated_by_user_id,
            status=ReportStatusEnum.READY,
        )
        db.add(report)

        # Log Report generation in InspectionHistory
        history = InspectionHistory(
            inspection_id=inspection_id,
            user_id=generated_by_user_id,
            action=f"REPORT_GENERATED_{report_format.value}",
            previous_status=dossier["inspection"]["status"],
            new_status=dossier["inspection"]["status"],
            change_metadata={
                "report_type": report_type.value if hasattr(report_type, "value") else str(report_type),
                "format": report_format.value if hasattr(report_format, "value") else str(report_format),
                "file_path": file_path,
            },
        )
        db.add(history)

        await db.commit()
        await db.refresh(report)
        return report

    def read_report_file(self, report: Report) -> bytes:
        """Safely read report file bytes from storage."""
        if not report.file_path or not os.path.exists(report.file_path):
            raise FileNotFoundError(f"Report file for ID '{report.id}' is not available on disk.")
        with open(report.file_path, "rb") as f:
            return f.read()


report_service = ReportExportService()
