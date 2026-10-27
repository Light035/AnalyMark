"""Sequential CSV refreshes; all inputs are fictional isolated test fixtures."""
import csv
import io
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from core.importing import run_import
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, SourceOffer
from core.providers import COLUMNS, InvalidSourceData
from core.tests.test_importing import sample


class Provider:
    kind = "csv"

    def __init__(self, records):
        self.records = records

    def fetch(self):
        return self.records


class RefreshTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")

    def load(self, *records, apply=True, key="refresh", demo=False):
        return run_import(Provider(list(records or [sample()])), key=key,
                          marketplace=self.market, is_demo=demo, apply=apply)

    def confirm(self):
        offer = SourceOffer.objects.get(source__key="refresh").offer
        user = get_user_model().objects.create_user(username="reviewer")
        offer.match_status = "confirmed"
        offer.match_notes = "Exact variant and bundle checked."
        offer.match_reviewed_by = user
        offer.match_reviewed_at = timezone.now()
        offer.save()
        return offer

    def test_first_import_no_inferred_history_then_price_sequence_repeatable(self):
        self.assertEqual(self.load().observations_created, 0)
        self.assertFalse(PriceObservation.objects.exists())
        for price, expected in (("1300", 1), ("1300", 0), ("1200", 1)):
            before = timezone.now()
            result = self.load(sample(listed_price=Decimal(price)))
            self.assertEqual(result.observations_created, expected)
            mapping = SourceOffer.objects.get()
            if expected:
                newest = PriceObservation.objects.first()
                self.assertEqual(newest.price, Decimal(price))
                self.assertTrue(before <= newest.observed_at <= timezone.now())
                self.assertEqual(newest.observed_at, mapping.imported_at)
                self.assertTrue(newest.recorded_by_import)
                self.assertFalse(newest.is_demo)
        self.assertEqual(list(PriceObservation.objects.order_by("pk").values_list("price", flat=True)),
                         [Decimal("1300"), Decimal("1200")])
        self.assertEqual((Product.objects.count(), Offer.objects.count(), SourceOffer.objects.count()), (1, 1, 1))

    def test_price_only_update_preserves_complete_manual_review(self):
        self.load()
        offer = self.confirm()
        original = (offer.match_status, offer.match_notes, offer.match_reviewed_at, offer.match_reviewed_by_id)
        result = self.load(sample(listed_price=Decimal("1400"), delivery_cost=None, discount=None, brand=""))
        offer.refresh_from_db()
        self.assertEqual((offer.match_status, offer.match_notes, offer.match_reviewed_at, offer.match_reviewed_by_id), original)
        self.assertEqual((offer.delivery_cost, offer.discount, offer.product.brand), (Decimal("100"), Decimal("50"), "Test brand"))
        self.assertEqual(result.reviews_reset, 0)

    def test_identity_change_invalidates_review_with_field_reason(self):
        self.load()
        offer = self.confirm()
        result = self.load(sample(product_name="Different variant", seller_name="Different seller"))
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "unreviewed")
        self.assertIn("seller_name", offer.match_notes)
        self.assertIn("name", offer.match_notes)
        self.assertIsNone(offer.match_reviewed_at)
        self.assertIsNone(offer.match_reviewed_by_id)
        self.assertEqual(result.reviews_reset, 1)
        self.assertEqual(offer.product_id, Product.objects.get().pk)

    def test_product_identity_reason_records_metadata_field(self):
        self.load()
        offer = self.confirm()
        self.load(sample(brand="Changed brand"))
        offer.refresh_from_db()
        self.assertIn("brand", offer.match_notes)
        self.assertEqual(offer.match_status, "unreviewed")

    def test_preview_counts_changes_and_rolls_back_history_review_status_and_times(self):
        self.load()
        self.confirm()
        original_offer = Offer.objects.values().get()
        original_source = DataSource.objects.values().get()
        original_mapping = SourceOffer.objects.values().get()
        result = self.load(sample(listed_price=Decimal("1400"), product_name="New variant"), apply=False)
        self.assertEqual((result.offers_updated, result.observations_created, result.reviews_reset), (1, 1, 1))
        self.assertEqual(Offer.objects.values().get(), original_offer)
        self.assertEqual(DataSource.objects.values().get(), original_source)
        self.assertEqual(SourceOffer.objects.values().get(), original_mapping)
        self.assertFalse(PriceObservation.objects.exists())

    def test_later_row_conflict_rolls_back_price_history_metadata_and_review(self):
        self.load()
        self.confirm()
        before = Offer.objects.values().get()
        before_product = Product.objects.values().get()
        old_time = SourceOffer.objects.get().imported_at
        with self.assertRaises(InvalidSourceData) as error:
            self.load(sample(listed_price=Decimal("1400"), product_name="Changed"),
                      sample(offer_id="conflict", product_name="Changed"))
        self.assertEqual(error.exception.rejected_count, 2)
        self.assertEqual(Offer.objects.values().get(), before)
        self.assertEqual(Product.objects.values().get(), before_product)
        self.assertEqual(SourceOffer.objects.get().imported_at, old_time)
        self.assertFalse(PriceObservation.objects.exists())
        source = DataSource.objects.get()
        self.assertEqual(source.status, "error")
        self.assertEqual(source.last_success_at, old_time)
        self.assertIsNotNone(source.last_attempt_at)

    def test_observation_write_failure_rolls_back_current_price(self):
        self.load()
        with patch.object(PriceObservation, "save", side_effect=IntegrityError("PRIVATE")):
            with self.assertRaises(InvalidSourceData) as error:
                self.load(sample(listed_price=Decimal("1400")))
        self.assertNotIn("PRIVATE", error.exception.public_message)
        self.assertEqual(Offer.objects.get().price, Decimal("1200"))
        self.assertFalse(PriceObservation.objects.exists())

    def test_missing_fields_never_zero_and_charge_changes_do_not_capture_prices(self):
        self.load(sample(delivery_cost=None, discount=None))
        self.load(sample(listed_price=Decimal("1400"), delivery_cost=None, discount=None))
        offer = Offer.objects.get()
        self.assertIsNone(offer.total_buyer_cost)
        self.assertIsNone(offer.delivery_cost)
        self.assertIsNone(offer.discount)
        result = self.load(sample(listed_price=Decimal("1400"), delivery_cost=Decimal("0"), discount=Decimal("0")))
        self.assertEqual(result.observations_created, 0)
        self.assertEqual(PriceObservation.objects.count(), 1)
        self.assertEqual(Offer.objects.get().total_buyer_cost, Decimal("1400"))

    def test_absent_rows_and_other_sources_keep_price_history_and_last_seen(self):
        second = sample(offer_id="second", seller_name="Second seller")
        self.load(sample(), second)
        self.load(key="other")
        omitted = SourceOffer.objects.get(external_id="second")
        other = SourceOffer.objects.get(source__key="other")
        original_other = Offer.objects.values().get(pk=other.offer_id)
        self.load(sample(listed_price=Decimal("1400")))
        omitted.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(Offer.objects.count(), 3)
        self.assertEqual(omitted.offer.price, Decimal("1200"))
        self.assertEqual(Offer.objects.values().get(pk=other.offer_id), original_other)
        self.assertEqual(PriceObservation.objects.count(), 1)
        self.assertLess(omitted.imported_at, DataSource.objects.get(key="refresh").last_success_at)
        self.assertEqual(other.imported_at, other.source.last_success_at)

    def test_demo_and_imported_history_labels_and_old_observations_preserved(self):
        self.load(demo=True)
        self.load(sample(listed_price=Decimal("1400")), demo=True)
        observation = PriceObservation.objects.get()
        self.assertTrue(observation.is_demo)
        self.assertTrue(observation.recorded_by_import)
        offer = observation.offer
        old = PriceObservation.objects.create(offer=offer, price="1000", is_demo=True)
        self.load(sample(listed_price=Decimal("1500")), demo=True)
        self.assertTrue(PriceObservation.objects.filter(pk=old.pk, price="1000", recorded_by_import=False).exists())
        response = self.client.get(f"/offers/{offer.pk}/history/")
        self.assertContains(response, "Demonstration observation · not live")
        self.assertContains(response, "Recorded at import time, not marketplace update time.")
        self.assertNotContains(response, "CSV price change · unverified · not live")

    def test_imported_observation_has_distinct_table_and_chart_labels(self):
        self.load()
        self.load(sample(listed_price=Decimal("1400")))
        offer = Offer.objects.get()
        for url in (f"/offers/{offer.pk}/history/", f"/products/{offer.product_id}/"):
            response = self.client.get(url)
            self.assertContains(response, "CSV price change · unverified · not live")
            self.assertContains(response, "Recorded at import time, not marketplace update time.")
        response = self.client.get(f"/products/{offer.product_id}/", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertContains(response, "Изменение цены из CSV")

    def test_unimported_manual_observation_is_not_relabelled_as_csv(self):
        self.load()
        offer = Offer.objects.get()
        PriceObservation.objects.create(offer=offer, price="1100", is_demo=False)
        response = self.client.get(f"/offers/{offer.pk}/history/")
        self.assertContains(response, "Manually recorded · unverified")
        self.assertNotContains(response, "CSV price change · unverified · not live")
        self.assertNotContains(response, "Recorded at import time, not marketplace update time.")

    def test_observation_requires_matching_import_provenance(self):
        product = Product.objects.create(name="Manual", category="Test")
        offer = Offer.objects.create(product=product, marketplace=self.market, seller_name="Test", price="100")
        with self.assertRaises(ValidationError):
            PriceObservation(offer=offer, price="100", recorded_by_import=True).full_clean()

    def test_cli_duplicate_counts_preview_and_rejected_atomic_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "refresh.csv"
            def write(*records):
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
                    writer.writeheader()
                    for record in records:
                        writer.writerow({field:getattr(record, field) for field in COLUMNS})
            args = ("import_offers_csv", str(path))
            options = {"source":"refresh", "marketplace":"Kaspi.kz"}
            write(sample(), sample())
            out = io.StringIO()
            call_command(*args, **options, stdout=out)
            self.assertIn("skipped=1", out.getvalue())
            self.assertIn("rejected=0", out.getvalue())
            self.assertFalse(Offer.objects.exists())
            call_command(*args, **options, apply=True, stdout=io.StringIO())
            write(sample(listed_price=Decimal("1400")))
            out = io.StringIO()
            call_command(*args, **options, stdout=out)
            self.assertIn("observations=1", out.getvalue())
            self.assertFalse(PriceObservation.objects.exists())
            write(sample(), sample(currency="USD", offer_id="invalid"))
            with self.assertRaisesMessage(CommandError, "rejected=2"):
                call_command(*args, **options, apply=True)
            self.assertEqual(Offer.objects.get().price, Decimal("1200"))


class SourceAgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")

    def source(self, **kwargs):
        return DataSource.objects.create(key="age", marketplace=self.market, **kwargs)

    def test_no_default_threshold_or_invented_success(self):
        source = self.source()
        self.assertIsNone(source.stale_after_hours)
        self.assertIn("No successful import", source.import_age_status)
        source.last_success_at = timezone.now() - timedelta(days=365)
        source.save()
        self.assertEqual(source.import_age_status, "No import age threshold configured")

    def test_configured_interval_boundary_failure_and_future_clock(self):
        now = timezone.now()
        source = self.source(stale_after_hours=24, last_success_at=now-timedelta(hours=24), status="error")
        with patch("core.models.timezone.now", return_value=now):
            self.assertEqual(source.import_age_status, "Configured import interval exceeded")
            source.last_success_at += timedelta(seconds=1)
            self.assertIn("Within configured", source.import_age_status)
            source.last_success_at = now + timedelta(seconds=1)
            self.assertIn("check the clock", source.import_age_status)

    def test_threshold_validation_and_database_constraint(self):
        source = self.source()
        for value in (0, -1):
            source.stale_after_hours = value
            with self.assertRaises(ValidationError):
                source.full_clean()
            with self.assertRaises(IntegrityError), transaction.atomic():
                DataSource.objects.filter(pk=source.pk).update(stale_after_hours=value)

    def test_public_timestamps_separate_from_staff_errors_and_marketplace_time(self):
        source = self.source(last_success_at=timezone.now()-timedelta(days=3),
                             last_attempt_at=timezone.now(), status="error", last_error="Staff-only row error")
        for url in ("/", "/data-sources/"):
            response = self.client.get(url)
            self.assertContains(response, "Last successful import")
            self.assertContains(response, "Last attempted import")
            self.assertContains(response, "No import age threshold configured")
            self.assertContains(response, "Marketplace update time: not supplied")
            self.assertContains(response, "Changed imported prices create observations")
            self.assertNotContains(response, "Imports do not create price observations")
            self.assertNotContains(response, source.last_error)

    def test_admin_can_set_only_age_policy_without_reassigning_source(self):
        source = self.source()
        staff = get_user_model().objects.create_superuser(username="source-admin", password="test-only")
        self.client.force_login(staff)
        response = self.client.post(f"/admin/core/datasource/{source.pk}/change/", {
            "stale_after_hours":"48", "key":"tampered", "is_demo":"on", "_save":"Save"})
        self.assertEqual(response.status_code, 302)
        source.refresh_from_db()
        self.assertEqual(source.stale_after_hours, 48)
        self.assertEqual(source.key, "age")
        self.assertFalse(source.is_demo)
