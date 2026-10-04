import re
from typing import Dict, List, Pattern

# Common keyword prefix patterns for Legal Metrology declarations

MRP_KEYWORDS: List[str] = [
    r"maximum\s+retail\s+price",
    r"max\.?\s+retail\s+price",
    r"m\.?r\.?p\.?",
    r"mrp",
]

NET_QTY_KEYWORDS: List[str] = [
    r"net\s+quantity",
    r"net\s+qty\.?",
    r"net\s+weight",
    r"net\s+wt\.?",
    r"net\s+content[s]?",
    r"n\.?q\.?",
    r"quantity",
    r"qty\.?",
]

USP_KEYWORDS: List[str] = [
    r"unit\s+sale\s+price",
    r"unit\s+price",
    r"u\.?s\.?p\.?",
    r"usp",
]

MFD_KEYWORDS: List[str] = [
    r"date\s+of\s+manufacture",
    r"date\s+of\s+mfg\.?",
    r"manufactured\s+on",
    r"manufactured",
    r"mfd\s+on",
    r"mfg\s+on",
    r"mfd\.?",
    r"mfg\.?",
]

PKD_KEYWORDS: List[str] = [
    r"date\s+of\s+packing",
    r"date\s+of\s+packaging",
    r"date\s+of\s+pkg\.?",
    r"packed\s+on",
    r"packaging\s+date",
    r"pkd\s+on",
    r"packed",
    r"pkd\.?",
]

MFG_ENTITY_KEYWORDS: List[str] = [
    r"manufactured\s+(&|and)\s+packed\s+by",
    r"manufactured\s+(&|and)\s+marketed\s+by",
    r"manufactured\s+by",
    r"mfd\.?\s+(&|and)\s+pkd\.?\s+by",
    r"mfd\.?\s+by",
    r"mfg\.?\s+by",
    r"manufacturer",
]

PACKER_ENTITY_KEYWORDS: List[str] = [
    r"packed\s+by",
    r"pkd\.?\s+by",
    r"repacked\s+by",
    r"packer",
]

IMPORTER_ENTITY_KEYWORDS: List[str] = [
    r"imported\s+(&|and)\s+marketed\s+by",
    r"imported\s+by",
    r"imp\.?\s+by",
    r"importer",
]

COUNTRY_KEYWORDS: List[str] = [
    r"country\s+of\s+origin",
    r"country\s+of\s+manufacture",
    r"made\s+in",
    r"product\s+of",
    r"origin",
]

CONSUMER_CARE_KEYWORDS: List[str] = [
    r"consumer\s+care",
    r"customer\s+care",
    r"customer\s+service",
    r"customer\s+support",
    r"consumer\s+feedback",
    r"for\s+feedback\s*(/|or)?\s*queries",
    r"for\s+complaints",
    r"care\s+cell",
    r"helpline",
    r"toll\s+free",
]

GENERIC_NAME_KEYWORDS: List[str] = [
    r"name\s+of\s+(the\s+)?commodity",
    r"generic\s+name",
    r"common\s+name",
    r"commodity",
    r"product\s+name",
]

# Comprehensive Regular Expression Patterns

REGEX_MRP_AMOUNT: Pattern = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*)?([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/-\s*)?"
    r"(?:\(?(?:incl\.?|inclusive)\s*(?:of)?\s*(?:all)?\s*(?:taxes|tax)?\)?)?",
    re.IGNORECASE,
)

REGEX_METRIC_QUANTITY: Pattern = re.compile(
    r"\b([0-9]+(?:[.,][0-9]+)?)\s*"
    r"(kg|kilogram[s]?|g|gm|gms|gram[s]?|mg|milligram[s]?|"
    r"l|ltr|litre[s]?|liter[s]?|ml|millilitre[s]?|milliliter[s]?|"
    r"m|meter[s]?|metre[s]?|cm|centimeter[s]?|centimetre[s]?|mm|"
    r"sq\.?\s*m|sq\.?\s*cm|units?|pieces?|pcs?|nos?|n)\b",
    re.IGNORECASE,
)

REGEX_USP: Pattern = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*)?([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/|per)\s*"
    r"(kg|g|gm|mg|l|ltr|ml|piece|unit|pcs?|n|meter|m)\b",
    re.IGNORECASE,
)

REGEX_DATE: Pattern = re.compile(
    r"\b(?:(0[1-9]|[12][0-9]|3[01])[-/.\s]+)?"  # Optional Day
    r"(0[1-9]|1[0-2]|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[-/.\s,]+"
    r"((?:19|20)?(?:[0-9]{2}))\b",  # Year (e.g. 2026, 26, 1999)
    re.IGNORECASE,
)

REGEX_PHONE: Pattern = re.compile(
    r"\b(?:1800[- ]?[0-9]{3}[- ]?[0-9]{3,4}|(?:\+?91[- ]?)?[6-9][0-9]{4}[- ]?[0-9]{5}|[0-9]{3,5}[- ][0-9]{6,8})\b"
)

REGEX_EMAIL: Pattern = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

REGEX_PINCODE: Pattern = re.compile(
    r"\b(?:[1-9][0-9]{2}\s?[0-9]{3})\b"
)

COUNTRY_NAMES: List[str] = [
    "india", "china", "vietnam", "thailand", "indonesia", "bangladesh",
    "sri lanka", "germany", "japan", "united states", "usa", "uk",
    "united kingdom", "italy", "france", "switzerland", "malaysia",
    "singapore", "taiwan", "korea", "south korea", "turkey", "spain",
]
