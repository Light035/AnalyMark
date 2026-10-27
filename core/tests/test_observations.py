from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Marketplace, Offer, PriceObservation, Product


class PriceObservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        product = Product.objects.create(name="Demo lamp", category="Lighting")
        marketplace = Marketplace.objects.create(name="Kaspi.kz")
        cls.offer = Offer.objects.create(product=product, marketplace=marketplace, seller_name="Demo seller", price="100.00")
        cls.other = Offer.objects.create(product=product, marketplace=marketplace, seller_name="Other demo", price="200.00", delivery_cost=None, discount=None)
        cls.manual = Offer.objects.create(product=product, marketplace=marketplace, seller_name="Manual", price="300.00", is_demo=False)

    def record(self):
        output = StringIO()
        call_command("record_demo_observations", stdout=output)
        return output.getvalue()

    def test_model_validates_prices_and_does_not_mislabel_demo_data(self):
        PriceObservation(offer=self.offer, price=Decimal("1.23")).full_clean()
        for price in ("0", "-1", "1.001", "NaN", "Infinity", "invalid"):
            with self.subTest(price=price):
                with self.assertRaises(ValidationError):
                    PriceObservation(offer=self.offer, price=price).full_clean()
        with self.assertRaises(ValidationError):
            PriceObservation(offer=self.offer, price="100.00", is_demo=False).full_clean()
        with self.assertRaises(ValidationError):
            PriceObservation(offer_id=99999, price="100.00").full_clean()

    def test_future_and_naive_timestamps_are_rejected(self):
        for timestamp in (timezone.now() + timedelta(days=1), timezone.now().replace(tzinfo=None)):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValidationError):
                    PriceObservation(offer=self.offer, price="100", observed_at=timestamp).full_clean()

    def test_database_enforces_positive_prices_but_allows_coincident_captures(self):
        timestamp = timezone.now()
        PriceObservation.objects.create(offer=self.offer, price="100", observed_at=timestamp)
        PriceObservation.objects.create(offer=self.offer, price="200", observed_at=timestamp)
        self.assertEqual(self.offer.observations.count(), 2)
        for price in ("0", "-1"):
            with self.subTest(price=price):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    PriceObservation.objects.create(offer=self.offer, price=price)

    def test_first_run_only_captures_demo_offers_at_actual_invocation_time(self):
        started = timezone.now()
        output = self.record()
        finished = timezone.now()
        observations = PriceObservation.objects.all()
        self.assertEqual(observations.count(), 2)
        self.assertFalse(observations.filter(offer=self.manual).exists())
        for observation in observations:
            self.assertTrue(observation.is_demo)
            self.assertEqual(observation.price, observation.offer.price)
            self.assertGreaterEqual(observation.observed_at, started)
            self.assertLessEqual(observation.observed_at, finished)
        self.assertIn("Recorded 2", output)
        self.assertIn("not live marketplace history", output)

    def test_rerun_without_price_change_preserves_ids_and_timestamps(self):
        frozen = timezone.now()
        with patch("core.management.commands.record_demo_observations.timezone.now", return_value=frozen):
            self.record()
            originals = list(PriceObservation.objects.values_list("pk", "observed_at"))
            output = self.record()
        self.assertIn("skipped 2 unchanged and 0 invalid", output)
        self.assertEqual(list(PriceObservation.objects.values_list("pk", "observed_at")), originals)

    def test_price_changes_and_returns_to_an_older_price_are_recorded(self):
        self.record()
        Offer.objects.filter(pk=self.offer.pk).update(price="110.00")
        self.record()
        Offer.objects.filter(pk=self.offer.pk).update(price="100.00")
        self.record()
        self.assertEqual(list(self.offer.observations.values_list("price", flat=True)), [Decimal("100"), Decimal("110"), Decimal("100")])
        self.assertEqual(self.other.observations.count(), 1)

    def test_distinct_price_transitions_within_one_clock_tick_keep_honest_times(self):
        frozen = timezone.now()
        with patch("core.management.commands.record_demo_observations.timezone.now", return_value=frozen):
            self.record()
            Offer.objects.filter(pk=self.offer.pk).update(price="110.00")
            self.record()
            Offer.objects.filter(pk=self.offer.pk).update(price="100.00")
            self.record()
            self.record()  # Unchanged price must still be suppressed.
        self.assertEqual(list(self.offer.observations.values_list("price", flat=True)), [Decimal("100"), Decimal("110"), Decimal("100")])
        self.assertEqual(set(self.offer.observations.values_list("observed_at", flat=True)), {frozen})
        self.assertEqual(self.other.observations.count(), 1)

    def test_delivery_or_discount_changes_do_not_add_listed_price_history(self):
        self.record()
        Offer.objects.filter(pk=self.offer.pk).update(delivery_cost="10.00", discount="5.00")
        self.record()
        self.assertEqual(PriceObservation.objects.count(), 2)

    def test_snapshot_price_survives_offer_price_changes_and_offer_deletion_is_protected(self):
        self.record()
        Offer.objects.filter(pk=self.offer.pk).update(price="150.00")
        self.assertEqual(self.offer.observations.get().price, Decimal("100"))
        with self.assertRaises(ProtectedError):
            self.offer.delete()

    def test_loading_demo_data_does_not_fabricate_history(self):
        call_command("load_demo_data", stdout=StringIO())
        call_command("load_demo_data", stdout=StringIO())
        self.assertEqual(PriceObservation.objects.count(), 0)

    def test_empty_history_is_public_and_read_only(self):
        url = reverse("core:price_history", args=[self.offer.pk])
        response = self.client.get(url)
        self.assertContains(response, "No observations recorded")
        self.assertContains(response, "No historical prices have been generated or inferred")
        self.assertFalse(PriceObservation.objects.exists())
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(reverse("core:price_history", args=[99999])).status_code, 404)

    def test_history_shows_only_stored_observations_for_this_offer(self):
        recorded_at = timezone.now()
        observation = PriceObservation.objects.create(offer=self.offer, price="99.25", observed_at=recorded_at)
        PriceObservation.objects.create(offer=self.other, price="888.88")
        response = self.client.get(reverse("core:price_history", args=[self.offer.pk]))
        self.assertContains(response, "99.25 KZT")
        self.assertNotContains(response, "888.88")
        self.assertContains(response, "Demonstration observation · not live")
        self.assertContains(response, 'role="region" aria-label="Scrollable offer observation table" tabindex="0"')
        self.assertContains(response, timezone.localtime(recorded_at).strftime("%Y-%m-%d %H:%M:%S %z"))
        self.assertEqual(list(response.context["observations"]), [observation])

    def test_manually_recorded_observations_are_unverified(self):
        PriceObservation.objects.create(offer=self.manual, price="300", is_demo=False)
        response = self.client.get(reverse("core:price_history", args=[self.manual.pk]))
        self.assertContains(response, "Manually recorded · unverified")
        self.assertNotContains(response, "Demonstration observation · not live")
