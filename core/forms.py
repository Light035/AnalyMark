from django import forms

from .models import Marketplace, Product

SORT_CHOICES = [
    ("name", "Product name: A–Z"),
    ("name_desc", "Product name: Z–A"),
    ("price", "Listed price: low to high"),
    ("price_desc", "Listed price: high to low"),
    ("total", "Buyer total: low to high"),
    ("total_desc", "Buyer total: high to low"),
]


class ProductSearchForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False, widget=forms.HiddenInput)
    q = forms.CharField(
        label="Product or brand", required=False, max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Try Luma, white, bundle, or AspanLab"}),
    )
    marketplace = forms.ModelChoiceField(
        queryset=Marketplace.objects.all(), required=False, empty_label="All marketplaces"
    )
    sort = forms.ChoiceField(label="Sort by", choices=SORT_CHOICES, required=False, initial="name")
