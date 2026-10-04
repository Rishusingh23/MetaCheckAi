"""
Realistic Packaged Product Label Image Generator for MetaCheck AI.
Generates controlled, legally grounded synthetic packaged commodity label images
using Pillow across 5 distinct compliance evaluation scenarios:
  1. Sample A: Compliant Potato Wafers (All mandatory declarations present)
  2. Sample B: Missing Manufacturer Address (Violates Rule 6(1)(a))
  3. Sample C: Non-Compliant MRP without Tax Clause (Violates Rule 6(1)(e))
  4. Sample D: Non-Metric Quantity in Lbs/Oz (Violates Rule 13 / Sched III)
  5. Sample E: Blurry / Low Quality Label (Triggers Advisory Review state)
"""
import io
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageFont, PngImagePlugin


def _get_font(size: int) -> ImageFont.ImageFont:
    """Load default Pillow font scaled or fallback to default."""
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("Helvetica.ttc", size)
        except Exception:
            return ImageFont.load_default()


def generate_compliant_label() -> Tuple[bytes, Dict[str, str]]:
    """
    Generate Sample A: 100% Compliant Packaged Commodity Label.
    Product: Himalayan Crunch Potato Wafers (200 g, MRP ₹ 40.00 incl. of all taxes)
    """
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(15, 15), (785, 585)], outline=(30, 41, 59), width=3)
    draw.rectangle([(20, 20), (780, 80)], fill=(15, 23, 42))
    draw.text((30, 35), "HIMALAYAN CRUNCH — POTATO WAFERS", fill=(255, 255, 255), font=_get_font(22))
    draw.text((630, 40), "READY TO EAT", fill=(56, 189, 248), font=_get_font(14))

    lines = [
        ("COMMON / GENERIC NAME:", "Fried Potato Chips (Classic Salted)"),
        ("NET QUANTITY:", "200 g"),
        ("MAXIMUM RETAIL PRICE:", "₹ 40.00 (Inclusive of all taxes)"),
        ("UNIT SALE PRICE (USP):", "₹ 0.20 / g"),
        ("MONTH & YEAR OF PKG:", "08/2026"),
        ("BEST BEFORE:", "6 Months from packaging date"),
        ("MANUFACTURED & PACKED BY:", "Himalayan Foods Pvt. Ltd., Plot 42, Industrial Area, Solan, H.P. - 173212"),
        ("CONSUMER CARE DETAILS:", "Manager, Customer Care: 1800-111-222 | care@himalayanfoods.in"),
        ("COUNTRY OF ORIGIN:", "India"),
    ]

    y = 100
    for label, val in lines:
        draw.text((40, y), label, fill=(15, 23, 42), font=_get_font(14))
        draw.text((300, y), val, fill=(30, 58, 138), font=_get_font(15))
        draw.line([(40, y + 26), (760, y + 26)], fill=(226, 232, 240), width=1)
        y += 45

    draw.rectangle([(40, 520), (320, 565)], outline=(100, 116, 139), width=1)
    for bx in range(50, 310, 6):
        draw.line([(bx, 525), (bx, 550)], fill=(0, 0, 0), width=2)
    draw.text((90, 552), "8901234567890 (GTIN-13)", fill=(71, 85, 105), font=_get_font(10))

    meta_png = PngImagePlugin.PngInfo()
    text_lines = [f"{label} {val}" for label, val in lines]
    meta_png.add_text("label_text", "\n".join(text_lines))

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta_png)
    return buf.getvalue(), {
        "name": "Himalayan Crunch Potato Wafers",
        "brand": "Himalayan Crunch",
        "category": "Food & Snacks",
        "barcode": "8901234567890",
        "expected_result": "COMPLIANT",
    }


def generate_missing_manufacturer_label() -> Tuple[bytes, Dict[str, str]]:
    """
    Generate Sample B: Label missing Manufacturer/Packer name and address.
    Product: Royal Darjeeling Leaf Tea (250 g, Violates Rule 6(1)(a))
    """
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(15, 15), (785, 585)], outline=(30, 41, 59), width=3)
    draw.rectangle([(20, 20), (780, 80)], fill=(20, 83, 45))
    draw.text((30, 35), "ROYAL DARJEELING — PREMIUM LEAF TEA", fill=(255, 255, 255), font=_get_font(22))

    lines = [
        ("GENERIC COMMODITY:", "Black Tea Leaves (Orthodox Blend)"),
        ("NET QUANTITY:", "250 g"),
        ("MAXIMUM RETAIL PRICE:", "₹ 220.00 (Incl. of all taxes)"),
        ("UNIT SALE PRICE:", "₹ 0.88 / g"),
        ("MONTH & YEAR OF PKG:", "07/2026"),
        ("CONSUMER CARE:", "Customer Support: 1800-444-555 | help@darjeelingtea.in"),
        ("COUNTRY OF ORIGIN:", "India"),
    ]

    y = 110
    for label, val in lines:
        draw.text((40, y), label, fill=(15, 23, 42), font=_get_font(14))
        draw.text((300, y), val, fill=(20, 83, 45), font=_get_font(15))
        draw.line([(40, y + 28), (760, y + 28)], fill=(226, 232, 240), width=1)
        y += 50

    meta_png = PngImagePlugin.PngInfo()
    text_lines = [f"{label} {val}" for label, val in lines]
    meta_png.add_text("label_text", "\n".join(text_lines))

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta_png)
    return buf.getvalue(), {
        "name": "Royal Darjeeling Premium Leaf Tea",
        "brand": "Royal Darjeeling",
        "category": "Beverages",
        "barcode": "8909876543210",
        "expected_result": "POTENTIAL_NON_COMPLIANCE",
        "expected_violation": "VIOL_PCR_2011_RULE_6_1_A",
    }


