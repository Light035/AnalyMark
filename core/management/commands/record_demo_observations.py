"""Capture actual invocation times and current demo listed prices, never backfill."""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Offer, PriceObservation


class Command(BaseCommand):
    help = "Record demo listed prices now; skip offers unchanged since their latest demo observation."

    @transaction.atomic
    def handle(self, *args, **options):
        recorded = unchanged = invalid = 0
        recorded_at = timezone.now()
        for offer in Offer.objects.select_for_update().filter(is_demo=True).order_by("pk"):
            observation = PriceObservation(offer=offer, price=offer.price, observed_at=recorded_at, is_demo=True)
            try:
                observation.full_clean(validate_unique=False, validate_constraints=False)
            except ValidationError:
                invalid += 1
                self.stderr.write(f"Skipped offer {offer.pk}: invalid observation data.")
                continue
            latest = offer.observations.filter(is_demo=True).first()
            if latest is not None and latest.price == observation.price:
                unchanged += 1
                continue
            observation.save()
            recorded += 1
        self.stdout.write(self.style.SUCCESS(
            f"Recorded {recorded} demonstration observations now; skipped {unchanged} unchanged and {invalid} invalid offers. "
            "These are demo snapshots, not live marketplace history."
        ))
