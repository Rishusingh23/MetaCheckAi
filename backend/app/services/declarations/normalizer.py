import re
from typing import List, Optional, Tuple

from app.services.declarations.models import (
    NormalizedContact,
    NormalizedDate,
    NormalizedPrice,
    NormalizedQuantity,
    NormalizedUSP,
)
from app.services.declarations.patterns import (
    COUNTRY_NAMES,
    REGEX_DATE,
    REGEX_EMAIL,
    REGEX_METRIC_QUANTITY,
    REGEX_MRP_AMOUNT,
    REGEX_PHONE,
    REGEX_USP,
)

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

UNIT_CANONICAL_MAP = {
    "kg": ("kg", "g", 1000.0),
    "kilogram": ("kg", "g", 1000.0),
    "kilograms": ("kg", "g", 1000.0),
    "g": ("g", "g", 1.0),
    "gm": ("g", "g", 1.0),
    "gms": ("g", "g", 1.0),
    "gram": ("g", "g", 1.0),
    "grams": ("g", "g", 1.0),
    "mg": ("mg", "g", 0.001),
    "milligram": ("mg", "g", 0.001),
    "milligrams": ("mg", "g", 0.001),
    "l": ("L", "ml", 1000.0),
    "ltr": ("L", "ml", 1000.0),
    "litre": ("L", "ml", 1000.0),
    "litres": ("L", "ml", 1000.0),
    "liter": ("L", "ml", 1000.0),
    "liters": ("L", "ml", 1000.0),
    "ml": ("ml", "ml", 1.0),
    "millilitre": ("ml", "ml", 1.0),
    "millilitres": ("ml", "ml", 1.0),
    "milliliter": ("ml", "ml", 1.0),
    "milliliters": ("ml", "ml", 1.0),
    "m": ("m", "m", 1.0),
    "meter": ("m", "m", 1.0),
    "meters": ("m", "m", 1.0),
    "metre": ("m", "m", 1.0),
    "metres": ("m", "m", 1.0),
    "cm": ("cm", "m", 0.01),
    "centimeter": ("cm", "m", 0.01),
    "centimetre": ("cm", "m", 0.01),
    "mm": ("mm", "m", 0.001),
    "sq m": ("sq m", "sq m", 1.0),
    "sq cm": ("sq cm", "sq m", 0.0001),
    "units": ("N", "N", 1.0),
    "unit": ("N", "N", 1.0),
    "pieces": ("N", "N", 1.0),
    "piece": ("N", "N", 1.0),
    "pcs": ("N", "N", 1.0),
    "n": ("N", "N", 1.0),
    "no": ("N", "N", 1.0),
    "nos": ("N", "N", 1.0),
}


def normalize_mrp(raw: str) -> Tuple[str, Optional[NormalizedPrice]]:
    """
    Extract and normalize Maximum Retail Price from raw text literal.
    Example: 'MRP: Rs. 149.00 (incl. of all taxes)' -> '₹149.00'
    """
    cleaned = raw.replace(",", ".")
    match = REGEX_MRP_AMOUNT.search(cleaned)
    if not match:
        # Fallback numeric extraction
        num_match = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", cleaned)
        if num_match:
            val = float(num_match.group(1))
            formatted = f"₹{val:.2f}"
            return formatted, NormalizedPrice(amount=val, currency="INR", raw_amount_string=num_match.group(1))
        return raw.strip(), None

    amt_str = match.group(1)
    try:
        amount = float(amt_str)
        is_inclusive = "incl" in raw.lower() or "tax" in raw.lower()
        formatted = f"₹{amount:.2f}"
        return formatted, NormalizedPrice(
            amount=amount,
            currency="INR",
            is_inclusive_of_all_taxes=is_inclusive,
            raw_amount_string=amt_str,
        )
    except ValueError:
        return raw.strip(), None


def normalize_net_quantity(raw: str) -> Tuple[str, Optional[NormalizedQuantity]]:
    """
    Extract and standardize metric Net Quantity.
    Example: '500g' -> '500 g', '1.5 KG' -> '1.5 kg'
    """
    match = REGEX_METRIC_QUANTITY.search(raw)
    if not match:
        return raw.strip(), None

    val_str, unit_raw = match.group(1), match.group(2)
    val_str = val_str.replace(",", ".")
    try:
        val = float(val_str)
        unit_key = unit_raw.lower().replace(".", "").strip()
        canonical_unit, base_unit, multiplier = UNIT_CANONICAL_MAP.get(
            unit_key, (unit_raw, unit_raw, 1.0)
        )
        standard_val = val * multiplier

        # Format cleanly (remove trailing .0 if integer)
        val_display = f"{val:g}"
        formatted = f"{val_display} {canonical_unit}"

        return formatted, NormalizedQuantity(
            value=val,
            unit=canonical_unit,
            standard_unit=base_unit,
            standard_value=standard_val,
            raw_unit_string=unit_raw,
        )
    except ValueError:
        return raw.strip(), None


