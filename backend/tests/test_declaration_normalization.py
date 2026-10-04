import pytest
from app.services.declarations.normalizer import (
    clean_entity_text,
    normalize_consumer_care,
    normalize_country,
    normalize_date,
    normalize_mrp,
    normalize_net_quantity,
    normalize_usp,
)
from app.services.declarations.patterns import MFG_ENTITY_KEYWORDS


def test_normalize_mrp_standard():
    formatted, price = normalize_mrp("MAXIMUM RETAIL PRICE (MRP): Rs. 295.00 (INCL. OF ALL TAXES)")
    assert formatted == "₹295.00"
    assert price is not None
    assert price.amount == 295.00
    assert price.currency == "INR"
    assert price.is_inclusive_of_all_taxes is True


def test_normalize_mrp_symbol_and_slash():
    formatted, price = normalize_mrp("MRP ₹ 120.50/- incl of taxes")
    assert formatted == "₹120.50"
    assert price is not None
    assert price.amount == 120.50


def test_normalize_net_quantity_grams():
    formatted, qty = normalize_net_quantity("NET QUANTITY: 500g")
    assert formatted == "500 g"
    assert qty is not None
    assert qty.value == 500.0
    assert qty.unit == "g"
    assert qty.standard_unit == "g"
    assert qty.standard_value == 500.0


def test_normalize_net_quantity_kilograms():
    formatted, qty = normalize_net_quantity("Net Wt. 1.5 KG")
    assert formatted == "1.5 kg"
    assert qty is not None
    assert qty.value == 1.5
    assert qty.unit == "kg"
    assert qty.standard_unit == "g"
    assert qty.standard_value == 1500.0


def test_normalize_net_quantity_millilitres():
    formatted, qty = normalize_net_quantity("Volume: 750 ml")
    assert formatted == "750 ml"
    assert qty is not None
    assert qty.value == 750.0
    assert qty.unit == "ml"
    assert qty.standard_unit == "ml"
    assert qty.standard_value == 750.0


def test_normalize_net_quantity_units():
    formatted, qty = normalize_net_quantity("Contents: 10 Units")
    assert formatted == "10 N"
    assert qty is not None
    assert qty.value == 10.0
    assert qty.unit == "N"


def test_normalize_usp_standard():
    formatted, usp = normalize_usp("UNIT SALE PRICE: Rs. 59.00 / kg")
    assert formatted == "₹59.00 / kg"
    assert usp is not None
    assert usp.unit_price == 59.0
    assert usp.unit == "kg"


def test_normalize_date_month_year():
    formatted, dt = normalize_date("DATE OF MANUFACTURE: 02/2026")
    assert formatted == "02/2026"
    assert dt is not None
    assert dt.month == 2
    assert dt.year == 2026
    assert dt.day is None


def test_normalize_date_month_name():
    formatted, dt = normalize_date("PKD: AUG 2026")
    assert formatted == "08/2026"
    assert dt is not None
    assert dt.month == 8
    assert dt.year == 2026


def test_normalize_date_full_day_month_year():
    formatted, dt = normalize_date("Manufactured on: 15/08/2025")
    assert formatted == "15/08/2025"
    assert dt is not None
    assert dt.day == 15
    assert dt.month == 8
    assert dt.year == 2025


def test_normalize_consumer_care():
    raw = "CUSTOMER CARE: 1800-111-2222 / SUPPORT@APEXFOODS.IN / WWW.APEXFOODS.IN"
    formatted, contact = normalize_consumer_care(raw)
    assert contact is not None
    assert "1800-111-2222" in contact.phones
    assert "support@apexfoods.in" in contact.emails
    assert "WWW.APEXFOODS.IN" in formatted or "support@apexfoods.in" in formatted


def test_normalize_country():
    formatted, country = normalize_country("COUNTRY OF ORIGIN: INDIA")
    assert formatted == "India"
    assert country == "India"


def test_clean_entity_text():
    cleaned = clean_entity_text("MANUFACTURED & PACKED BY: APEX FOODS INDIA PVT LTD", MFG_ENTITY_KEYWORDS)
    assert cleaned == "APEX FOODS INDIA PVT LTD"
