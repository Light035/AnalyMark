from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def dashboard(request):
    return render(request, "core/dashboard.html", {"page_title": "Dashboard"})


@require_safe
def product_search(request):
    return render(
        request,
        "core/placeholder.html",
        {
            "page_title": "Product Search",
            "eyebrow": "Discover and compare",
            "heading": "Find the right product. Compare with confidence.",
            "description": "Kaspi.kz is our first marketplace focus. Product search and offer comparison are planned for the next stage.",
            "empty_title": "Product search is coming next",
            "empty_description": "No product catalog or marketplace data source is connected. There are no searchable offers yet.",
            "planned_features": [
                ("Comparable products", "Review model, variant, and bundle details before comparing offers."),
                ("Transparent buyer prices", "See discounts, buyer delivery, and totals when the required information is available."),
                ("Visible evidence", "Check sources, observation times, and warnings for missing data or uncertain matches."),
            ],
        },
    )


@require_safe
def watchlist(request):
    return render(
        request,
        "core/placeholder.html",
        {
            "page_title": "Watchlist",
            "eyebrow": "Keep products in view",
            "heading": "A place for products that matter to you.",
            "description": "The watchlist will bring saved products together for your next pricing review.",
            "empty_title": "Your watchlist starts in a future update",
            "empty_description": "Saving products and watchlist storage are not implemented yet. No saved-product records are being collected.",
            "planned_features": [
                ("Save a product", "Keep selected products available for a later review."),
                ("Return to the comparison", "Open a saved product and inspect its available competitor offers."),
                ("Review data freshness", "See when offers were observed and which information is unavailable."),
            ],
        },
    )


@require_safe
def analytics(request):
    return render(
        request,
        "core/placeholder.html",
        {
            "page_title": "Analytics",
            "eyebrow": "Understand your position",
            "heading": "Make room for a more informed pricing decision.",
            "description": "Benchmarks and seller inputs will add context to comparable competitor offers.",
            "empty_title": "No benchmarks to calculate yet",
            "empty_description": "Price statistics, product cost inputs, and minimum margin calculations are not implemented. No prices or recommendations are shown.",
            "planned_features": [
                ("Price benchmarks", "Review minimum, average, and median prices with a clear comparison basis."),
                ("Your costs and margin", "Enter seller product cost and desired margin separately from buyer delivery fees."),
                ("You make the decision", "Use the information to review your price. Automatic repricing is outside the MVP scope."),
            ],
        },
    )
