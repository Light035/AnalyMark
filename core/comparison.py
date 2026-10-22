"""Decimal-only statistics and sorting for the small MVP offer set."""
from decimal import Decimal, ROUND_HALF_UP
from statistics import median


def listed_price_summary(prices):
    valid_prices = [p for p in prices if p is not None and p.is_finite() and p > 0]
    if not valid_prices:
        return dict(count=0, minimum=None, maximum=None, average=None, median=None)
    cents = Decimal("0.01")
    return {
        "count": len(valid_prices),
        "minimum": min(valid_prices),
        "maximum": max(valid_prices),
        "average": (sum(valid_prices, Decimal("0")) / len(valid_prices)).quantize(cents, rounding=ROUND_HALF_UP),
        "median": median(valid_prices).quantize(cents, rounding=ROUND_HALF_UP),
    }


def sort_offers(offers, sort):
    descending = sort.endswith("_desc")
    field = sort.removesuffix("_desc")
    if field == "total":
        known = [offer for offer in offers if offer.total_buyer_cost is not None]
        unknown = [offer for offer in offers if offer.total_buyer_cost is None]
        return sorted(known, key=lambda offer: offer.total_buyer_cost, reverse=descending) + unknown
    if field == "price":
        return sorted(offers, key=lambda offer: offer.price, reverse=descending)
    return sorted(offers, key=lambda offer: offer.product.name.casefold(), reverse=descending)
