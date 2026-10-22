"""Small catalog and current offers; all money is denominated in KZT."""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator, URLValidator
from django.db import models
from django.utils import timezone


nonempty_name = RegexValidator(r"\S", "Enter a value containing more than whitespace.")
web_url = URLValidator(schemes=["http", "https"])


class Marketplace(models.Model):
    name = models.CharField(max_length=120, unique=True, validators=[nonempty_name])
    website_url = models.URLField(blank=True, validators=[web_url])

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, validators=[nonempty_name])
    brand = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=120, validators=[nonempty_name])
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="offers")
    marketplace = models.ForeignKey(
        Marketplace, on_delete=models.PROTECT, related_name="offers"
    )
    seller_name = models.CharField(max_length=160, validators=[nonempty_name])
    price = models.DecimalField(
        "Listed price (KZT)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    delivery_cost = models.DecimalField(
        "Buyer delivery (KZT)", max_digits=12, decimal_places=2,
        blank=True, null=True, validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Leave blank when unknown. Enter 0 only for known free delivery.",
    )
    discount = models.DecimalField(
        "Discount amount (KZT)", max_digits=12, decimal_places=2,
        blank=True, null=True, validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Amount deducted from listed price, not a percentage. Blank means unknown.",
    )
    product_url = models.URLField(blank=True, validators=[web_url])
    is_demo = models.BooleanField("Demonstration data", default=True)

    class Meta:
        ordering = ["product__name", "marketplace__name", "seller_name", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="offer_price_positive"),
            models.CheckConstraint(
                condition=models.Q(delivery_cost__isnull=True) | models.Q(delivery_cost__gte=0),
                name="offer_delivery_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount__isnull=True) | models.Q(discount__gte=0),
                name="offer_discount_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(discount__isnull=True) | models.Q(discount__lte=models.F("price")),
                name="offer_discount_within_price",
            ),
            models.UniqueConstraint(
                fields=["product", "marketplace", "seller_name", "is_demo"],
                name="offer_unique_seller_product_source",
            ),
        ]

    def __str__(self):
        return f"{self.product} — {self.seller_name} ({self.marketplace})"

    def clean(self):
        super().clean()
        if (
            isinstance(self.price, Decimal) and self.price.is_finite()
            and isinstance(self.discount, Decimal) and self.discount.is_finite()
            and self.discount > self.price
        ):
            raise ValidationError({"discount": "Discount cannot exceed the listed price."})

    @property
    def total_buyer_cost(self):
        """Known listed price minus a known discount plus known buyer delivery."""
        if any(value is None for value in (self.price, self.delivery_cost, self.discount)):
            return None
        try:
            price, delivery, discount = (
                Decimal(str(value)) for value in (self.price, self.delivery_cost, self.discount)
            )
        except (InvalidOperation, ValueError):
            return None
        if not all(value.is_finite() for value in (price, delivery, discount)):
            return None
        if price <= 0 or delivery < 0 or not Decimal("0") <= discount <= price:
            return None
        return price - discount + delivery


class WatchlistEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlist_entries")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="watchlist_entries")
    saved_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-saved_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="watchlist_unique_user_product")]

    def __str__(self):
        return f"{self.user} — {self.product}"


class PriceObservation(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT, related_name="observations")
    price = models.DecimalField(
        "Recorded listed price (KZT)", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    observed_at = models.DateTimeField(default=timezone.now, editable=False)
    is_demo = models.BooleanField("Demonstration observation", default=True)

    class Meta:
        ordering = ["-observed_at", "-pk"]
        indexes = [models.Index(fields=["offer", "-observed_at"], name="observation_offer_time")]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="observation_price_positive"),
        ]

    def clean(self):
        super().clean()
        if isinstance(self.observed_at, datetime):
            if timezone.is_naive(self.observed_at):
                raise ValidationError({"observed_at": "Use a timestamp with a timezone."})
            if self.observed_at > timezone.now():
                raise ValidationError({"observed_at": "An observation cannot be recorded in the future."})
        if self.offer_id:
            try:
                offer = self.offer
            except Offer.DoesNotExist:
                return  # Field validation reports an invalid foreign key.
            if offer.is_demo and not self.is_demo:
                raise ValidationError({"is_demo": "Observations of demonstration offers must be labeled demonstration data."})

    def __str__(self):
        return f"{self.offer} — {self.price} KZT at {self.observed_at}"
