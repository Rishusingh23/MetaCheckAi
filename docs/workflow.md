# MetaCheck AI — Inspection Workflow & Enforcement User Guide

## 1. Overview
MetaCheck AI transforms automated Legal Metrology AI screening into an authoritative, enforceable inspection management workflow. It provides Legal Metrology Officers (LMOs) with tools to review findings, substantiate observations with spatial evidence, submit statutory determinations, and compile immutable advisory reports.

---

## 2. Standard Inspection Lifecycle

```
Commodity Ingestion / Field Scan
            │
            ▼
Optical Character Recognition (OCR & Spatial Coordinates)
            │
            ▼
Structured Declaration Extraction & Normalization
            │
            ▼
Statutory Rule Evaluation (Version-Aware PCR 2011 Engine)
            │
            ├── All Checks PASS ──────────────► Status: COMPLETED
            │
            └── Potential Violations Flagged ─► Status: REVIEW_REQUIRED
                                                      │
                                                      ▼
                                          Enforcement Officer Review
                                          (Confirm or Dismiss with Comment)
                                                      │
                                                      ▼
                                              Status: OFFICER_REVIEWED
                                                      │
                                                      ▼
                                          Report Export (PDF / JSON / CSV)
```

---

## 3. Enforcement Officer Review Process

### 3.1. Identifying Potential Non-Compliances
When the rule engine detects a potential violation, it records a `Violation` with `status = FLAGGED_FOR_REVIEW`.
Officers can inspect:
- **Statutory Rule Code & Version**: e.g., `PCR_2021_RULE_6_1_EA` (Unit Sale Price mandate).
- **Gazette Reference**: e.g., `G.S.R. 779(E) dated 2nd Nov 2021`.
- **Detected Value vs. Expected Requirement**: Detected text snippets compared against statutory requirements.
- **Confidence Score & Image Bounding Box**: Highlighted region on the commodity label.

### 3.2. Submitting Statutory Review Decisions
Officers select either:
1. **Confirm Violation (`OFFICER_CONFIRMED`)**:
   - Confirms that the commodity packaging is in non-compliance with the cited rule.
   - Requires entering a detailed rationale or physical inspection observation.
2. **Dismiss Finding (`DISMISSED`)**:
   - Dismisses the AI-flagged finding if physical packaging examination proves compliance (e.g. text legible under direct lighting, permissible exemption applicable).
   - Requires recording the factual justification.

---

## 4. Operational Dashboard & Real-Time Analytics

The Executive Compliance Dashboard provides live database metrics with no synthetic mock data:
- **Inspection Metrics**: Total screenings, daily volumes, review backlogs, and overall compliance rate.
- **Categorical Trends**: Distribution of inspections and infractions across commodity sectors (Food & Beverages, Edible Oils, Personal Care, Electronics, etc.).
- **Risk & Severity Analysis**: Breakdown of findings by statutory impact (`CRITICAL`, `MAJOR`, `MINOR`, `ADVISORY`).
- **Rule Infraction Frequency**: Top non-compliant PCR 2011 clauses identified across market surveillance.

---

## 5. Advisory Reports & Inspection Dossier Export

AI-assisted advisory inspection reports can be generated on demand:
- **PDF Report**: Formatted vector document titled *"AI-Assisted Legal Metrology Inspection Report"* with prominent advisory disclaimer, commodity specifications, finding breakdown, officer review statements, and statutory notice.
- **JSON Dossier**: Complete structured hierarchical dataset for system integration and analytics.
- **CSV Data Sheet**: Tabular export formatted for screening records and statistical reporting.
