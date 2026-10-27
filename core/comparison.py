"""Decimal-only statistics and sorting for the small MVP offer set."""
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from django.db.models import BigIntegerField, Case, Count, F, Max, Min, Q, Sum, Value, When
from django.db.models.functions import Cast, Round

from .db import Casefold


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


def cents(field):
    # Round before integer conversion to avoid SQLite floating-point truncation.
    return Cast(Round(F(field) * 100, precision=0), BigIntegerField())


def queryset_price_summary(offers):
    """Exact integer-cent SQL aggregates; median fetches at most two scalars.

    Scope is the full filtered set excluding explicitly rejected associations,
    independently of pagination. Unreviewed associations are provisional.
    """
    eligible = offers.filter(price__gt=0).exclude(match_status="rejected").order_by().annotate(_cents=cents("price"))
    values = eligible.aggregate(count=Count("pk"), minimum=Min("_cents"), maximum=Max("_cents"), total=Sum("_cents"))
    count = values["count"]
    if not count:
        return dict(count=0, minimum=None, maximum=None, average=None, median=None)
    middle = list(eligible.order_by("_cents", "pk").values_list("_cents", flat=True)[(count - 1) // 2:count // 2 + 1])
    money = lambda value: (Decimal(value) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return dict(count=count, minimum=money(values["minimum"]), maximum=money(values["maximum"]),
                average=money(Decimal(values["total"]) / count), median=money(Decimal(sum(middle)) / len(middle)))


def ordered_offers(offers, sort):
    """SQL sorting before LIMIT/OFFSET, with stable tie-breaks and unknowns last."""
    offers = offers.annotate(_name=Casefold("product__name"))
    ties = ["_name", "marketplace__name", "seller_name", "pk"]
    if sort in ("price", "price_desc"):
        return offers.order_by("-price" if sort.endswith("_desc") else "price", *ties)
    if sort in ("total", "total_desc"):
        known = Q(price__gt=0, delivery_cost__isnull=False, delivery_cost__gte=0,
                  discount__isnull=False, discount__gte=0, discount__lte=F("price"))
        offers = offers.annotate(_buyer_cents=Case(
            When(known, then=cents("price") - cents("discount") + cents("delivery_cost")),
            default=Value(None), output_field=BigIntegerField(),
        ))
        order = F("_buyer_cents").desc(nulls_last=True) if sort.endswith("_desc") else F("_buyer_cents").asc(nulls_last=True)
        return offers.order_by(order, *ties)
    return offers.order_by("-_name" if sort == "name_desc" else "_name", "marketplace__name", "seller_name", "pk")


def scoped_price_summaries(offers):
    """Never aggregate fictional prices with supplied prices or different markets.

    Only distinct marketplace/provenance keys are materialized, not the catalog.
    The combined count is informational; combined monetary benchmarks are absent.
    """
    groups = []
    scopes = offers.order_by("marketplace__name", "is_demo").values(
        "marketplace_id", "marketplace__name", "is_demo").distinct()
    for scope in scopes:
        summary = queryset_price_summary(offers.filter(
            marketplace_id=scope["marketplace_id"], is_demo=scope["is_demo"]))
        groups.append({"marketplace": scope["marketplace__name"], "is_demo": scope["is_demo"], "summary": summary})
    combined = dict(count=sum(g["summary"]["count"] for g in groups), minimum=None, maximum=None, average=None, median=None)
    return (groups[0]["summary"] if len(groups) == 1 else combined), groups
