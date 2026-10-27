from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count, Exists, Max, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from django.utils import timezone
from django.utils.translation import gettext as _

from .comparison import ordered_offers, scoped_price_summaries
from .db import Casefold
from .pagination import paginate
from .forms import ComparisonScopeForm, DataSourceConfigureForm, ProductSearchForm
from .history import observation_chart
from .models import DataSource, Marketplace, Offer, PriceObservation, Product, WatchlistEntry
from .providers import SourceError
from .refreshing import enqueue_refresh


def _catalog_products():
    return Product.objects.active().annotate(
        offer_count=Count("offers", filter=Q(offers__marketplace__in=Marketplace.objects.active())),
        demo_offer_count=Count("offers", filter=Q(offers__is_demo=True, offers__marketplace__in=Marketplace.objects.active())),
    ).order_by("name", "pk")


def _data_sources():
    return DataSource.objects.filter(marketplace__in=Marketplace.objects.active()).select_related("marketplace").annotate(
        product_count=Count("products", distinct=True), offer_count=Count("offers", distinct=True)
    ).order_by("key", "pk")


def _source_summary():
    return DataSource.objects.filter(marketplace__in=Marketplace.objects.active()).aggregate(
        total=Count("pk"), errors=Count("pk", filter=Q(status=DataSource.Status.ERROR)),
        blocked=Count("pk", filter=Q(status=DataSource.Status.BLOCKED)),
        never=Count("pk", filter=Q(last_success_at__isnull=True)),
    )


def _scope_offers(offers, form):
    if not form.is_valid():
        return offers.none()
    if form.cleaned_data.get("marketplace"):
        offers = offers.filter(marketplace=form.cleaned_data["marketplace"])
    kind = form.cleaned_data.get("data_kind")
    return offers.filter(is_demo=(kind == "demo")) if kind else offers


def _history_charts(observations):
    groups = {}
    for observation in observations:
        key = (observation.offer.marketplace_id, observation.is_demo)
        groups.setdefault(key, []).append(observation)
    return [{"marketplace": rows[0].offer.marketplace.name, "is_demo": key[1],
             "chart": observation_chart(rows), "identifier": f"{key[0]}-{int(key[1])}"}
            for key, rows in groups.items()]


@require_safe
def dashboard(request):
    offers = Offer.objects.active().aggregate(
        total=Count("pk"), demo=Count("pk", filter=Q(is_demo=True)),
        imported=Count("pk", filter=Q(is_demo=False, import_record__isnull=False)),
    )
    observations = PriceObservation.objects.filter(offer__marketplace__in=Marketplace.objects.active()).aggregate(
        total=Count("pk"), demo=Count("pk", filter=Q(is_demo=True)), latest=Max("observed_at")
    )
    metrics = {
        "products": Product.objects.active().count(), "marketplaces": Marketplace.objects.active().count(),
        "offers": offers["total"], "demo_offers": offers["demo"],
        "unverified_offers": offers["total"] - offers["demo"],
        "observations": observations["total"], "demo_observations": observations["demo"],
        "unverified_observations": observations["total"] - observations["demo"],
        "watchlist": WatchlistEntry.objects.filter(user=request.user).count() if request.user.is_authenticated else None,
    }
    return render(request, "core/dashboard.html", {
        "page_title": _("Dashboard"), "metrics": metrics,
        "latest_observation": observations["latest"], "products": _catalog_products()[:6],
        "data_sources": _data_sources()[:5],
        "data_mix": {"demo": offers["demo"], "imported": offers["imported"],
                     "manual": offers["total"] - offers["demo"] - offers["imported"]},
        "source_summary": _source_summary(),
    })