def normalize_usp(raw: str) -> Tuple[str, Optional[NormalizedUSP]]:
    """
    Extract and standardize Unit Sale Price (USP).
    Example: 'Rs. 59.00 / kg' -> '₹59.00 / kg'
    """
    match = REGEX_USP.search(raw)
    if not match:
        return raw.strip(), None

    price_str, unit_raw = match.group(1), match.group(2)
    price_str = price_str.replace(",", ".")
    try:
        price_val = float(price_str)
        unit_key = unit_raw.lower().replace(".", "").strip()
        canonical_unit, _, _ = UNIT_CANONICAL_MAP.get(unit_key, (unit_raw, unit_raw, 1.0))
        formatted = f"₹{price_val:.2f} / {canonical_unit}"

        return formatted, NormalizedUSP(
            unit_price=price_val,
            currency="INR",
            unit=canonical_unit,
            raw_usp_string=raw.strip(),
        )
    except ValueError:
        return raw.strip(), None


def normalize_date(raw: str) -> Tuple[str, Optional[NormalizedDate]]:
    """
    Extract and standardize packaging or manufacturing dates.
    Example: '02/2026' -> '02/2026', 'Aug 2026' -> '08/2026'
    """
    match = REGEX_DATE.search(raw)
    if not match:
        return raw.strip(), None

    day_str, month_str, year_str = match.group(1), match.group(2), match.group(3)

    # Parse Month
    month_lower = month_str.lower()
    if month_lower in MONTH_MAP:
        month_val = MONTH_MAP[month_lower]
    else:
        try:
            month_val = int(month_str)
        except ValueError:
            return raw.strip(), None

    # Parse Year (handle 2-digit e.g. '26' -> 2026)
    try:
        year_val = int(year_str)
        if year_val < 100:
            year_val += 2000
    except ValueError:
        return raw.strip(), None

    day_val = int(day_str) if day_str else None

    if day_val:
        formatted = f"{day_val:02d}/{month_val:02d}/{year_val}"
        iso_str = f"{year_val}-{month_val:02d}-{day_val:02d}"
    else:
        formatted = f"{month_val:02d}/{year_val}"
        iso_str = f"{year_val}-{month_val:02d}"

    return formatted, NormalizedDate(
        day=day_val,
        month=month_val,
        year=year_val,
        iso_format=iso_str,
        raw_date_string=raw.strip(),
    )


def normalize_consumer_care(raw: str) -> Tuple[str, Optional[NormalizedContact]]:
    """
    Extract structured consumer care contact info (phones, emails, website).
    """
    phones = [p.strip() for p in REGEX_PHONE.findall(raw)]
    emails = [e.strip().lower() for e in REGEX_EMAIL.findall(raw)]
    toll_frees = [p for p in phones if p.startswith("1800")]

    website = None
    web_match = re.search(r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)\b", raw)
    if web_match:
        website = web_match.group(0)

    # Clean textual summary
    parts = []
    if phones:
        parts.append(f"Tel: {', '.join(phones)}")
    if emails:
        parts.append(f"Email: {', '.join(emails)}")
    if website:
        parts.append(f"Web: {website}")

    formatted = " | ".join(parts) if parts else raw.strip()

    return formatted, NormalizedContact(
        phones=phones,
        emails=emails,
        toll_free_numbers=toll_frees,
        address=raw.strip() if not parts else None,
        website=website,
    )


def normalize_country(raw: str) -> Tuple[str, str]:
    """
    Extract and canonicalize Country of Origin.
    Example: 'Made in INDIA' -> 'India'
    """
    lower = raw.lower()
    for country in COUNTRY_NAMES:
        if country in lower:
            # Title case canonical
            return country.title(), country.title()

    # Fallback: strip leading prefix
    cleaned = re.sub(r"^(?:country\s+of\s+origin|made\s+in|product\s+of|origin)[:\s]*", "", raw, flags=re.IGNORECASE).strip()
    return cleaned.title(), cleaned.title()


def clean_entity_text(raw: str, prefix_keywords: List[str]) -> str:
    """
    Strip leading keyword headers from entity name/address declarations.
    """
    pattern = r"^(?:" + "|".join(prefix_keywords) + r")[:\s-]*"
    cleaned = re.sub(pattern, "", raw.strip(), flags=re.IGNORECASE)
    # Remove leading colons or hyphens left over
    cleaned = re.sub(r"^[:\s-]+", "", cleaned).strip()
    return cleaned
