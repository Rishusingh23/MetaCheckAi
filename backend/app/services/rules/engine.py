from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compliance import ComplianceCheck, ComplianceStatusEnum
from app.models.declaration import Declaration
from app.models.evidence import Evidence, EvidenceSourceTypeEnum
from app.models.history import InspectionHistory
from app.models.inspection import Inspection, InspectionStatusEnum, OverallResultEnum
from app.models.ocr import OCRResult
from app.models.product import Product
from app.models.rule import Rule, RuleVersion, SeverityEnum
from app.models.scan import Scan
from app.models.violation import Violation, ViolationSeverityEnum, ViolationStatusEnum
from app.services.rules.applicability import (
    is_rule_version_applicable,
    is_rule_version_temporally_valid,
    normalize_datetime,
)
from app.services.rules.evaluator import rule_evaluator
from app.services.rules.models import EvaluationContext, FindingRecord
from app.services.rules.seed_rules import seed_statutory_baseline_rules


class RuleEngineService:
    """
    Central orchestration service for Legal Metrology compliance evaluation.
    Evaluates packaged commodity declarations against versioned statutory rules.
    """

    async def evaluate_inspection(
        self,
        inspection_id: str,
        db: AsyncSession,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 1. Load Inspection with product, scans, and existing declarations
        query = (
            select(Inspection)
            .options(
                selectinload(Inspection.product),
                selectinload(Inspection.scans).selectinload(Scan.ocr_results),
            )
            .where(Inspection.id == inspection_id)
        )
        res = await db.execute(query)
        inspection = res.scalar_one_or_none()
        if not inspection:
            raise ValueError(f"Inspection with ID '{inspection_id}' not found.")

        # 2. Gather all declarations from scans belonging to this inspection
        scan_ids = [s.id for s in inspection.scans]
        declarations: List[Declaration] = []
        if scan_ids:
            decl_query = select(Declaration).where(Declaration.scan_id.in_(scan_ids))
            decl_res = await db.execute(decl_query)
            declarations = list(decl_res.scalars().all())

        # 3. Aggregate raw OCR text and quality metrics from scans
        full_ocr_texts = []
        best_quality = None
        for s in inspection.scans:
            for ocr in s.ocr_results:
                raw_t = getattr(ocr, "extracted_text", None) or getattr(ocr, "full_text", None)
                if raw_t:
                    full_ocr_texts.append(raw_t)
                p_meta = getattr(ocr, "processing_metadata", None)
                if isinstance(p_meta, dict):
                    q_metrics = p_meta.get("quality_metrics") if "quality_metrics" in p_meta else p_meta
                    if isinstance(q_metrics, dict) and "is_blurry" in q_metrics:
                        best_quality = q_metrics
                elif hasattr(ocr, "quality_metrics") and isinstance(getattr(ocr, "quality_metrics"), dict):
                    best_quality = getattr(ocr, "quality_metrics")

        combined_ocr_text = "\n".join(full_ocr_texts) if full_ocr_texts else None

        # 4. Build EvaluationContext
        target_date = inspection.inspection_date or datetime.now(timezone.utc)
        context = EvaluationContext(
            inspection_id=inspection.id,
            product=inspection.product,
            inspection_date=target_date,
            declarations=declarations,
            ocr_raw_text=combined_ocr_text,
            image_quality=best_quality,
        )

        # 5. Fetch all Active Rules with their versions
        rules_query = select(Rule).options(selectinload(Rule.versions)).where(Rule.is_active == True)
        rules_res = await db.execute(rules_query)
        rules = list(rules_res.scalars().all())

        # If rules table is empty, seed statutory baseline
        if not rules:
            await seed_statutory_baseline_rules(db)
            rules_res = await db.execute(rules_query)
            rules = list(rules_res.scalars().all())

        # 6. Select the single most relevant active RuleVersion for each rule
        selected_versions: List[RuleVersion] = []
        for r in rules:
            matching_versions = [
                v for v in r.versions if is_rule_version_applicable(v, target_date, inspection.product)
            ]
            if matching_versions:
                # Pick highest version or latest active_from
                best_v = max(
                    matching_versions,
                    key=lambda v: (normalize_datetime(v.active_from) or datetime.min),
                )
                selected_versions.append(best_v)
            elif r.versions:
                # If no version temporally fits, pick latest to evaluate applicability failure
                selected_versions.append(r.versions[0])

        # 7. Evaluate each RuleVersion
        findings: List[FindingRecord] = []
        for rule_ver in selected_versions:
            finding = rule_evaluator.evaluate(rule_ver, context)
            findings.append(finding)

        # 8. Idempotently Clean previous automated compliance checks & violations for this inspection
        # Delete previous checks (cascade will remove violations/evidence linked to them)
        del_checks = delete(ComplianceCheck).where(ComplianceCheck.inspection_id == inspection.id)
        await db.execute(del_checks)
        await db.flush()

        # 9. Persist ComplianceChecks, Violations, and Evidence
        created_checks: List[ComplianceCheck] = []
        created_violations: List[Violation] = []
        evidence_records: List[Evidence] = []

        for f in findings:
            sev_str = f.severity.value if hasattr(f.severity, "value") else str(f.severity)

            check = ComplianceCheck(
                inspection_id=inspection.id,
                rule_version_id=f.rule_version.id,
                status=f.status,
                explanation=f.explanation,
                detected_value=f.detected_value,
                expected_requirement=f.expected_requirement,
                confidence=f.confidence,
                severity=sev_str,
            )
            db.add(check)
            await db.flush()
            created_checks.append(check)

            # If check failed, create a FLAGGED_FOR_REVIEW violation
            if f.is_violation or f.status == ComplianceStatusEnum.FAIL:
                viol_severity = (
                    ViolationSeverityEnum.CRITICAL
                    if f.severity == "CRITICAL" or getattr(f.severity, "name", "") == "CRITICAL"
                    else ViolationSeverityEnum.MAJOR
                )
                violation = Violation(
                    inspection_id=inspection.id,
                    compliance_check_id=check.id,
                    violation_code=f"VIOL_{f.rule_code}",
                    description=f.explanation,
                    severity=viol_severity,
                    status=ViolationStatusEnum.FLAGGED_FOR_REVIEW,
                )
                db.add(violation)
                await db.flush()
                created_violations.append(violation)

                # Add evidence linked to violation
                for ev_spec in f.evidences:
                    ev_type = (
                        EvidenceSourceTypeEnum[ev_spec.source_type]
                        if ev_spec.source_type in EvidenceSourceTypeEnum.__members__
                        else EvidenceSourceTypeEnum.OCR_TEXT_SNIPPET
                    )
                    ev = Evidence(
                        inspection_id=inspection.id,
                        violation_id=violation.id,
                        source_type=ev_type,
                        image_url_or_path=ev_spec.image_url_or_path,
                        bounding_box=ev_spec.bounding_box,
                        description=ev_spec.description,
                        confidence=ev_spec.confidence,
                    )
                    db.add(ev)
                    evidence_records.append(ev)

        # 10. Update Inspection Status & Overall Result
        fail_count = sum(1 for f in findings if f.status == ComplianceStatusEnum.FAIL)
        review_count = sum(1 for f in findings if f.status == ComplianceStatusEnum.REVIEW)
        pass_count = sum(1 for f in findings if f.status == ComplianceStatusEnum.PASS)
        na_count = sum(1 for f in findings if f.status == ComplianceStatusEnum.NOT_APPLICABLE)

        overall_status = "COMPLIANT"
        if fail_count > 0:
            overall_status = "POTENTIAL_NON_COMPLIANCE"
            inspection.status = InspectionStatusEnum.REVIEW_REQUIRED
            inspection.overall_result_placeholder = OverallResultEnum.POTENTIAL_NON_COMPLIANCE
        elif review_count > 0:
            overall_status = "REVIEW_REQUIRED"
            inspection.status = InspectionStatusEnum.REVIEW_REQUIRED
            inspection.overall_result_placeholder = OverallResultEnum.PENDING_VERIFICATION
        else:
            overall_status = "COMPLIANT"
            inspection.status = InspectionStatusEnum.COMPLETED
            inspection.overall_result_placeholder = OverallResultEnum.COMPLIANT

        # 11. Record Inspection Audit Log
        history = InspectionHistory(
            inspection_id=inspection.id,
            user_id=user_id or inspection.inspector_id,
            action="COMPLIANCE_EVALUATION",
            previous_status=inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status),
            new_status=overall_status,
            change_metadata={
                "total_rules_evaluated": len(findings),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "review_count": review_count,
                "violations_flagged": len(created_violations),
            },
        )
        db.add(history)

        await db.commit()

        # Mean confidence and Screening Score (Mathematical formula: Pass / (Pass + Fail + Review) * 100)
        mean_conf = (
            sum(f.confidence for f in findings) / len(findings) if findings else 1.0
        )
        evaluated_actionable = pass_count + fail_count + review_count
        screening_score = (
            round((pass_count / evaluated_actionable) * 100.0, 1)
            if evaluated_actionable > 0
            else 100.0
        )

        return {
            "inspection_id": inspection.id,
            "overall_status": overall_status,
            "total_rules_evaluated": len(findings),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "review_count": review_count,
            "not_applicable_count": na_count,
            "violations_flagged": len(created_violations),
            "mean_confidence": round(mean_conf, 3),
            "screening_score": screening_score,
            "findings": findings,
            "checks": created_checks,
            "disclaimer": (
                "MetaCheck AI operates as an AI-assisted screening tool. Output findings represent "
                "advisory indications. Final legal compliance determinations rest exclusively with "
                "authorized Legal Metrology Officers."
            ),
        }

    async def get_inspection_compliance(
        self,
        inspection_id: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Retrieve existing compliance check dossier for an inspection."""
        query = (
            select(ComplianceCheck)
            .options(
                selectinload(ComplianceCheck.rule_version).selectinload(RuleVersion.rule),
                selectinload(ComplianceCheck.violations).selectinload(Violation.evidences),
            )
            .where(ComplianceCheck.inspection_id == inspection_id)
            .order_by(ComplianceCheck.created_at.asc())
        )
        res = await db.execute(query)
        checks = list(res.scalars().all())

        fail_count = sum(1 for c in checks if c.status == ComplianceStatusEnum.FAIL)
        review_count = sum(1 for c in checks if c.status == ComplianceStatusEnum.REVIEW)
        pass_count = sum(1 for c in checks if c.status == ComplianceStatusEnum.PASS)
        na_count = sum(1 for c in checks if c.status == ComplianceStatusEnum.NOT_APPLICABLE)

        overall_status = "COMPLIANT"
        if fail_count > 0:
            overall_status = "POTENTIAL_NON_COMPLIANCE"
        elif review_count > 0:
            overall_status = "REVIEW_REQUIRED"
        elif not checks:
            overall_status = "PENDING_EVALUATION"

        mean_conf = (
            sum(c.confidence or 0.85 for c in checks) / len(checks) if checks else 0.0
        )
        evaluated_actionable = pass_count + fail_count + review_count
        screening_score = (
            round((pass_count / evaluated_actionable) * 100.0, 1)
            if evaluated_actionable > 0
            else 100.0
        )

        violations_count = sum(len(c.violations) for c in checks)

        return {
            "inspection_id": inspection_id,
            "overall_status": overall_status,
            "total_rules_evaluated": len(checks),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "review_count": review_count,
            "not_applicable_count": na_count,
            "violations_flagged": violations_count,
            "mean_confidence": round(mean_conf, 3),
            "screening_score": screening_score,
            "checks": checks,
            "disclaimer": (
                "MetaCheck AI operates as an AI-assisted screening tool. Output findings represent "
                "advisory indications. Final legal compliance determinations rest exclusively with "
                "authorized Legal Metrology Officers."
            ),
        }



rule_engine = RuleEngineService()
