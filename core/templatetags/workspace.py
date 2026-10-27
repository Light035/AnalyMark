from django import template

register = template.Library()


@register.filter
def marketplace_style(marketplace):
    """Allowlisted presentation tokens; never interpolate names into CSS paths."""
    from core.marketplaces import MARKETPLACES
    return next((key for key, name, _ in MARKETPLACES if name == getattr(marketplace, "name", marketplace)), "archive")


@register.inclusion_tag("core/includes/marketplace_navigation.html", takes_context=True)
def marketplace_navigation(context):
    from core.marketplaces import APPROVED_NAMES
    from core.models import Marketplace
    markets = sorted(Marketplace.objects.active(), key=lambda market: APPROVED_NAMES.index(market.name))
    return {"markets": markets, "request": context["request"]}


@register.filter
def marketplace_order(markets):
    from core.marketplaces import APPROVED_NAMES
    return sorted(markets, key=lambda market: APPROVED_NAMES.index(market.name))


@register.simple_tag(takes_context=True)
def page_link(context, parameter, number, anchor=""):
    query = context["request"].GET.copy()
    query[parameter] = str(number)
    return "?" + query.urlencode() + ("#" + anchor if anchor else "")