@require_safe
def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    offers = product.offers.active().select_related("product", "marketplace", "import_record__source").order_by("marketplace__name", "seller_name", "pk")
    scope_form = ComparisonScopeForm(request.GET)
    offers = _scope_offers(offers, scope_form)
    summary, comparison_groups = scoped_price_summaries(offers)
    offer_page = paginate(request, offers, "offers_page")
    history = PriceObservation.objects.filter(offer_id__in=offers.values("pk"))
    if scope_form.is_valid() and scope_form.cleaned_data.get("data_kind"):
        history = history.filter(is_demo=(scope_form.cleaned_data["data_kind"] == "demo"))
    history_page = paginate(request, history
                            .exclude(offer__match_status=Offer.MatchStatus.REJECTED)
                            .select_related("offer__marketplace", "offer__import_record__source").order_by("observed_at", "pk"), "history_page", 50)
    observations = list(history_page.object_list)
    charts = _history_charts(observations)
    saved = request.user.is_authenticated and WatchlistEntry.objects.filter(user=request.user, product=product).exists()
    return render(request, "core/product_detail.html", {
        "page_title": _("Product analytics"), "product": product, "offers": list(offer_page.object_list),
        "offer_page": offer_page, "history_page": history_page,
        "summary": summary, "comparison_groups": comparison_groups, "scope_form": scope_form,
        "review_counts": offers.aggregate(unreviewed=Count("pk", filter=Q(match_status="unreviewed")),
                                          confirmed=Count("pk", filter=Q(match_status="confirmed")),
                                          rejected=Count("pk", filter=Q(match_status="rejected"))),
        "observations": observations, "charts": charts, "chart": charts[0]["chart"] if len(charts) == 1 else None,
        "is_saved": saved, "saved_product_ids": {product.pk} if saved else set(),
        "in_active_catalog": Product.objects.active().filter(pk=product.pk).exists(),
    })


@require_safe
def product_search(request):
    form = ProductSearchForm(request.GET)
    offers = Offer.objects.active().select_related("product", "marketplace", "import_record__source").filter(price__gt=0)
    sort = "name"
    selected_product = None
    valid = form.is_valid()
    if valid:
        selected_product = form.cleaned_data["product"]
        if selected_product:
            offers = offers.filter(product=selected_product)
        query = form.cleaned_data["q"]
        if query:
            offers = offers.alias(_search_name=Casefold("product__name"), _search_brand=Casefold("product__brand")).filter(
                Q(_search_name__contains=query.casefold()) | Q(_search_brand__contains=query.casefold()))
        sort = form.cleaned_data["sort"] or "name"
        if form.cleaned_data["review"]:
            offers = offers.filter(match_status=form.cleaned_data["review"])
    else:
        offers = offers.none()
    offers = _scope_offers(offers, form)
    summary, comparison_groups = scoped_price_summaries(offers)
    page = paginate(request, ordered_offers(offers, sort))
    results = list(page.object_list)
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(WatchlistEntry.objects.filter(
            user=request.user, product_id__in={offer.product_id for offer in results}
        ).values_list("product_id", flat=True))
    return render(
        request,
        "core/product_search.html",
        {
            "page_title": _("Product Search"),
            "form": form,
            "comparison_groups": comparison_groups,
            "offers": results,
            "summary": summary, "page_obj": page,
            "selected_product": selected_product,
            "saved_product_ids": saved_ids,
            "active_filters": {
                "query": form.cleaned_data.get("q", ""),
                "marketplace": form.cleaned_data.get("marketplace"),
                "data_kind": dict(form.fields["data_kind"].choices).get(form.cleaned_data.get("data_kind", "")),
                "sort": dict(form.fields["sort"].choices).get(sort),
                "review": dict(form.fields["review"].choices).get(form.cleaned_data.get("review", "")),
            } if valid else None,
        },
    )


@login_required
@never_cache
@require_safe
def watchlist(request):
    page = paginate(request, WatchlistEntry.objects.filter(user=request.user)
                    .select_related("product").annotate(
                        offer_count=Count("product__offers", filter=Q(product__offers__marketplace__in=Marketplace.objects.active())),
                        in_active_catalog=Exists(Product.objects.active().filter(pk=OuterRef("product_id"))),
                    ).order_by("-saved_at", "-pk").prefetch_related(Prefetch(
                        "product__offers", to_attr="watchlist_preview",
                        queryset=Offer.objects.active().select_related("marketplace")
                        .order_by("marketplace__name", "seller_name", "pk")[:3],
                    )))
    return render(
        request, "core/watchlist.html",
        {"page_title": _("Watchlist"), "entries": page.object_list, "page_obj": page},
    )


@require_POST
def watchlist_add(request, product_id):
    if not request.user.is_authenticated:
        messages.info(request, _("Log in, then save the product again."))
        return redirect_to_login(reverse("core:product_detail", args=[product_id]))
    product = get_object_or_404(Product.objects.active(), pk=product_id)
    entry, created = WatchlistEntry.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, _("Saved %(product)s to your Watchlist.") % {"product": product.name})
    else:
        messages.info(request, _("This product is already in your Watchlist."))
    return redirect("core:watchlist")


