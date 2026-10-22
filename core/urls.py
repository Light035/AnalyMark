from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("products/", views.product_search, name="product_search"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("watchlist/", views.watchlist, name="watchlist"),
    path("watchlist/add/<int:product_id>/", views.watchlist_add, name="watchlist_add"),
    path("watchlist/remove/<int:product_id>/", views.watchlist_remove, name="watchlist_remove"),
    path("offers/<int:offer_id>/history/", views.price_history, name="price_history"),
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="registration/login.html", extra_context={"page_title": "Log in"}
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("analytics/", views.analytics, name="analytics"),
]
