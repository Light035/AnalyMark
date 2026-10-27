from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.marketplaces import MARKETPLACES
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, SourceOffer, SourceProduct
from core.providers import InvalidSourceData, provider_for
from core.refreshing import enqueue_refresh


class MarketplaceFixtureTests(TestCase):
    def load(self):
        call_command("load_marketplace_demo", stdout=StringIO())

    def test_initialization_is_additive_idempotent_and_preserves_metadata(self):
        kaspi = Marketplace.objects.create(name="Kaspi.kz", website_url="https://operator.example/")
        Marketplace.objects.create(name="Existing custom label")
        for _ in range(2):
            call_command("init_marketplaces", stdout=StringIO())
        self.assertEqual(Marketplace.objects.count(), len(MARKETPLACES) + 1)
        kaspi.refresh_from_db()
        self.assertEqual(kaspi.website_url, "https://operator.example/")
        self.assertEqual(Offer.objects.count(), 0)

    def test_counts_namespaces_and_no_fabricated_history(self):
        self.load()
        self.assertEqual((Product.objects.count(), Offer.objects.count(), DataSource.objects.count()), (8, 12, 4))
        self.assertFalse(PriceObservation.objects.exists())
        self.assertEqual(Offer.objects.filter(is_demo=True).count(), 12)
        self.assertEqual(SourceProduct.objects.filter(external_id="solo").count(), 4)
        self.assertEqual(SourceProduct.objects.filter(external_id="solo").values("product_id").distinct().count(), 4)
        self.assertEqual(SourceOffer.objects.filter(external_id="solo-seller-1").count(), 4)
        for source in DataSource.objects.all():
            self.assertEqual(source.provider, "demo")
            self.assertTrue(source.is_demo)
            self.assertEqual(source.products.count(), 2)
            self.assertEqual(source.offers.count(), 3)
            self.assertFalse(source.refresh_enabled)
        self.assertFalse(Offer.objects.exclude(seller_name__startswith="Demo ").exists())

    def test_rerun_preserves_all_records_timestamps_reviews_and_changed_prices(self):
        self.load()
        offer = Offer.objects.first()
        offer.price = Decimal("12345.67")
        offer.match_status, offer.match_notes = "confirmed", "Manual review of fictional variant"
        offer.match_reviewed_at = timezone.now()
        offer.save()
        PriceObservation.objects.create(offer=offer, price=offer.price, is_demo=True)
        product = offer.product
        product.name = "User-edited product name"
        product.save()
        models = (Product, Offer, SourceProduct, SourceOffer, PriceObservation, DataSource, Marketplace)
        before = [list(model.objects.order_by("pk").values()) for model in models]
        self.load()
        self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in models])

    def test_legacy_demo_is_preserved_and_not_adopted_by_name(self):
        call_command("load_demo_data", stdout=StringIO())
        original = list(Offer.objects.order_by("pk").values())
        Product.objects.create(name="Demo · MiraLab Desk Light Solo", brand="MiraLab Demo", category="User record")
        self.load()
        self.assertEqual(Product.objects.count(), 22)
        self.assertEqual(Offer.objects.count(), 30)
        self.assertEqual(original, list(Offer.objects.filter(pk__in=[row["id"] for row in original]).order_by("pk").values()))

    def test_missing_values_are_not_zero_and_known_totals_are_valid(self):
        self.load()
        known = SourceOffer.objects.filter(external_id="solo-seller-1").first().offer
        unknown = SourceOffer.objects.filter(external_id="solo-seller-2").first().offer
        self.assertEqual(known.total_buyer_cost, known.price - Decimal("500"))
        self.assertIsNone(unknown.delivery_cost)
        self.assertIsNone(unknown.discount)
        self.assertIsNone(unknown.total_buyer_cost)

    def test_reserved_source_collision_rolls_back_whole_command(self):
        market = Marketplace.objects.create(name="Teez")
        source = DataSource.objects.create(key="mvp-demo-teez-v1", marketplace=market, provider="csv", is_demo=False)
        with self.assertRaises(CommandError):
            self.load()
        self.assertEqual(Marketplace.objects.count(), 1)
        self.assertEqual(DataSource.objects.count(), 1)
        self.assertEqual(DataSource.objects.get().pk, source.pk)
        self.assertFalse(Product.objects.exists())
        self.assertFalse(Offer.objects.exists())

    def test_failure_during_second_offer_rolls_back_products_sources_and_offers(self):
        original = SourceOffer.objects.create
        def fail_second(**kwargs):
            if SourceOffer.objects.exists():
                raise RuntimeError("Simulated write failure")
            return original(**kwargs)
        with patch.object(SourceOffer.objects, "create", side_effect=fail_second), self.assertRaises(RuntimeError):
            self.load()
        for model in (Product, Offer, SourceProduct, SourceOffer, DataSource, Marketplace):
            self.assertFalse(model.objects.exists())

    def test_demo_cannot_become_live_or_be_queued_for_refresh(self):
        self.load()
        source = DataSource.objects.first()
        with self.assertRaises(InvalidSourceData):
            enqueue_refresh(source.pk)
        with self.assertRaises(InvalidSourceData):
            provider_for(source)
        source.is_demo = False
        with self.assertRaises(ValidationError):
            source.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            DataSource.objects.filter(pk=source.pk).update(is_demo=False)
        self.assertEqual(source.refresh_runs.count(), 0)

    def test_demo_load_has_no_provider_calls_and_does_not_claim_network_access(self):
        with patch("core.refreshing.provider_for", side_effect=AssertionError("No network provider should run")):
            self.load()
        response = self.client.get(reverse("core:data_sources"))
        self.assertContains(response, "No LIVE competitor feed is connected")
        self.assertContains(response, "DEMO · local fictional fixtures")
        self.assertContains(response, "mvp-demo-ozon-v1")

    def test_csv_updates_new_market_source_without_touching_fixtures_or_other_sources(self):
        from core.importing import run_import
        from core.tests.test_importing import sample
        from core.tests.test_refresh import Provider
        self.load()
        original_demo = list(Offer.objects.order_by("pk").values())
        markets = list(Marketplace.objects.filter(name__in=["Ozon", "Wildberries"]).order_by("pk"))
        for market in markets:
            run_import(Provider([sample()]), key=f"supplied-{market.pk}", marketplace=market, apply=True)
        offer = SourceOffer.objects.get(source__key=f"supplied-{markets[0].pk}").offer
        offer.match_status, offer.match_notes = "confirmed", "Reviewed exact variant"
        offer.save()
        for expected in (1, 0):
            result = run_import(Provider([sample(listed_price=Decimal("1350"), delivery_cost=None)]),
                                key=f"supplied-{markets[0].pk}", marketplace=markets[0], apply=True)
            self.assertEqual(result.observations_created, expected)
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "confirmed")
        self.assertEqual(offer.delivery_cost, Decimal("100"))
        self.assertEqual(PriceObservation.objects.count(), 1)
        self.assertFalse(PriceObservation.objects.get().is_demo)
        other = SourceOffer.objects.get(source__key=f"supplied-{markets[1].pk}").offer
        self.assertEqual(other.price, Decimal("1200"))
        self.assertNotEqual(offer.product_id, other.product_id)
        self.assertEqual(original_demo, list(Offer.objects.filter(is_demo=True).order_by("pk").values()))


class MarketplaceComparisonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")
        cls.other = Marketplace.objects.create(name="Halyk Market")
        cls.product = Product.objects.create(name="Same title", category="Office")
        cls.demo = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Demo", price="100", is_demo=True)
        cls.supplied = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Supplied", price="900", is_demo=False)
        cls.foreign = Offer.objects.create(product=cls.product, marketplace=cls.other, seller_name="Other", price="500", is_demo=False)
        for offer in (cls.demo, cls.supplied, cls.foreign):
            PriceObservation.objects.create(offer=offer, price=offer.price, is_demo=offer.is_demo)

    def test_no_combined_benchmark_or_chart_across_provenance_or_marketplaces(self):
        for url in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
            response = self.client.get(url)
            self.assertEqual(response.context["summary"]["count"], 3)
            self.assertIsNone(response.context["summary"]["average"])
            groups = response.context["comparison_groups"]
            self.assertEqual(len(groups), 3)
            self.assertEqual({g["summary"]["average"] for g in groups}, {Decimal("100"), Decimal("900"), Decimal("500")})
            self.assertContains(response, "Fictional and supplied prices are never combined")
        detail = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertIsNone(detail.context["chart"])
        self.assertEqual(len(detail.context["charts"]), 3)
        for group in detail.context["charts"]:
            self.assertEqual(len(group["chart"]["points"]), 1)

    def test_marketplace_and_provenance_filter_scope_offers_summary_and_history(self):
        for kind, offer in (("demo", self.demo), ("non_demo", self.supplied)):
            for url in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
                response = self.client.get(url, {"marketplace": self.market.pk, "data_kind": kind})
                self.assertEqual([o.pk for o in response.context["offers"]], [offer.pk])
                self.assertEqual(response.context["summary"]["average"], Decimal(offer.price))
                if response.context.get("observations"):
                    self.assertEqual([o.offer_id for o in response.context["observations"]], [offer.pk])

    def test_invalid_scope_is_empty_not_unfiltered(self):
        for url in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
            for params in ({"data_kind": "live"}, {"marketplace": "invalid"}):
                response = self.client.get(url, params)
                self.assertEqual(response.context["offers"], [])
                self.assertEqual(response.context["summary"]["count"], 0)

    def test_observation_provenance_is_preserved_independently_of_current_offer_flag(self):
        earlier_demo = PriceObservation.objects.create(offer=self.supplied, price="50", is_demo=True)
        url = reverse("core:product_detail", args=[self.product.pk])
        response = self.client.get(url, {"data_kind": "non_demo", "marketplace": self.market.pk})
        self.assertEqual(len(response.context["observations"]), 1)
        self.assertFalse(response.context["observations"][0].is_demo)
        self.assertTrue(PriceObservation.objects.filter(pk=earlier_demo.pk).exists())
        unfiltered = self.client.get(url)
        self.assertEqual(len(unfiltered.context["observations"]), 4)

    def test_provenance_filter_survives_pagination_with_search_and_sort(self):
        Offer.objects.bulk_create([Offer(product=self.product, marketplace=self.market, seller_name=f"Test {i}", price="101", is_demo=True) for i in range(23)])
        response = self.client.get(reverse("core:product_search"), {
            "marketplace": self.market.pk, "data_kind": "demo", "q": "Same", "sort": "price_desc", "page": 2,
        })
        self.assertEqual(response.context["page_obj"].paginator.count, 24)
        self.assertEqual(len(response.context["offers"]), 4)
        self.assertContains(response, "data_kind=demo")
        self.assertContains(response, "sort=price_desc")
        self.assertContains(response, "q=Same")
        self.assertTrue(all(o.is_demo and o.marketplace_id == self.market.pk for o in response.context["offers"]))

    def test_rejected_offer_does_not_contribute_to_scoped_summary_or_chart(self):
        self.demo.match_status, self.demo.match_notes = "rejected", "Wrong variant"
        self.demo.save()
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]), {"data_kind": "demo"})
        self.assertEqual(response.context["summary"]["count"], 0)
        self.assertEqual(response.context["charts"], [])
        self.assertEqual(len(response.context["offers"]), 1)
        self.assertEqual(PriceObservation.objects.count(), 3)

    def test_source_coverage_counts_are_real_not_hardcoded_demo_numbers(self):
        response = self.client.get(reverse("core:data_sources"))
        coverage = {m.pk: (m.demo_count, m.supplied_count) for m in response.context["marketplace_coverage"]}
        self.assertEqual(coverage, {self.market.pk: (1, 1), self.other.pk: (0, 1)})
        self.assertContains(response, f'?marketplace={self.market.pk}')

    def test_multiple_charts_have_distinct_accessible_identifiers(self):
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        for group in response.context["charts"]:
            ident = group["identifier"]
            self.assertContains(response, f'id="chart-title-{ident}"', count=1)
            self.assertContains(response, f'aria-labelledby="chart-title-{ident} chart-description-{ident}"', count=1)
