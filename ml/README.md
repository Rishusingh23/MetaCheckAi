# MetaCheck AI — Machine Learning & Computer Vision Subsystem

## Overview
The Machine Learning and Computer Vision subsystem provides the optical text recognition, spatial bounding box coordinate mapping, and pre-flight label quality analytics pipeline for packaged commodity inspections under the Legal Metrology (Packaged Commodities) Rules, 2011.

---

## OCR Architecture & Modular Providers

MetaCheck AI implements a modular, decoupled provider architecture governed by `BaseOCRProvider`:

```
               ┌──────────────────────────────┐
               │    Packaged Commodity Image  │
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │     File Validation & MIME   │ (Magic bytes, size & dim checks)
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │   Image Quality Analytics    │ (Laplacian blur, brightness, contrast)
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │   Pre-Processing Pipeline    │ (EXIF orientation, Grayscale, Contrast, Unsharp Mask)
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │     OCR Provider Factory     │
               └──────────────┬───────────────┘
          ┌───────────────────┼───────────────────┐
          │                   │                   │
┌─────────▼─────────┐ ┌───────▼─────────┐ ┌───────▼─────────┐
│  MockOCRProvider  │ │TesseractProvider│ │PaddleOCRProvider│
│  (CI/CD & Tests)  │ │  (pytesseract)  │ │   (PP-OCRv4)    │
└─────────┬─────────┘ └───────┬─────────┘ └───────┬─────────┘
          └───────────────────┼───────────────────┘
                              │
               ┌──────────────▼───────────────┐
               │  Structured OCR Result Data  │ (Text, Confidence, Spatial Bounding Boxes)
               └──────────────┬───────────────┘
                              │
               ┌──────────────▼───────────────┐
               │ DB Persistence: `OCRResult`  │ (Linked to Scan & ProductImage)
               └──────────────────────────────┘
```

### Supported Providers:
1. **`MockOCRProvider`**: High-fidelity synthetic OCR engine for deterministic unit tests, CI/CD runners, and fallback environments without external C++ OCR binaries.
2. **`TesseractOCRProvider`**: Production OCR engine utilizing Google's Tesseract with non-blocking async worker thread execution.
3. **`PaddleOCRProvider`**: Multi-lingual deep learning OCR model (PP-OCRv4) converting 4-point polygon text detection coordinates into axis-aligned spatial bounding boxes.
4. **`OCRProviderFactory`**: Dynamically detects available engines or honors configured engine preferences (`auto`, `tesseract`, `paddleocr`, `mock`).

---

## Computer Vision Analytics & Quality Metrics

Before OCR extraction, images undergo quantitative evaluation:

- **Sharpness / Blur Variance**: Discrete 2D Laplacian operator convolution over grayscale array:
  $$\text{Var}(\nabla^2 I) = \text{Var}\left( \frac{\partial^2 I}{\partial x^2} + \frac{\partial^2 I}{\partial y^2} \right)$$
  - Threshold: Score $< 100.0$ triggers advisory blur warning.
- **Luminance / Brightness**: Mean grayscale luminance ($\mu$).
  - Underexposed / Dark: $\mu < 50$
  - Overexposed / Glare: $\mu > 215$
- **Contrast Dynamic Range**: Standard deviation of pixel luminance ($\sigma$).
  - Low Contrast: $\sigma < 22.0$
- **Resolution Assessment**: Minimum recommended label dimension $400 \times 400$ pixels.

> **Advisory Quality Standard**:
> Quality warnings are non-blocking advisory indicators intended to inform the inspector of potential OCR noise; they do not invalidate intake or inspection processing.

---

---

## Phase 4: Declaration Extraction & Normalization

The Declaration Extraction pipeline maps raw OCR text blocks into the 13 canonical Legal Metrology declaration types:

### Pipeline Flow:
```
Raw OCR Text + BBoxes
       │
       ▼
1. Candidate Pattern Matching (13 Type Regex & Keywords)
       │
       ▼
2. Domain Value Normalization (Currency, Metric Units, Dates, Contacts, Entities)
       │
       ▼
3. Multi-Factor Confidence Evaluation (OCR 30% + Keyword 30% + Format 25% + Context 15%)
       │
       ▼
4. Candidate Disambiguation & Ambiguity Detection
       │
       ▼
5. Traceable Persistence in `Declaration` Table (Linked to Scan & BBoxes)
```

### Supported Declarations:
- `PRODUCT_NAME`, `GENERIC_NAME`
- `NET_QUANTITY` (Normalized to standard metric units: `g`, `kg`, `ml`, `L`, `m`, `N`)
- `MRP` (Normalized to `₹ <amount> (Incl. of all taxes)`)
- `UNIT_SALE_PRICE` (Normalized to `₹ <amount> / <unit>`)
- `DATE_OF_MANUFACTURE`, `DATE_OF_PACKING` (Normalized to `MM/YYYY` or `DD/MM/YYYY`)
- `MANUFACTURER_DETAILS`, `PACKER_DETAILS`, `IMPORTER_DETAILS`, `COUNTRY_OF_ORIGIN`
- `CONSUMER_CARE` (Extracted phones, toll-free lines, emails, website)
- `OTHER` (Batch numbers, certifications)

---

## Statutory Screening Scope & Legal Notice

> [!IMPORTANT]
> **Statutory Scope Notice**:
> In accordance with Phase 3 and Phase 4 specifications, OCR output and extracted declarations represent automated evidence extraction.
> They serve as verifiable evidence capture and do **NOT** constitute a legal compliance determination or final statutory verdict. Legal rule evaluation, font-size verification, and compliance scoring are isolated to subsequent phases (Phase 5+).
