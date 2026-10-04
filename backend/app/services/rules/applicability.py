from datetime import datetime, timezone
from typing import List, Optional
from app.models.product import Product
from app.models.rule import RuleVersion


def normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to convert any datetime (aware or naive) to timezone-naive UTC for comparison."""
    if dt is None:
        return None
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def is_rule_version_temporally_valid(
    rule_version: RuleVersion,
    target_date: datetime,
) -> bool:
    """
    Check if a RuleVersion was active on the target date (e.g. date of inspection / packing).
    - active_from is inclusive (target_date >= active_from)
    - active_to is exclusive (target_date < active_to)
    """
    norm_target = normalize_datetime(target_date)
    norm_from = normalize_datetime(rule_version.active_from)
    norm_to = normalize_datetime(rule_version.active_to)

    if norm_from and norm_target and norm_target < norm_from:
        return False
    if norm_to and norm_target and norm_target >= norm_to:
        return False
    return True


def is_rule_version_applicable_to_product(
    rule_version: RuleVersion,
    product: Optional[Product],
) -> bool:
    """
    Check whether a RuleVersion applies to the product category and commodity attributes.
    """
    applicable_categories = rule_version.applicable_product_categories

    # If no category constraints specified, applies generally to all packaged commodities
    if not applicable_categories:
        return True

    # Check if category list contains wildcard
    if isinstance(applicable_categories, list):
        if "*" in applicable_categories or "ALL" in applicable_categories or "all" in applicable_categories:
            return True
        if not product or not product.category:
            # When product category is unknown, apply generally
            return True
        prod_cat = product.category.lower().strip()
        return any(c.lower().strip() == prod_cat for c in applicable_categories)

    if isinstance(applicable_categories, dict):
        categories_list = applicable_categories.get("categories", [])
        if "*" in categories_list or "ALL" in categories_list:
            return True
        if product and product.category:
            prod_cat = product.category.lower().strip()
            return any(c.lower().strip() == prod_cat for c in categories_list)

    return True


def is_rule_version_applicable_to_context(
    rule_version: RuleVersion,
    applicable_context: str = "PHYSICAL_PACKAGE",
    is_imported: bool = False,
    is_e_commerce: bool = False,
) -> bool:
    """
    Check whether a RuleVersion applies to the inspection context:
      - PHYSICAL_PACKAGE: Physical package inspection on retail shelf/depot.
      - E_COMMERCE_LISTING: Digital catalog / online marketplace product listing.
      - IMPORTED_PRODUCT: Packaged commodity originating outside India.
      - DOMESTIC_PRODUCT: Packaged commodity manufactured within India.
    """
    raw_contexts = rule_version.applicable_contexts

    # If no specific context specified, applies generally by default
    if not raw_contexts:
        return True

    context_list: List[str] = []
    if isinstance(raw_contexts, list):
        context_list = [str(c).upper().strip() for c in raw_contexts]
    elif isinstance(raw_contexts, dict):
        context_list = [str(c).upper().strip() for c in raw_contexts.get("contexts", [])]

    if not context_list or "*" in context_list or "ALL" in context_list:
        return True

    is_ecom_ctx = is_e_commerce or (str(applicable_context).upper().strip() == "E_COMMERCE_LISTING")

    # 1. Channel Filter (E-Commerce Listing vs. Physical Package)
    if is_ecom_ctx:
        # Rule applies exclusively to physical package inspections
        if "PHYSICAL_PACKAGE" in context_list and "E_COMMERCE_LISTING" not in context_list:
            return False
    else:
        # Physical package inspection:
        # If the rule requires E_COMMERCE_LISTING and does not include PHYSICAL_PACKAGE, return False.
        if "E_COMMERCE_LISTING" in context_list and "PHYSICAL_PACKAGE" not in context_list:
            return False

    # 2. Origin Filter (Imported vs. Domestic)
    if is_imported:
        # Rule applies exclusively to domestic products
        if "DOMESTIC_PRODUCT" in context_list and "IMPORTED_PRODUCT" not in context_list:
            return False
    else:
        # Domestic product:
        # If rule requires IMPORTED_PRODUCT and does not include DOMESTIC_PRODUCT, return False.
        if "IMPORTED_PRODUCT" in context_list and "DOMESTIC_PRODUCT" not in context_list:
            return False

    return True


def is_rule_version_applicable(
    rule_version: RuleVersion,
    target_date: datetime,
    product: Optional[Product] = None,
    applicable_context: str = "PHYSICAL_PACKAGE",
    is_imported: bool = False,
    is_e_commerce: bool = False,
) -> bool:
    """
    Comprehensive applicability check combining statutory active status,
    temporal validity, product category, and context applicability.
    """
    if not rule_version.rule or not rule_version.rule.is_active:
        return False

    if not is_rule_version_temporally_valid(rule_version, target_date):
        return False

    if not is_rule_version_applicable_to_product(rule_version, product):
        return False

    if not is_rule_version_applicable_to_context(
        rule_version,
        applicable_context=applicable_context,
        is_imported=is_imported,
        is_e_commerce=is_e_commerce,
    ):
        return False

    return True
