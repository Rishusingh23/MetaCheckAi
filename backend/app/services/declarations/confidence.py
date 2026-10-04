from typing import Tuple


def calculate_extraction_confidence(
    ocr_confidence: float,
    has_explicit_keyword: bool,
    has_valid_format: bool,
    has_contextual_indicators: bool = False,
    is_ambiguous: bool = False,
) -> Tuple[float, str]:
    """
    Compute transparent multi-factor confidence score for an extracted declaration:
    - Base OCR token confidence (30% weight)
    - Explicit Legal Metrology keyword presence (30% weight)
    - Structural format / regular expression validity (25% weight)
    - Surrounding contextual indicators (15% weight)
    """
    # 1. OCR score (0.0 to 0.30)
    ocr_score = max(0.0, min(1.0, ocr_confidence)) * 0.30

    # 2. Keyword score (0.0 or 0.30)
    kw_score = 0.30 if has_explicit_keyword else 0.10

    # 3. Format validity (0.0 or 0.25)
    fmt_score = 0.25 if has_valid_format else 0.05

    # 4. Contextual score (0.0 to 0.15)
    ctx_score = 0.15 if has_contextual_indicators else 0.05

    raw_total = ocr_score + kw_score + fmt_score + ctx_score

    if is_ambiguous:
        raw_total *= 0.80  # 20% ambiguity deduction

    final_score = max(0.05, min(0.99, raw_total))

    # Construct human-readable rationale
    rationale_parts = []
    if final_score >= 0.85:
        level = "High"
    elif final_score >= 0.70:
        level = "Moderate"
    else:
        level = "Low"

    if has_explicit_keyword:
        rationale_parts.append("explicit keyword match")
    else:
        rationale_parts.append("heuristic entity pattern")

    if has_valid_format:
        rationale_parts.append("valid statutory format")

    if has_contextual_indicators:
        rationale_parts.append("context verified")

    rationale_parts.append(f"OCR confidence {round(ocr_confidence * 100)}%")

    if is_ambiguous:
        rationale_parts.append("ambiguous candidates detected")

    rationale = f"{level}: {', '.join(rationale_parts)}."

    return round(final_score, 4), rationale
