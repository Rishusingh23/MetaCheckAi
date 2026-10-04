# MetaCheck AI — Legal Metrology Rule Engine & Statutory Baseline (Phase 5.1 Verified)

## 1. Overview
The **MetaCheck AI Rule Engine** is a modular, versioned, configurable legal compliance evaluation system that assesses extracted packaged commodity declarations against statutory Legal Metrology rules.

Every rule, version, and validation algorithm in this engine is strictly grounded in official statutory publications from the **Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution, Government of India**.

---

## 2. Authoritative Statutory Sources

All legal rules are verified against official Government of India publications:
- **Official Portal**: [Department of Consumer Affairs — Legal Metrology Division](https://consumeraffairs.gov.in/pages/legal-metrology-act)
- **Principal Legislation**: The Legal Metrology Act, 2009 (Act No. 1 of 2010)
- **Principal Rules**: The Legal Metrology (Packaged Commodities) Rules, 2011 (G.S.R. 202(E), dated 7th March 2011)
- **Statutory Amendments**:
  - G.S.R. 592(E) dated 23rd June 2017 (GST & Imported Origin Amendments w.e.f. 1st July 2017)
  - G.S.R. 779(E) dated 2nd November 2021 (Unit Sale Price & Date of Manufacture Amendments)
  - G.S.R. 226(E), 571(E), and 758(E) (Enforcement timeline notifications fixing effective date as 1st December 2022)
  - Legal Metrology (Packaged Commodities) (Amendment) Rules, 2026 (E-Commerce Country of Origin Filter requirement effective 1st July 2026)

---

## 3. Statutory Rule Baseline & Provisions

### 3.1. Rule 6(1)(a) — Manufacturer, Packer, or Importer Identification
- **Statutory Requirement**: Complete name and address of the manufacturer, or where manufacturer is not the packer, both the manufacturer and packer, or for imported goods the importer.
- **Gazette Reference**: G.S.R. 202(E) dated 07-03-2011 & G.S.R. 592(E) dated 23-06-2017.
- **Applicable Contexts**: `PHYSICAL_PACKAGE`, `DOMESTIC_PRODUCT`, `IMPORTED_PRODUCT`, `E_COMMERCE_LISTING`.

### 3.2. Rule 6(1)(b) — Generic or Common Name of Commodity
- **Statutory Requirement**: The common or generic names of the commodity contained in the package declared on the principal display panel (PDP).
- **Gazette Reference**: G.S.R. 202(E) dated 07-03-2011.
- **Applicable Contexts**: `PHYSICAL_PACKAGE`, `DOMESTIC_PRODUCT`, `IMPORTED_PRODUCT`, `E_COMMERCE_LISTING`.

### 3.3. Rule 6(1)(c) & Rule 11 / Second Schedule — Net Quantity
- **Statutory Requirement**: Net quantity in standard units of weight (`g`, `kg`), volume (`ml`, `L`), length (`m`), or where sold by number, the count/number of the commodity (`N`, `units`, `pieces`, `nos`, `pairs`, `sets`).
- **Gazette Reference**: G.S.R. 202(E) dated 07-03-2011.
- **Statutory Note**: Valid packages sold by number/count are explicitly permitted and supported without restrictive unit whitelist rejections.

### 3.4. Rule 6(1)(d) — Date of Manufacture / Packing / Import
- **Historical Version 1.0 (01-04-2011 to 30-11-2022)**: Month and year of manufacture or pre-packing or import.
- **Current Version 2.0 (01-12-2022 onwards per G.S.R. 779(E))**: Month and year in which commodity is manufactured (domestic), month and year of import (imported), or month and year of pre-packing where packed by an entity other than manufacturer.

### 3.5. Rule 6(1)(e) — Maximum Retail Price (MRP)
- **Historical Pre-GST Version 1.0 (01-04-2011 to 30-06-2017)**: *"Max. retail price Rs. ... / ₹ ... inclusive of all taxes"*.
- **Post-GST / 2021 Version 2.0 (01-07-2017 onwards per G.S.R. 592(E) & 779(E))**: *"Maximum or Max. Retail Price Rs./₹ ... inclusive of all taxes or MRP Rs./₹ ... (inclusive of all taxes)"*.

### 3.6. Rule 6(1)(ea) & Rule 6(11) — Unit Sale Price (USP)
- **Statutory Requirement**: Unit sale price in Rupees per g/ml (for net quantity <= 1kg/1L), per kg/L (for net quantity > 1kg/1L), or per number/piece.
- **Effective Date**: **1st December 2022** (G.S.R. 779(E) dated 02-11-2021; enforced w.e.f. 01-12-2022 per G.S.R. 758(E)).
- **Exemptions**: Packages where net quantity is exactly 1 kg, 1 L, 1 m, or 1 number.

### 3.7. Rule 6(1)(g) — Consumer Care Details
- **Statutory Requirement**: Name, address, telephone number, and e-mail address of the person or office who can be contacted for consumer complaints.
- **Screening Standard**: If contact details are partially present (e.g. phone or email), yields `REVIEW` with an advisory note. Conclusive total absence on clean label yields `FAIL` (*"Potential non-compliance detected"*).

### 3.8. Rule 6(1)(h) & Rule 6(10A) — Country of Origin Distinctions
- **Physical Imported Package (`PCR_2011_RULE_6_1_H`)**: Country of origin or manufacture or assembly mandatory for imported products w.e.f. 01-07-2017 (G.S.R. 592(E)). For domestic packages with Indian manufacturer details, a separate country of origin declaration is not mandatory on the physical label.
- **E-Commerce Listing (`PCR_2026_RULE_6_10A_ECOM`)**: Marketplace e-commerce listings must prominently declare country of origin with consumer search/filter enablement under Rule 6(10A):
  - **Version 1.0**: Legal Metrology (Packaged Commodities) Amendment Rules, 2026 (G.S.R. 128(E) dated 13 February 2026; effective 1 July 2026 to 1 July 2027).
  - **Version 2.0**: Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026 (G.S.R. 312(E) dated 27 April 2026; effective 1 July 2027 onwards).
  - This rule is **NOT** applicable to physical package inspections.

### 3.9. Rules 7 & 8, Table I — Font Size & Prominence
- **Statutory Requirement**: Minimum numeral and character heights (1.0 mm to 6.0 mm) relative to principal display panel area.
- **Calibration Standard**: Uncalibrated 2D digital photographs cannot provide certified physical millimeter dimensions. The engine evaluates visual pixel prominence and returns `REVIEW` with an explicit calibration caveat, advising on-site millimeter measurement by an authorized officer.

---

## 4. Rule Versioning & Applicability Model

Every rule version in MetaCheck AI includes complete statutory metadata:
- `rule_code`: Statutory clause identifier
- `legal_reference`: Exact statutory citation
- `requirement_text`: Official statutory requirement statement
- `source_document`: Department of Consumer Affairs statutory source
- `source_gazette_reference`: Gazette publication number & date
- `active_from` / `active_to`: Temporal validity window
- `applicable_contexts`: `PHYSICAL_PACKAGE`, `E_COMMERCE_LISTING`, `IMPORTED_PRODUCT`, `DOMESTIC_PRODUCT`
- `verification_status`: `VERIFIED_OFFICIAL`, `NEEDS_LEGAL_REVIEW`, `DEPRECATED`

---

## 5. Safe Legal Language & Advisory Standard

MetaCheck AI strictly enforces safe legal advisory language:
- Automated screening failures indicate:
  > **"Potential non-compliance detected"** (Never *"Legal violation confirmed"*)
- Violations created automatically are assigned:
  > `status: FLAGGED_FOR_REVIEW`
- Uncertain, uncalibrated, blurry, or ambiguous evidence yields:
  > `status: REVIEW` (rather than automated `FAIL`)
- Final legal non-compliance determinations and compounding orders rest exclusively with authorized **Legal Metrology Officers**.

---

## 6. Known Legal Limitations

1. **Physical Scale Calibration**: 2D photos without an optical calibration scale target cannot certify absolute physical millimeter dimensions under Rule 7 Table I.
2. **Multi-panel Packaging**: When packaging spans multiple detached panels, full compliance assessment requires scanning all panels (`FRONT_PDP`, `BACK_DECLARATION`, `SIDE_PANEL`, `BOTTOM_BASE`).
3. **Sector-Specific Exemptions**: Wholesale packages, export commodities, and packages with net weight <= 10g/10ml (or package items exempt under Rule 26) require officer discretion.

---

## 7. Official Statutory Rule Baseline Table

| Rule Code | Exact Provision | Source | Effective From | Effective To | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PCR_2011_RULE_6_1_A` | Name & complete address of manufacturer / packer / importer | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E) & GSR 592(E)) | 2011-04-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_B` | Common or generic names of commodity on Principal Display Panel | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) | 2011-04-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_C` | Net quantity in standard metric units or count/number per Second Schedule | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E) & Rule 11) | 2011-04-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_D` (v1.0) | Month & year of manufacture or pre-packed or imported (Historical) | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) | 2011-04-01 | 2022-11-30 | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_D` (v2.0) | Month & year of manufacture (or import for imported goods) | Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021 (GSR 779(E)) | 2022-12-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_E` (v1.0) | Max. retail price Rs. ... inclusive of all taxes (Pre-GST wording) | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) | 2011-04-01 | 2017-06-30 | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_E` (v2.0) | Maximum Retail Price Rs./₹ ... inclusive of all taxes or MRP Rs./₹ ... | Legal Metrology (Packaged Commodities) Amendment Rules, 2017 & 2021 (GSR 592(E) & 779(E)) | 2017-07-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2021_RULE_6_1_EA` | Unit Sale Price in Rs. per g/ml, per kg/L, or per number/piece per Rule 6(11) | Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021 (GSR 779(E) & GSR 758(E)) | 2022-12-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_6_1_G` | Consumer care telephone number, email, and grievance address | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) | 2011-04-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2026_RULE_6_10A_ECOM` (v1.0)| Country of origin searchable/sortable filter for imported products on e-commerce (G.S.R. 128(E) dated 13 Feb 2026) | Legal Metrology (Packaged Commodities) Amendment Rules, 2026 | 2026-07-01 | 2027-07-01 | `VERIFIED_OFFICIAL` |
| `PCR_2026_RULE_6_10A_ECOM` (v2.0)| Country of origin searchable and sortable filter for imported products on e-commerce (G.S.R. 312(E) dated 27 Apr 2026) | Legal Metrology (Packaged Commodities) Second Amendment Rules, 2026 | 2027-07-01 | Present | `VERIFIED_OFFICIAL` |
| `PCR_2011_RULE_7_8` | Minimum font and numeral height ratio per Table I (Uncalibrated photo review) | Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E)) | 2011-04-01 | Present | `VERIFIED_OFFICIAL` |
