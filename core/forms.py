from django import forms
from django.utils.translation import gettext_lazy as _

from .models import DataSource, Marketplace, Offer, Product

SORT_CHOICES = [
    ("name", _("Product name: A–Z")),
    ("name_desc", _("Product name: Z–A")),
    ("price", _("Listed price: low to high")),
    ("price_desc", _("Listed price: high to low")),
    ("total", _("Buyer total: low to high")),
    ("total_desc", _("Buyer total: high to low")),
]


class ComparisonScopeForm(forms.Form):
    marketplace = forms.ModelChoiceField(
        label=_("Marketplace"), queryset=Marketplace.objects.active(), required=False, empty_label=_("All marketplaces")
    )
    data_kind = forms.ChoiceField(label=_("Data provenance"), required=False, choices=[
        ("", _("All provenance types (separate benchmarks)")),
        ("demo", _("Demonstration only")),
        ("non_demo", _("Imported / manual only — not verified live")),
    ])


class ProductSearchForm(ComparisonScopeForm):
    field_order = ["q", "marketplace", "data_kind", "sort", "review", "product"]
    product = forms.ModelChoiceField(queryset=Product.objects.active(), required=False, widget=forms.HiddenInput)
    q = forms.CharField(
        label=_("Product or brand"), required=False, max_length=200,
        widget=forms.TextInput(attrs={"placeholder": _("Try Luma, white, bundle, or AspanLab")}),
    )
    sort = forms.ChoiceField(label=_("Sort by"), choices=SORT_CHOICES, required=False, initial="name")
    review = forms.ChoiceField(label=_("Match review"), required=False,
                              choices=[("", _("All associations")), *Offer.MatchStatus.choices])


class DataSourceConfigureForm(forms.ModelForm):
    class Meta:
        model = DataSource
        fields = ("key", "marketplace", "provider", "refresh_enabled", "refresh_interval_minutes", "stale_after_hours")
        labels = {"key": _("Stable source key"), "marketplace": _("Marketplace"), "provider": _("Provider")}
        help_texts = {"key": _("Use 1–80 lowercase letters, digits, underscores or hyphens. Source identity cannot be changed later.")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marketplace"].queryset = Marketplace.objects.active()
        if self.instance.pk:
            for name in ("key", "marketplace", "provider"):
                self.fields[name].disabled = True
            if self.instance.provider != DataSource.Provider.KASPI:
                self.fields["refresh_enabled"].disabled = True
        else:
            self.fields["provider"].choices = [(DataSource.Provider.KASPI, DataSource.Provider.KASPI.label)]
            self.fields["provider"].initial = DataSource.Provider.KASPI
            self.fields["marketplace"].queryset = Marketplace.objects.active().filter(name="Kaspi.kz")
            self.fields["marketplace"].initial = Marketplace.objects.active().filter(name="Kaspi.kz").first()

    def clean_key(self):
        import re
        key = self.cleaned_data["key"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", key):
            raise forms.ValidationError(_("Use a lowercase stable source key without spaces."))
        return key
