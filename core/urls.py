from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("products/", views.product_search, name="product_search"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("analytics/", views.analytics, name="analytics"),
]
