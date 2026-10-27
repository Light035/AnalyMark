from django.contrib import admin
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import DataSource, Marketplace, Offer, Product, SourceProduct
from .matching import reset_reviews


@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url", "is_active")
    search_fields = ("name",)
    readonly_fields = ("name", "is_active")

    def has_add_permission(self, request):
        return False  # init_marketplaces maintains the approved scope.

    def has_delete_permission(self, request, obj=None):
        return False  # Archive instead; histories/source identities are retained.


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("key", "marketplace", "is_demo", "status", "last_success_at", "stale_after_hours")
    # An existing source's identity/mode must not be reassigned through admin.
    readonly_fields = ("key", "marketplace", "provider", "is_demo", "status",
                       "last_attempt_at", "last_success_at", "last_error")
    fields = readonly_fields + ("stale_after_hours",)

    def has_add_permission(self, request):
        return False  # Explicit import creates sources with immutable namespaces.

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Operational state belongs to imports/workers, even if a form was loaded earlier.
        if change:
            obj.save(update_fields=["stale_after_hours"])
        else:
            super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "category")
    search_fields = ("name", "brand")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and {"name", "brand", "category"}.intersection(form.changed_data):
            reset_reviews(obj.offers.all())


class OfferReviewForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "marketplace" not in self.fields:
            return  # Imported identities are read-only in the admin form.
        markets = Marketplace.objects.active()
        if self.instance.pk:
            # Retain the current archive identity for inspection/editing, but do
            # not offer other archived marketplaces as new associations.
            markets = Marketplace.objects.filter(pk__in=markets.values("pk")) | Marketplace.objects.filter(pk=self.instance.marketplace_id)
        self.fields["marketplace"].queryset = markets
        self.fields["marketplace"].label_from_instance = lambda market: (
            str(market) if market.is_supported else _("%(marketplace)s · archived") % {"marketplace": market.name})

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and "product" in self.changed_data:
            if (cleaned.get("match_status") != Offer.MatchStatus.CONFIRMED
                    or not cleaned.get("match_notes", "").strip() or "match_notes" not in self.changed_data):
                raise forms.ValidationError(_("Changing the catalog product requires a confirmed manual review and explanation."))
        return cleaned


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    form = OfferReviewForm
    list_display = ("product", "marketplace", "seller_name", "price", "is_demo", "match_status", "match_reviewed_at")
    list_filter = ("marketplace", "is_demo", "match_status")
    search_fields = ("product__name", "seller_name")
    list_select_related = ("product", "marketplace")
    readonly_fields = ("match_reviewed_at", "match_reviewed_by", "source_identity")

    @admin.display(description=_("Source identity / evidence"))
    def source_identity(self, obj):
        if not obj or not obj.pk:
            return _("Not imported")
        try:
            imported = obj.import_record
        except Offer.import_record.RelatedObjectDoesNotExist:
            return _("Manually entered or demonstration record; no source IDs recorded.")
        product = SourceProduct.objects.filter(source=imported.source, product=obj.product).first()
        return f"{imported.source.key} | product: {product.external_id if product else 'unknown'} | offer: {imported.external_id} | {imported.source_url} | {imported.imported_at}"

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and hasattr(obj, "import_record"):
            fields += ["product", "marketplace", "is_demo"]
        return fields

    def save_model(self, request, obj, form, change):
        identity = {"product", "marketplace", "seller_name", "product_url", "is_demo"}
        identity_changed = change and bool(identity.intersection(form.changed_data))
        explicitly_reviewed = bool({"match_status", "match_notes"}.intersection(form.changed_data))
        if identity_changed and not explicitly_reviewed:
            obj.match_status = Offer.MatchStatus.UNREVIEWED
            obj.match_notes = "Product or offer identity changed; manual review is required again."
        if identity_changed or explicitly_reviewed:
            if obj.match_status == Offer.MatchStatus.UNREVIEWED:
                obj.match_reviewed_at = obj.match_reviewed_by = None
            else:
                obj.match_reviewed_at = timezone.now()
                obj.match_reviewed_by = request.user
        super().save_model(request, obj, form, change)
