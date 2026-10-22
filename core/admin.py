from django.contrib import admin

from .models import Marketplace, Offer, Product


@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category")
    search_fields = ("name", "brand")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("product", "marketplace", "seller_name", "price", "is_demo")
    list_filter = ("marketplace", "is_demo")
    search_fields = ("product__name", "seller_name")
    list_select_related = ("product", "marketplace")
