from django.core.management.base import BaseCommand, CommandError

from core.importing import run_import
from core.models import Marketplace
from core.providers import CSVOfferProvider, SourceError


class Command(BaseCommand):
    help = "Preview (default) or explicitly apply operator-supplied KZT offers. No marketplace requests."

    def add_arguments(self, parser):
        parser.add_argument("file", help="UTF-8 CSV path, max 2 MiB / 1000 offer rows.")
        parser.add_argument("--source", required=True, help="Stable lowercase source namespace, reused on later imports.")
        parser.add_argument("--marketplace", required=True, help="Exact existing Marketplace name.")
        parser.add_argument("--demo", action="store_true", help="Required for fictional/illustrative inputs; cannot change an existing source's mode.")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--apply", action="store_true", help="Save the validated batch atomically.")
        mode.add_argument("--dry-run", action="store_true", help="Preview only; the default. Save no data or status.")

    def handle(self, *args, **options):
        try:
            marketplace = Marketplace.objects.active().get(name=options["marketplace"])
        except Marketplace.DoesNotExist:
            raise CommandError("Marketplace not found in the active MVP scope. Run init_marketplaces and use Kaspi.kz, Halyk Market, Ozon, Wildberries or Teez.") from None
        try:
            result = run_import(
                CSVOfferProvider(options["file"]), key=options["source"], marketplace=marketplace,
                is_demo=options["demo"], apply=options["apply"],
            )
        except SourceError as error:
            rejected = getattr(error, "rejected_count", None)
            count = "unknown" if rejected is None else str(rejected)
            raise CommandError(error.public_message +
                               f" Batch not applied: new=0, updated=0, unchanged=0, rejected={count}, skipped=0; observations=0.") from None
        label = "APPLIED" if options["apply"] else "PREVIEW ONLY - no records or status saved"
        source_mode = "Demonstration CSV (fictional), not live" if options["demo"] else "Manual CSV, unverified, not live"
        self.stdout.write(self.style.SUCCESS(
            f"{label}: products created={result.products_created}, updated={result.products_updated}; "
            f"offers created={result.offers_created}, updated={result.offers_updated}, unchanged={result.offers_unchanged}. "
            f"rejected={result.offers_rejected}, skipped={result.offers_skipped}; "
            f"observations={result.observations_created}, reviews invalidated={result.reviews_reset}. "
            f"{source_mode}; no marketplace request. Observations use actual import time, not marketplace update time."
        ))
