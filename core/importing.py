"""Explicit, atomic ingestion; acquisition is delegated to an OfferProvider."""
import re
from dataclasses import asdict, dataclass

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone

from .models import DataSource, Marketplace, Offer, PriceObservation, Product, RefreshRun, SourceOffer, SourceProduct
from .matching import reset_reviews
from .providers import InvalidSourceData, SourceBlocked, SourceError, SourceTimeout, SourceUnavailable, SUPPORTED_PROVIDER_KINDS, validate_records


@dataclass
class ImportResult:
    products_created: int = 0
    products_updated: int = 0
    offers_created: int = 0
    offers_updated: int = 0
    offers_unchanged: int = 0
    offers_rejected: int = 0
    offers_skipped: int = 0
    observations_created: int = 0
    reviews_reset: int = 0


def _save_validated(instance, row, label):
    try:
        instance.full_clean()
    except ValidationError:
        # Model errors can contain submitted values. Expose field names only.
        raise InvalidSourceData(
            f"Row {row}: {label} violates catalog validation or a uniqueness constraint. "
            "Check retained discounts, field lengths and seller/product identity."
        ) from None
    instance.save()


def _update(instance, values):
    changed = False
    for name, value in values.items():
        if getattr(instance, name) != value:
            setattr(instance, name, value)
            changed = True
    return changed


def _persist(source, records, imported_at, refresh_run=None):
    result = ImportResult(offers_skipped=getattr(records, "skipped", 0))
    products = {}
    changed_products = {}
    for row, record in enumerate(records, start=2):
        row = record.row_number or row
        if record.product_id not in products:
            mapping = SourceProduct.objects.select_related("product").filter(
                source=source, external_id=record.product_id
            ).first()
            values = {"name": record.product_name, "category": record.category}
            if record.brand:
                values["brand"] = record.brand
            if mapping:
                product = mapping.product
                identity_fields = [field for field, value in values.items() if getattr(product, field) != value]
                if _update(product, values):
                    _save_validated(product, row, "product")
                    affected = product.offers.all()
                    result.reviews_reset += affected.exclude(match_status=Offer.MatchStatus.UNREVIEWED).count()
                    reset_reviews(affected, "Source product identity changed (" + ", ".join(identity_fields) + "); manual review is required again.")
                    changed_products[record.product_id] = identity_fields
                    result.products_updated += 1
            else:
                product = Product(**values)
                _save_validated(product, row, "product")
                mapping = SourceProduct(source=source, external_id=record.product_id, product=product)
                _save_validated(mapping, row, "product identity")
                result.products_created += 1
            products[record.product_id] = product
        product = products[record.product_id]
        mapping = SourceOffer.objects.select_related("offer").filter(
            source=source, external_id=record.offer_id
        ).first()
        if mapping and (mapping.offer.product_id != product.pk
                        or mapping.offer.marketplace_id != source.marketplace_id
                        or mapping.offer.is_demo != source.is_demo):
            raise InvalidSourceData(f"Row {row}: offer_id cannot change product, marketplace or demo status.")
        values = {"seller_name": record.seller_name, "price": record.listed_price, "product_url": record.source_url}
        # Blank means unknown on create, preserve known values on updates. No clear operation.
        for field in ("delivery_cost", "discount"):
            if getattr(record, field) is not None:
                values[field] = getattr(record, field)
        if mapping:
            offer = mapping.offer
            price_changed = offer.price != record.listed_price
            identity_fields = [field for field in ("seller_name", "product_url") if getattr(offer, field) != values[field]]
            if identity_fields:
                affected = Offer.objects.filter(pk=offer.pk)
                result.reviews_reset += affected.exclude(match_status=Offer.MatchStatus.UNREVIEWED).count()
                reason = "Source offer identity changed (" + ", ".join(identity_fields) + "); manual review is required again."
                if record.product_id in changed_products:
                    reason += " Product identity also changed (" + ", ".join(changed_products[record.product_id]) + ")."
                reset_reviews(affected, reason)
                offer.refresh_from_db()
            changed = _update(offer, values)
            # Validate even unchanged managed offers (including manual edits).
            _save_validated(offer, row, "offer")
            if changed:
                result.offers_updated += 1
            else:
                result.offers_unchanged += 1
            if price_changed:
                observation = PriceObservation(offer=offer, price=offer.price,
                                               observed_at=imported_at, is_demo=source.is_demo,
                                               recorded_by_import=source.provider == "csv", refresh_run=refresh_run)
                _save_validated(observation, row, "price observation")
                result.observations_created += 1
            mapping.source_url = record.source_url
            mapping.imported_at = imported_at
        else:
            offer = Offer(product=product, marketplace=source.marketplace, is_demo=source.is_demo, **values)
            _save_validated(offer, row, "offer")
            mapping = SourceOffer(source=source, external_id=record.offer_id, offer=offer,
                                  source_url=record.source_url, imported_at=imported_at)
            result.offers_created += 1
        _save_validated(mapping, row, "offer provenance")
    return result


