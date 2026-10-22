from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe

from .comparison import listed_price_summary, sort_offers
from .forms import ProductSearchForm
from .history import observation_chart
from .models import Marketplace, Offer, PriceObservation, Product, WatchlistEntry


def _catalog_products():
    return Product.objects.annotate(
        offer_count=Count("offers"),
        demo_offer_count=Count("offers", filter=Q(offers__is_demo=True)),
    )


@require_safe
def dashboard(request):
    offers = Offer.objects.aggregate(total=Count("pk"), demo=Count("pk", filter=Q(is_demo=True)))
    observations = PriceObservation.objects.aggregate(
        total=Count("pk"), demo=Count("pk", filter=Q(is_demo=True)), latest=Max("observed_at")
    )
    metrics = {
        "products": Product.objects.count(), "marketplaces": Marketplace.objects.count(),
        "offers": offers["total"], "demo_offers": offers["demo"],
        "unverified_offers": offers["total"] - offers["demo"],
        "observations": observations["total"], "demo_observations": observations["demo"],
        "unverified_observations": observations["total"] - observations["demo"],
        "watchlist": WatchlistEntry.objects.filter(user=request.user).count() if request.user.is_authenticated else None,
    }
    return render(request, "core/dashboard.html", {
        "page_title": "Dashboard", "metrics": metrics,
        "latest_observation": observations["latest"], "products": _catalog_products()[:6],
    })


@require_safe
def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    offers = list(product.offers.select_related("product", "marketplace").order_by("marketplace__name", "seller_name", "pk"))
    observations = list(PriceObservation.objects.filter(offer__product_id=product.pk)
                        .select_related("offer__marketplace").order_by("observed_at", "pk"))
    saved = request.user.is_authenticated and WatchlistEntry.objects.filter(user=request.user, product=product).exists()
    return render(request, "core/product_detail.html", {
        "page_title": "Product analytics", "product": product, "offers": offers,
        "summary": listed_price_summary(offer.price for offer in offers),
        "observations": observations, "chart": observation_chart(observations),
        "is_saved": saved, "saved_product_ids": {product.pk} if saved else set(),
    })


@require_safe
def product_search(request):
    form = ProductSearchForm(request.GET)
    offers = Offer.objects.select_related("product", "marketplace").filter(price__gt=0)
    sort = "name"
    selected_product = None
    if form.is_valid():
        selected_product = form.cleaned_data["product"]
        if selected_product:
            offers = offers.filter(product=selected_product)
        query = form.cleaned_data["q"]
        if query:
            offers = offers.filter(Q(product__name__icontains=query) | Q(product__brand__icontains=query))
        if form.cleaned_data["marketplace"]:
            offers = offers.filter(marketplace=form.cleaned_data["marketplace"])
        sort = form.cleaned_data["sort"] or "name"
    else:
        offers = offers.none()
    results = sort_offers(list(offers), sort)
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(WatchlistEntry.objects.filter(
            user=request.user, product_id__in={offer.product_id for offer in results}
        ).values_list("product_id", flat=True))
    return render(
        request,
        "core/product_search.html",
        {
            "page_title": "Product Search",
            "form": form,
            "offers": results,
            "summary": listed_price_summary(offer.price for offer in results),
            "selected_product": selected_product,
            "saved_product_ids": saved_ids,
        },
    )


@login_required
@never_cache
@require_safe
def watchlist(request):
    return render(
        request, "core/watchlist.html",
        {"page_title": "Watchlist", "entries": WatchlistEntry.objects.filter(user=request.user).select_related("product")},
    )


@require_POST
def watchlist_add(request, product_id):
    if not request.user.is_authenticated:
        messages.info(request, "Log in, then save the product again.")
        return redirect_to_login(reverse("core:product_detail", args=[product_id]))
    product = get_object_or_404(Product, pk=product_id)
    _, created = WatchlistEntry.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f"Saved {product.name} to your Watchlist.")
    else:
        messages.info(request, "This product is already in your Watchlist.")
    return redirect("core:watchlist")


@require_POST
def watchlist_remove(request, product_id):
    if not request.user.is_authenticated:
        messages.info(request, "Log in, then retry removing the product from your Watchlist.")
        return redirect_to_login(reverse("core:watchlist"))
    deleted, _ = WatchlistEntry.objects.filter(user=request.user, product_id=product_id).delete()
    if deleted:
        messages.success(request, "Product removed from your Watchlist.")
    else:
        messages.error(request, "That product is not in your Watchlist.")
    return redirect("core:watchlist")


@require_safe
def price_history(request, offer_id):
    offer = get_object_or_404(Offer.objects.select_related("product", "marketplace"), pk=offer_id)
    return render(request, "core/price_history.html", {
        "page_title": "Price History", "offer": offer, "observations": offer.observations.all(),
    })


@require_safe
def analytics(request):
    return render(request, "core/analytics.html", {"page_title": "Analytics", "products": _catalog_products()})
