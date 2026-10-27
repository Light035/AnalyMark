"""Small catalog and current offers; all money is denominated in KZT."""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator, URLValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


nonempty_name = RegexValidator(r"\S", "Enter a value containing more than whitespace.")
web_url = URLValidator(schemes=["http", "https"])


class MarketplaceQuerySet(models.QuerySet):
    def active(self):
        from .marketplaces import APPROVED_NAMES
        return self.filter(is_active=True, name__in=APPROVED_NAMES)


class Marketplace(models.Model):
    objects = MarketplaceQuerySet.as_manager()
    name = models.CharField(max_length=120, unique=True, validators=[nonempty_name])
    website_url = models.URLField(blank=True, validators=[web_url])
    is_active = models.BooleanField(_("Active in MVP"), default=True)

    @property
    def is_supported(self):
        from .marketplaces import APPROVED_NAMES
        return self.is_active and self.name in APPROVED_NAMES

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def active(self):
        active_markets = Marketplace.objects.active()
        return self.alias(
            _active_offer=models.Exists(Offer.objects.filter(product_id=models.OuterRef("pk"), marketplace__in=active_markets)),
            _any_offer=models.Exists(Offer.objects.filter(product_id=models.OuterRef("pk"))),
            _archived_origin=models.Exists(SourceProduct.objects.filter(product_id=models.OuterRef("pk")).exclude(source__marketplace__in=active_markets)),
        ).filter(models.Q(_active_offer=True) | models.Q(_any_offer=False, _archived_origin=False))


class Product(models.Model):
    objects = ProductQuerySet.as_manager()
    name = models.CharField(max_length=200, validators=[nonempty_name])
    brand = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=120, validators=[nonempty_name])
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """An operator-managed namespace, not a claim of marketplace authorization."""

    class Status(models.TextChoices):
        NEVER = "never", _("Not imported")
        SUCCESS = "success", _("Last import succeeded")
        ERROR = "error", _("Last import failed")
        BLOCKED = "blocked", _("Refresh blocked: access not verified")

    class Provider(models.TextChoices):
        DEMO = "demo", _("Fictional demonstration fixtures")
        CSV = "csv", "Manual CSV"
        KASPI = "kaspi", _("Kaspi competitor offers — access required")

    key = models.SlugField(max_length=80, unique=True)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.PROTECT)
    provider = models.CharField(max_length=20, default=Provider.CSV, choices=Provider)
    is_demo = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status, default=Status.NEVER)
    last_attempt_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_success_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_error = models.TextField(blank=True, editable=False)
    stale_after_hours = models.PositiveIntegerField(
        _("Import age threshold (hours)"), null=True, blank=True,
        validators=[MinValueValidator(1)],
        help_text=_("Optional source-specific interval. Blank means no age assessment; it does not establish price freshness."),
    )
    refresh_enabled = models.BooleanField(_("Periodic refresh enabled"), default=False)
    refresh_interval_minutes = models.PositiveIntegerField(
        _("Refresh interval (minutes)"), default=60,
        validators=[MinValueValidator(5), MaxValueValidator(10080)],
    )
    next_refresh_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["key"]
        constraints = [models.CheckConstraint(
            condition=models.Q(stale_after_hours__isnull=True) | models.Q(stale_after_hours__gte=1),
            name="source_age_threshold_positive",
        ), models.CheckConstraint(condition=models.Q(refresh_interval_minutes__gte=5, refresh_interval_minutes__lte=10080),
                                  name="source_refresh_interval_valid"),
            models.CheckConstraint(condition=models.Q(refresh_enabled=False) | models.Q(provider="kaspi"),
                                   name="source_refresh_provider_valid"),
            models.CheckConstraint(condition=~models.Q(provider="demo") | models.Q(is_demo=True),
                                   name="demo_source_requires_demo")]

    def __str__(self):
        return self.key

    def clean(self):
        super().clean()
        if self.provider == self.Provider.DEMO and not self.is_demo:
            raise ValidationError({"is_demo": _("Demonstration fixtures must remain demonstration data.")})
        if self.refresh_enabled and self.provider != self.Provider.KASPI:
            raise ValidationError({"refresh_enabled": _("CSV and demo fixtures cannot be scheduled as competitor feeds.")})
        if self.provider == self.Provider.KASPI and (self.is_demo or not Marketplace.objects.filter(pk=self.marketplace_id, name="Kaspi.kz").exists()):
            raise ValidationError({"provider": _("The pending Kaspi source requires the Kaspi.kz marketplace and non-demo mode. It does not supply data yet.")})

    @property
    def import_age_status(self):
        if self.last_success_at is None:
            return _("No successful import; age cannot be assessed")
        age_seconds = (timezone.now() - self.last_success_at).total_seconds()
        if age_seconds < 0:
            return _("Import timestamp is in the future; check the clock")
        if self.stale_after_hours is None:
            return _("No import age threshold configured")
        if age_seconds >= self.stale_after_hours * 3600:
            return _("Configured import interval exceeded")
        return _("Within configured import interval; prices remain unverified")


class RefreshRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", _("Queued — waiting for worker")
        RUNNING = "running", _("Running")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")
        BLOCKED = "blocked", _("Blocked — provider access required")
        CANCELLED = "cancelled", _("Cancelled")

    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="refresh_runs")
    status = models.CharField(max_length=12, choices=Status, default=Status.QUEUED)
    scheduled = models.BooleanField(default=False)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    queued_at = models.DateTimeField(default=timezone.now, editable=False)
    started_at = models.DateTimeField(null=True, editable=False)
    finished_at = models.DateTimeField(null=True, editable=False)
    error = models.TextField(blank=True, editable=False)
    counts = models.JSONField(default=dict, editable=False)

    class Meta:
        ordering = ["-queued_at", "-pk"]
        constraints = [models.UniqueConstraint(fields=["source"], condition=models.Q(status__in=["queued", "running"]),
                                               name="source_one_active_refresh")]
        indexes = [models.Index(fields=["status", "queued_at"], name="refresh_queue_order")]


class SourceProduct(models.Model):
    """Exact source product/variant identity; names are never merge keys."""

    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="products")
    external_id = models.CharField(max_length=160)
    product = models.OneToOneField(Product, on_delete=models.PROTECT, related_name="import_record")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "external_id"], name="source_product_identity")]


class OfferQuerySet(models.QuerySet):
    def active(self):
        return self.filter(marketplace__in=Marketplace.objects.active())


class Offer(models.Model):
    objects = OfferQuerySet.as_manager()
    class MatchStatus(models.TextChoices):
        UNREVIEWED = "unreviewed", _("Unreviewed association")
        CONFIRMED = "confirmed", _("Manually confirmed match")
        REJECTED = "rejected", _("Rejected association")

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
    match_status = models.CharField(
        _("Match review"), max_length=12, choices=MatchStatus, default=MatchStatus.UNREVIEWED,
        help_text=_("A manual review of this offer's link to its catalog product, not verification of its price or cross-marketplace identity."),
    )
    match_notes = models.TextField(_("Review explanation"), blank=True,
                                  help_text=_("Required when confirming or rejecting. Check model, variant and bundle using the source evidence."))
    match_reviewed_at = models.DateTimeField(_("Review time"), null=True, blank=True, editable=False)
    match_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
        on_delete=models.SET_NULL, related_name="reviewed_offers", verbose_name=_("Reviewed by"),
    )

    class Meta:
        ordering = ["product__name", "marketplace__name", "seller_name", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(match_status__in=["unreviewed", "confirmed", "rejected"]), name="offer_match_status_valid"),
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
        if self.match_status in (self.MatchStatus.CONFIRMED, self.MatchStatus.REJECTED) and not (self.match_notes or "").strip():
            raise ValidationError({"match_notes": _("Explain why this association is confirmed or rejected.")})
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


class SourceOffer(models.Model):
    """Provenance of the latest imported current offer, independent of history."""

    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="offers")
    external_id = models.CharField(max_length=160)
    offer = models.OneToOneField(Offer, on_delete=models.PROTECT, related_name="import_record")
    source_url = models.URLField(validators=[web_url])
    imported_at = models.DateTimeField(editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "external_id"], name="source_offer_identity")]


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
    recorded_by_import = models.BooleanField(_("Recorded by CSV import"), default=False, editable=False)
    refresh_run = models.ForeignKey(RefreshRun, null=True, blank=True, editable=False,
                                    on_delete=models.PROTECT, related_name="observations")

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
            if self.recorded_by_import or self.refresh_run_id:
                try:
                    source = offer.import_record.source
                except SourceOffer.DoesNotExist:
                    raise ValidationError({"recorded_by_import": "An imported observation requires offer source provenance."}) from None
                if self.is_demo != source.is_demo:
                    raise ValidationError({"is_demo": "Imported observations must retain the source's demonstration mode."})
                if self.refresh_run_id and self.refresh_run.source_id != source.pk:
                    raise ValidationError({"refresh_run": "Refresh source must match offer provenance."})

    def __str__(self):
        return f"{self.offer} — {self.price} KZT at {self.observed_at}"