def run_import(provider, *, key, marketplace, is_demo=False, apply=False, refresh_run=None):
    """Dry-run exercises the same writes/constraints then rolls everything back.

    Apply keeps a safe source failure status outside the catalog transaction.
    Only actual changed imported prices create observations. No backfill, HTTP,
    automatic merging or deletion occurs here.
    """
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", key):
        raise InvalidSourceData("Source key: use 1–80 lowercase letters, digits, underscores or hyphens.")
    if provider.kind not in SUPPORTED_PROVIDER_KINDS:
        raise InvalidSourceData("Unsupported provider; access must be verified before implementing an adapter.")
    try:
        if not Marketplace.objects.active().filter(pk=marketplace.pk).exists():
            raise InvalidSourceData("Marketplace is archived or outside the five-marketplace MVP scope.")
        source = DataSource.objects.filter(key=key).first()
    except DatabaseError:
        raise SourceUnavailable from None
    if source and (source.marketplace_id != marketplace.pk or source.is_demo != is_demo or source.provider != provider.kind):
        raise InvalidSourceData("Source key already belongs to a different marketplace, provider or demo mode. Use the original settings.")
    if apply and not source:
        try:
            source = DataSource.objects.create(key=key, marketplace=marketplace, is_demo=is_demo, provider=provider.kind)
        except DatabaseError:
            raise SourceUnavailable from None
    attempted_at = timezone.now()
    records = None
    try:
        try:
            records = validate_records(provider.fetch())
        except TimeoutError:
            raise SourceTimeout from None
        except OSError:
            raise SourceUnavailable from None
        with transaction.atomic():
            if not Marketplace.objects.active().filter(pk=marketplace.pk).exists():
                raise InvalidSourceData("Marketplace was archived; no catalog changes were saved.")
            if source:
                source = DataSource.objects.select_for_update().get(pk=source.pk)
            else:
                source = DataSource.objects.create(key=key, marketplace=marketplace, is_demo=is_demo, provider=provider.kind)
            if refresh_run:
                if not apply or not RefreshRun.objects.filter(pk=refresh_run.pk, source=source, status=RefreshRun.Status.RUNNING).update(started_at=refresh_run.started_at):
                    raise InvalidSourceData("Refresh is no longer owned by this worker; no catalog changes were saved.")
                # The conditional write fences late workers after explicit recovery.
            imported_at = timezone.now()  # Actual import operation; NOT marketplace update time.
            result = _persist(source, records, imported_at, refresh_run)
            if apply:
                source.status = DataSource.Status.SUCCESS
                source.last_attempt_at = attempted_at
                source.last_success_at = imported_at
                source.last_error = ""
                source.save(update_fields=["status", "last_attempt_at", "last_success_at", "last_error"])
                if refresh_run:
                    RefreshRun.objects.filter(pk=refresh_run.pk, status=RefreshRun.Status.RUNNING).update(
                        status=RefreshRun.Status.SUCCEEDED, finished_at=timezone.now(), counts=asdict(result), error="")
            else:
                transaction.set_rollback(True)
        return result
    except Exception as error:
        if isinstance(error, SourceError):
            safe_error = error
        elif isinstance(error, DatabaseError):
            safe_error = InvalidSourceData("Database conflict or unavailable database. No catalog changes were saved; check identities and retry.")
        else:
            safe_error = InvalidSourceData("Malformed provider result. No catalog changes were saved.")
        safe_error.rejected_count = (len(records) + getattr(records, "skipped", 0) if records is not None
                                     else getattr(error, "rejected_count", None))
        owned = not refresh_run or RefreshRun.objects.filter(pk=refresh_run.pk, status=RefreshRun.Status.RUNNING).exists()
        if apply and source and source.pk and owned:
            try:
                DataSource.objects.filter(pk=source.pk).update(
                    status=DataSource.Status.BLOCKED if isinstance(safe_error, SourceBlocked) else DataSource.Status.ERROR,
                    last_attempt_at=attempted_at, last_error=safe_error.public_message
                )
            except DatabaseError:
                # If SQLite itself is unavailable, a failure status cannot be stored.
                raise SourceUnavailable from None
        raise safe_error from None