def generate_non_compliant_mrp_label() -> Tuple[bytes, Dict[str, str]]:
    """
    Generate Sample C: Label with invalid MRP lacking 'inclusive of all taxes' clause.
    Product: Pure Almond Beverage (1 L, Violates Rule 6(1)(e))
    """
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(15, 15), (785, 585)], outline=(30, 41, 59), width=3)
    draw.rectangle([(20, 20), (780, 80)], fill=(67, 56, 202))
    draw.text((30, 35), "PURE ALMOND — NUTRITIOUS DRINK", fill=(255, 255, 255), font=_get_font(22))

    lines = [
        ("COMMODITY:", "Almond Milk Drink"),
        ("NET QUANTITY:", "1 L"),
        ("MAXIMUM RETAIL PRICE:", "MRP Rs. 150.00"),  # Missing mandatory 'inclusive of all taxes'
        ("UNIT SALE PRICE:", "₹ 0.15 / ml"),
        ("MONTH & YEAR OF PKG:", "09/2026"),
        ("MANUFACTURED BY:", "PureDairy Ltd., GIDC Estate, Anand, Gujarat - 388001"),
        ("CONSUMER CARE:", "Toll Free: 1800-999-000 | care@puredairy.in"),
        ("COUNTRY OF ORIGIN:", "India"),
    ]

    y = 100
    for label, val in lines:
        draw.text((40, y), label, fill=(15, 23, 42), font=_get_font(14))
        draw.text((300, y), val, fill=(67, 56, 202), font=_get_font(15))
        draw.line([(40, y + 26), (760, y + 26)], fill=(226, 232, 240), width=1)
        y += 45

    meta_png = PngImagePlugin.PngInfo()
    text_lines = [f"{label} {val}" for label, val in lines]
    meta_png.add_text("label_text", "\n".join(text_lines))

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta_png)
    return buf.getvalue(), {
        "name": "Pure Almond Nutritious Drink",
        "brand": "Pure Almond",
        "category": "Dairy & Alternatives",
        "barcode": "8905556667778",
        "expected_result": "POTENTIAL_NON_COMPLIANCE",
        "expected_violation": "VIOL_PCR_2011_RULE_6_1_E",
    }


def generate_non_metric_quantity_label() -> Tuple[bytes, Dict[str, str]]:
    """
    Generate Sample D: Label using non-standard non-metric units (LBS / OZ).
    Product: Organic Basmati Rice (2 LBS, Violates Rule 13 / Sched III)
    """
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(15, 15), (785, 585)], outline=(30, 41, 59), width=3)
    draw.rectangle([(20, 20), (780, 80)], fill=(161, 98, 7))
    draw.text((30, 35), "ORGANIC BASMATI — ROYAL GRAIN RICE", fill=(255, 255, 255), font=_get_font(22))

    lines = [
        ("COMMODITY:", "Traditional Basmati Rice"),
        ("NET QUANTITY:", "Net Wt. 2 LBS (32 OZ)"),  # Non-metric violation! Must be in g / kg
        ("MAXIMUM RETAIL PRICE:", "₹ 350.00 (Incl. of all taxes)"),
        ("UNIT SALE PRICE:", "₹ 0.38 / g"),
        ("MONTH & YEAR OF PKG:", "06/2026"),
        ("PACKED & MARKETED BY:", "Agro Heritage Farms, Karnal, Haryana - 132001"),
        ("CONSUMER CARE:", "Helpline: 1800-222-333 | contact@agrofarms.in"),
        ("COUNTRY OF ORIGIN:", "India"),
    ]

    y = 100
    for label, val in lines:
        draw.text((40, y), label, fill=(15, 23, 42), font=_get_font(14))
        draw.text((300, y), val, fill=(161, 98, 7), font=_get_font(15))
        draw.line([(40, y + 26), (760, y + 26)], fill=(226, 232, 240), width=1)
        y += 45

    meta_png = PngImagePlugin.PngInfo()
    text_lines = [f"{label} {val}" for label, val in lines]
    meta_png.add_text("label_text", "\n".join(text_lines))

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta_png)
    return buf.getvalue(), {
        "name": "Organic Basmati Royal Grain Rice",
        "brand": "Organic Basmati",
        "category": "Grains & Staples",
        "barcode": "8907778889990",
        "expected_result": "POTENTIAL_NON_COMPLIANCE",
        "expected_violation": "VIOL_PCR_2011_RULE_13",
    }


def generate_blurry_review_label() -> Tuple[bytes, Dict[str, str]]:
    """
    Generate Sample E: Heavily blurred label image to test image-quality-to-review pipeline.
    Should trigger is_blurry=True and result in REVIEW / INSUFFICIENT EVIDENCE.
    """
    img = Image.new("RGB", (800, 600), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    draw.rectangle([(20, 20), (780, 80)], fill=(71, 85, 105))
    draw.text((30, 35), "GOLDEN HARVEST COOKIES", fill=(255, 255, 255), font=_get_font(22))
    draw.text((40, 150), "Net Quantity: 150 g", fill=(100, 100, 100), font=_get_font(12))
    draw.text((40, 220), "MRP: Rs. 30 (All taxes incl.)", fill=(100, 100, 100), font=_get_font(12))
    draw.text((40, 290), "Manufactured by: Bakery Products Ltd", fill=(100, 100, 100), font=_get_font(12))

    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=8.0))

    buf = io.BytesIO()
    blurred_img.save(buf, format="JPEG", quality=40)
    return buf.getvalue(), {
        "name": "Golden Harvest Butter Cookies",
        "brand": "Golden Harvest",
        "category": "Bakery",
        "barcode": "8903334445556",
        "expected_result": "REVIEW_REQUIRED",
    }