@require_POST
def watchlist_remove(request, product_id):
    if not request.user.is_authenticated:
        messages.info(request, _("Log in, then retry removing the product from your Watchlist."))
        return redirect_to_login(reverse("core:watchlist"))
    deleted, deleted_by_model = WatchlistEntry.objects.filter(user=request.user, product_id=product_id).delete()
    if deleted:
        messages.success(request, _("Product removed from your Watchlist."))
    else:
        messages.error(request, _("That product is not in your Watchlist."))
    return redirect("core:watchlist")


@require_safe
def price_history(request, offer_id):
    offer = get_object_or_404(Offer.objects.select_related("product", "marketplace", "import_record__source"), pk=offer_id)
    page = paginate(request, offer.observations.all(), per_page=50)
    return render(request, "core/price_history.html", {
        "page_title": _("Price History"), "offer": offer, "observations": page.object_list, "page_obj": page,
    })


@require_safe
def analytics(request):
    page = paginate(request, _catalog_products())
    return render(request, "core/analytics.html", {"page_title": _("Analytics"), "products": page.object_list, "page_obj": page})


@require_safe
def data_sources(request):
    page = paginate(request, _data_sources())
    return render(request, "core/data_sources.html", {
        "page_title": _("Data Sources"), "data_sources": page.object_list, "page_obj": page,
        "demo_offer_count": Offer.objects.active().filter(is_demo=True).count(),
        "marketplace_coverage": Marketplace.objects.active().annotate(
            product_count=Count("offers__product", distinct=True),
            offer_count=Count("offers"),
            demo_count=Count("offers", filter=Q(offers__is_demo=True)),
            supplied_count=Count("offers", filter=Q(offers__is_demo=False))),
        "source_summary": _source_summary(),
    })


@login_required
@permission_required("core.add_datasource", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def source_create(request):
    return _source_configuration(request)


@login_required
@permission_required("core.change_datasource", raise_exception=True)
@never_cache
@require_http_methods(["GET", "POST"])
def source_manage(request, source_id):
    return _source_configuration(request, get_object_or_404(DataSource, pk=source_id, marketplace__in=Marketplace.objects.active()))


def _source_configuration(request, source=None):
    if not request.user.is_staff:
        raise PermissionDenied
    form = DataSourceConfigureForm(request.POST if request.method == "POST" else None, instance=source)
    if request.method == "POST" and form.is_valid():
        configured = form.save(commit=False)
        schedule_changed = not source or bool({"refresh_enabled", "refresh_interval_minutes"}.intersection(form.changed_data))
        if not configured.refresh_enabled:
            configured.next_refresh_at = None
        elif schedule_changed:
            configured.next_refresh_at = timezone.now()
        if source:
            fields = ["refresh_enabled", "refresh_interval_minutes", "stale_after_hours"]
            if schedule_changed or not configured.refresh_enabled:
                fields.append("next_refresh_at")
            # Do not overwrite worker status, attempts or successes from a stale form instance.
            configured.save(update_fields=fields)
        else:
            configured.save()
        messages.success(request, _("Source configuration saved. Kaspi acquisition remains blocked until approved access is implemented."))
        return redirect("core:source_manage", source_id=configured.pk)
    runs = source.refresh_runs.all()[:10] if source else []
    return render(request, "core/source_manage.html", {"page_title": _("Configure refresh"), "form": form,
                                                       "source": source, "runs": runs})


@login_required
@permission_required("core.change_datasource", raise_exception=True)
@never_cache
@require_POST
def source_refresh(request, source_id):
    if not request.user.is_staff:
        raise PermissionDenied
    source = get_object_or_404(DataSource, pk=source_id, marketplace__in=Marketplace.objects.active())
    try:
        run, created = enqueue_refresh(source.pk, requested_by=request.user)
    except SourceError:
        messages.error(request, _("This source cannot be refreshed automatically. CSV and demo loading use explicit local commands."))
    else:
        messages.info(request, _("Refresh queued. A running worker is required; reload this page to see the actual outcome.") if created
                      else _("A refresh is already queued or running for this source."))
    return redirect("core:source_manage", source_id=source.pk)
