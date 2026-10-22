from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Marketplace, Offer, PriceObservation, Product, WatchlistEntry


class DemoDataCommandTests(TestCase):
    def load(self, **options):
        output = StringIO()
        call_command("load_demo_data", stdout=output, **options)
        return output.getvalue()

    def test_loading_twice_keeps_the_same_records(self):
        output = self.load()
        original_ids = list(Offer.objects.order_by("pk").values_list("pk", flat=True))
        self.load()
        self.assertEqual(Marketplace.objects.count(), 2)
        self.assertEqual(Product.objects.count(), 14)
        self.assertEqual(Offer.objects.count(), 30)
        self.assertEqual(original_ids, list(Offer.objects.order_by("pk").values_list("pk", flat=True)))
        self.assertFalse(Offer.objects.filter(is_demo=False).exists())
        self.assertFalse(PriceObservation.objects.exists())
        self.assertIn("invented, not live", output)

    def test_examples_cover_known_zeros_and_missing_information(self):
        self.load()
        self.assertTrue(Offer.objects.filter(delivery_cost=0, discount=0).exists())
        self.assertTrue(Offer.objects.filter(delivery_cost__isnull=True).exists())
        self.assertTrue(Offer.objects.filter(discount__isnull=True).exists())
        self.assertTrue(Offer.objects.filter(delivery_cost__isnull=True, discount__isnull=True).exists())
        for offer in Offer.objects.all():
            offer.full_clean()
            self.assertIn("Demo", offer.seller_name)
            if offer.delivery_cost is None or offer.discount is None:
                self.assertIsNone(offer.total_buyer_cost)
        for product in Product.objects.all():
            product.full_clean()
            self.assertIn("Fictional demonstration product.", product.description)
        self.assertEqual(Product.objects.values("category").distinct().count(), 4)
        counts = list(Product.objects.annotate(count=Count("offers")).values_list("count", flat=True))
        self.assertIn(1, counts)
        self.assertIn(4, counts)

    def test_rerun_preserves_manual_offers_and_unrelated_records(self):
        self.load()
        sample = Offer.objects.first()
        manual = Offer.objects.create(
            product=sample.product, marketplace=sample.marketplace, seller_name=sample.seller_name,
            price=Decimal("7654.32"), is_demo=False,
        )
        unrelated = Product.objects.create(name="Personal product", category="Other")
        self.load()
        manual.refresh_from_db()
        self.assertEqual(manual.price, Decimal("7654.32"))
        self.assertIsNone(manual.delivery_cost)
        self.assertTrue(Product.objects.filter(pk=unrelated.pk).exists())
        self.assertEqual(Offer.objects.count(), 31)

    def illustrative_offer(self):
        return Offer.objects.get(seller_name="Steppe Keys Demo — illustrative history")

    def test_rerun_preserves_edits_to_demo_offers_products_and_marketplaces(self):
        self.load()
        offer = self.illustrative_offer()
        Offer.objects.filter(pk=offer.pk).update(price="19999.99", discount=None, product_url="https://personal.example/item")
        Product.objects.filter(pk=offer.product_id).update(description="My edited description", category="Personal category")
        Marketplace.objects.filter(pk=offer.marketplace_id).update(website_url="https://personal.example/")
        before = [list(model.objects.order_by("pk").values()) for model in (Marketplace, Product, Offer)]
        output = self.load(with_illustrative_history=True)
        self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in (Marketplace, Product, Offer)])
        self.assertFalse(PriceObservation.objects.exists())
        self.assertIn("edited sample offer/product preserved", output)

    def test_existing_saved_products_and_observations_are_unchanged(self):
        self.load()
        offer = self.illustrative_offer()
        user = get_user_model().objects.create_user(username="demo-preservation-test")
        WatchlistEntry.objects.create(user=user, product=offer.product)
        PriceObservation.objects.create(offer=offer, price="21111.00")
        before = [list(model.objects.order_by("pk").values()) for model in (Offer, WatchlistEntry, PriceObservation)]
        self.assertIn("existing observations preserved", self.load(with_illustrative_history=True))
        self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in (Offer, WatchlistEntry, PriceObservation)])

    def test_preexisting_matching_product_metadata_is_not_rewritten(self):
        product = Product.objects.create(name="Keyra K1 — compact, EN layout (demo)", brand="QalamLab", category="My category", description="My description")
        self.load(with_illustrative_history=True)
        product.refresh_from_db()
        self.assertEqual(product.category, "My category")
        self.assertEqual(product.description, "My description")
        self.assertFalse(PriceObservation.objects.exists())
        self.assertEqual(Product.objects.count(), 14)

    def test_seed_benchmarks_use_current_listed_prices_not_history_or_totals(self):
        self.load(with_illustrative_history=True)
        offer = self.illustrative_offer()
        response = self.client.get(reverse("core:product_detail", args=[offer.product_id]))
        self.assertEqual(response.context["summary"], {
            "count": 3, "minimum": Decimal("21900.00"), "maximum": Decimal("23000.00"),
            "average": Decimal("22466.67"), "median": Decimal("22500.00"),
        })
        self.assertEqual(offer.total_buyer_cost, Decimal("22700.00"))
        response = self.client.get(reverse("core:product_search"), {"product": offer.product_id, "marketplace": offer.marketplace_id})
        self.assertEqual(response.context["summary"]["average"], Decimal("22200.00"))
        self.assertEqual(response.context["summary"]["count"], 2)

    def test_illustrative_sequence_captures_actual_demo_state_at_real_invocation_times(self):
        self.load()
        observed_offer_prices = []
        original_save = PriceObservation.save

        def save_and_check_state(observation, *args, **kwargs):
            observed_offer_prices.append(Offer.objects.get(pk=observation.offer_id).price)
            return original_save(observation, *args, **kwargs)

        started = timezone.now()
        with patch.object(PriceObservation, "save", new=save_and_check_state):
            self.load(with_illustrative_history=True)
        finished = timezone.now()
        offer = self.illustrative_offer()
        observations = list(offer.observations.order_by("observed_at", "pk"))
        self.assertEqual([o.price for o in observations], [Decimal("23500"), Decimal("21900"), Decimal("22500")])
        self.assertEqual(observed_offer_prices, [o.price for o in observations])
        self.assertEqual(offer.price, Decimal("22500"))
        for observation in observations:
            observation.full_clean()
            self.assertTrue(observation.is_demo)
            self.assertGreaterEqual(observation.observed_at, started)
            self.assertLessEqual(observation.observed_at, finished)
        self.assertEqual(Product.objects.filter(offers__observations__isnull=False).distinct().count(), 1)
        self.assertEqual(Product.objects.exclude(offers__observations__isnull=False).count(), 13)

    def test_illustrative_history_is_optional_repeatable_and_not_reseeded_after_price_edits(self):
        self.load()
        self.assertFalse(PriceObservation.objects.exists())
        self.load(with_illustrative_history=True)
        before = list(PriceObservation.objects.order_by("pk").values())
        Offer.objects.filter(pk=self.illustrative_offer().pk).update(price="24000")
        self.load(with_illustrative_history=True)
        self.load()
        self.assertEqual(list(PriceObservation.objects.order_by("pk").values()), before)
        self.assertEqual(self.illustrative_offer().price, Decimal("24000"))

    def test_current_price_capture_does_not_repeat_the_final_illustrative_point(self):
        self.load(with_illustrative_history=True)
        offer = self.illustrative_offer()
        originals = list(offer.observations.values_list("pk", "observed_at", "price"))
        call_command("record_demo_observations", stdout=StringIO())
        self.assertEqual(list(offer.observations.values_list("pk", "observed_at", "price")), originals)
        self.assertEqual(PriceObservation.objects.count(), 32)  # 3 illustrative + 29 other offers.
        call_command("record_demo_observations", stdout=StringIO())
        self.assertEqual(PriceObservation.objects.count(), 32)

    def test_same_clock_tick_keeps_three_changes_without_artificial_time_offsets(self):
        frozen = timezone.now()
        with patch("core.management.commands.load_demo_data.timezone.now", return_value=frozen):
            self.load(with_illustrative_history=True)
        self.assertEqual(PriceObservation.objects.count(), 3)
        self.assertEqual(set(PriceObservation.objects.values_list("observed_at", flat=True)), {frozen})

    def test_failed_illustrative_capture_rolls_back_prices_and_partial_history(self):
        self.load()
        before = [list(model.objects.order_by("pk").values()) for model in (Product, Offer, PriceObservation)]
        original_save = PriceObservation.save
        captures = []

        def fail_second_capture(observation, *args, **kwargs):
            captures.append(observation.price)
            if len(captures) == 2:
                raise RuntimeError("Simulated capture failure")
            return original_save(observation, *args, **kwargs)

        with patch.object(PriceObservation, "save", new=fail_second_capture):
            with self.assertRaisesMessage(RuntimeError, "Simulated capture failure"):
                self.load(with_illustrative_history=True)
        self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in (Product, Offer, PriceObservation)])

    def test_illustrative_disclosures_and_empty_history_are_rendered(self):
        self.load(with_illustrative_history=True)
        offer = self.illustrative_offer()
        for url in (reverse("core:product_detail", args=[offer.product_id]), reverse("core:price_history", args=[offer.pk])):
            response = self.client.get(url)
            self.assertContains(response, "Illustrative sample price changes")
            self.assertContains(response, "within one command run")
            self.assertContains(response, "Demonstration observation · not live")
            self.assertContains(response, "Steppe Keys Demo — illustrative history")
            self.assertContains(response, "23,500.00 KZT")
        response = self.client.get(reverse("core:product_detail", args=[Product.objects.get(name="Matra M1 — large grey desk mat (demo)").pk]))
        self.assertContains(response, "No observations recorded")
        self.assertNotContains(response, 'class="observation-point"')
