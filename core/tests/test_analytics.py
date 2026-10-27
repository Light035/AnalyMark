from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.history import observation_chart
from core.models import Marketplace, Offer, PriceObservation, Product, WatchlistEntry


class EmptyWorkspaceTests(TestCase):
    def test_dashboard_uses_zero_counts_and_honest_empty_states(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        metrics = response.context["metrics"]
        for name in ("products", "offers", "marketplaces", "observations", "demo_offers", "demo_observations"):
            self.assertEqual(metrics[name], 0)
        self.assertIsNone(metrics["watchlist"])
        self.assertIsNone(response.context["latest_observation"])
        self.assertContains(response, "No products loaded")
        self.assertContains(response, "No price observations recorded")
        self.assertNotContains(response, '<span class="card-kicker">Your Watchlist</span>')

    def test_analytics_empty_state(self):
        response = self.client.get(reverse("core:analytics"))
        self.assertContains(response, "No products to analyze")
        self.assertFalse(PriceObservation.objects.exists())


class ProductAnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = get_user_model().objects.create_user(username="analytics-alice")
        cls.bob = get_user_model().objects.create_user(username="analytics-bob")
        cls.product = Product.objects.create(name="Luma lamp", brand="DemoBrand", category="Lighting")
        cls.similar = Product.objects.create(name="Luma lamp bundle", brand="DemoBrand", category="Lighting")
        cls.market = Marketplace.objects.create(name="Kaspi.kz")
        cls.practice = Marketplace.objects.create(name="Halyk Market")
        cls.a = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Cedar", price="100.10", delivery_cost="200", discount="0")
        cls.b = Offer.objects.create(product=cls.product, marketplace=cls.practice, seller_name="Mosaic", price="200.20", delivery_cost="0", discount="20.20", is_demo=False)
        cls.c = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Paper", price="300.30", delivery_cost=None, discount="0")
        cls.d = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Tumar", price="400.40", delivery_cost="0", discount=None)
        cls.unrelated = Offer.objects.create(product=cls.similar, marketplace=cls.market, seller_name="Bundle-only seller", price="9999")
        now = timezone.now()
        # Insert out of chronological order to test ordering against stored timestamps.
        cls.newest = PriceObservation.objects.create(offer=cls.a, price="120", observed_at=now)
        cls.oldest = PriceObservation.objects.create(offer=cls.a, price="110", observed_at=now - timedelta(minutes=2))
        cls.middle = PriceObservation.objects.create(offer=cls.b, price="210", observed_at=now - timedelta(minutes=1), is_demo=False)
        PriceObservation.objects.create(offer=cls.unrelated, price="9999", observed_at=now)
        WatchlistEntry.objects.create(user=cls.alice, product=cls.product)
        WatchlistEntry.objects.create(user=cls.bob, product=cls.product)
        WatchlistEntry.objects.create(user=cls.bob, product=cls.similar)

    def detail(self, product=None):
        return self.client.get(reverse("core:product_detail", args=[(product or self.product).pk]))

    def test_dashboard_counts_actual_records_and_source_flags(self):
        response = self.client.get(reverse("core:dashboard"))
        metrics = response.context["metrics"]
        self.assertEqual(metrics, {
            "products": 2, "offers": 5, "marketplaces": 2, "observations": 4,
            "demo_offers": 4, "unverified_offers": 1, "demo_observations": 3,
            "unverified_observations": 1, "watchlist": None,
        })
        self.assertEqual(response.context["latest_observation"], self.newest.observed_at)
        self.assertContains(response, "Neither is verified live marketplace data")
        self.assertContains(response, "not a marketplace refresh time")
        self.assertNotContains(response, '<span class="card-kicker">Your Watchlist</span>')

    def test_dashboard_watchlist_metric_is_private_to_the_current_user(self):
        for user, expected in ((self.alice, 1), (self.bob, 2)):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse("core:dashboard"))
                self.assertEqual(response.context["metrics"]["watchlist"], expected)
                self.assertContains(response, '<span class="card-kicker">Your Watchlist</span>')

    def test_dashboard_counts_change_with_database_records(self):
        Product.objects.create(name="New catalog record", category="Other")
        Marketplace.objects.create(name="Teez")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.context["metrics"]["products"], 3)
        self.assertEqual(response.context["metrics"]["marketplaces"], 3)

    def test_product_is_public_read_only_and_unknown_id_is_not_found(self):
        url = reverse("core:product_detail", args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/product_detail.html")
        self.assertContains(response, "DemoBrand")
        self.assertContains(response, "Lighting")
        self.assertEqual(self.client.head(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(reverse("core:product_detail", args=[99999])).status_code, 404)

    def test_product_offer_filter_never_uses_similar_names_or_query_override(self):
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]), {"product": self.similar.pk})
        self.assertEqual({o.pk for o in response.context["offers"]}, {self.a.pk, self.b.pk, self.c.pk, self.d.pk})
        self.assertNotContains(response, "Bundle-only seller")
        self.assertNotContains(response, "9,999.00")
        self.assertContains(response, "Product associations are unverified")
        for offer in (self.a, self.b, self.c, self.d):
            self.assertContains(response, f"<h3>{offer.seller_name}</h3>", html=True)

    def test_product_summary_reuses_listed_prices_not_totals_or_other_products(self):
        response = self.detail()
        self.assertIsNone(response.context["summary"]["average"])
        self.assertEqual(next(g["summary"] for g in response.context["comparison_groups"] if g["marketplace"] == "Kaspi.kz"), {
            "count": 3, "minimum": Decimal("100.10"), "maximum": Decimal("400.40"),
            "average": Decimal("266.93"), "median": Decimal("300.30"),
        })
        self.assertTemplateUsed(response, "core/includes/price_summary.html")
        self.assertTemplateUsed(response, "core/includes/offer_card.html")
        self.assertContains(response, "Delivery and discounts are excluded")
        self.assertContains(response, "Each marketplace and provenance type has its own benchmark")
        self.assertContains(response, "Fictional and supplied prices are never combined")

    def test_product_shows_marketplaces_totals_and_unknown_inputs(self):
        response = self.detail()
        self.assertContains(response, "Kaspi.kz")
        self.assertContains(response, "Halyk Market")
        self.assertContains(response, "180.00")
        self.assertContains(response, "Total unavailable: delivery information missing.")
        self.assertContains(response, "Total unavailable: discount information missing.")
        self.assertContains(response, "Demonstration data · not live")
        self.assertContains(response, "Manually entered · unverified")
        self.assertContains(response, "marketplace update times remain unknown")
        self.assertContains(response, "snapshot capture times, not marketplace refresh times")

    def test_product_history_orders_only_its_stored_observations(self):
        response = self.detail()
        expected = [self.oldest.pk, self.middle.pk, self.newest.pk]
        self.assertEqual([o.pk for o in response.context["observations"]], expected)
        self.assertIsNone(response.context["chart"])
        points = [p["observation"] for group in response.context["charts"] for p in group["chart"]["points"]]
        self.assertEqual([p.pk for p in sorted(points, key=lambda p: (p.observed_at, p.pk))], expected)
        self.assertContains(response, 'class="observation-point"', count=3)
        self.assertContains(response, "Demonstration observation · not live")
        self.assertContains(response, "Manually recorded · unverified")
        self.assertContains(response, 'fill="white"')
        self.assertContains(response, timezone.localtime(self.oldest.observed_at).strftime("%Y-%m-%d %H:%M:%S %z"))
        self.assertNotContains(response, "<polyline")
        self.assertContains(response, "No synthetic points or interpolated prices are added")

    def test_missing_history_has_no_chart_or_inferred_points(self):
        PriceObservation.objects.filter(offer__product=self.product).delete()
        response = self.detail()
        self.assertEqual(response.context["observations"], [])
        self.assertIsNone(response.context["chart"])
        self.assertContains(response, "No observations recorded")
        self.assertNotContains(response, 'class="observation-chart"')
        self.assertEqual(PriceObservation.objects.count(), 1)

    def test_product_without_offers_has_unavailable_statistics(self):
        empty = Product.objects.create(name="No offers yet", category="Other")
        response = self.detail(empty)
        self.assertEqual(response.context["summary"]["count"], 0)
        self.assertIsNone(response.context["summary"]["average"])
        self.assertContains(response, "No offers for this product")
        self.assertContains(response, "Unavailable", count=4)
        self.assertContains(response, "No observations recorded")

    def test_anonymous_watchlist_control_links_to_login(self):
        response = self.detail()
        self.assertFalse(response.context["is_saved"])
        self.assertContains(response, "Log in to save product")
        self.assertContains(response, f"next=/products/{self.product.pk}/")
        self.assertNotContains(response, "Remove from your Watchlist")

    def test_authenticated_save_remove_controls_do_not_use_another_users_list(self):
        self.client.force_login(self.alice)
        self.assertContains(self.detail(), "Remove from your Watchlist")
        response = self.detail(self.similar)
        self.assertFalse(response.context["is_saved"])
        self.assertContains(response, "Save to your Watchlist")
        self.assertContains(response, f'action="{reverse("core:watchlist_add", args=[self.similar.pk])}"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_product_controls_work_with_enforced_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        url = reverse("core:product_detail", args=[self.similar.pk])
        client.get(url)
        add = reverse("core:watchlist_add", args=[self.similar.pk])
        self.assertEqual(client.post(add).status_code, 403)
        response = client.post(add, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertRedirects(response, reverse("core:watchlist"))
        self.assertContains(client.get(url), "Remove from your Watchlist")
        remove = reverse("core:watchlist_remove", args=[self.similar.pk])
        self.assertRedirects(client.post(remove, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}), reverse("core:watchlist"))
        self.assertTrue(WatchlistEntry.objects.filter(user=self.bob, product=self.similar).exists())

    def test_navigation_connects_search_watchlist_analytics_and_history(self):
        product_url = reverse("core:product_detail", args=[self.product.pk])
        self.assertContains(self.client.get(reverse("core:product_search")), f'href="{product_url}"')
        self.assertContains(self.client.get(reverse("core:analytics")), f'href="{product_url}"')
        self.assertContains(self.client.get(reverse("core:price_history", args=[self.a.pk])), f'href="{product_url}"')
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("core:watchlist")), f'href="{product_url}"')
        response = self.detail()
        self.assertContains(response, f'href="{reverse("core:price_history", args=[self.a.pk])}"')
        self.assertContains(response, f'href="{reverse("core:analytics")}" aria-current="page"')
        self.assertContains(response, 'aria-current="page"', count=1)
        for destination in ("price-benchmarks", "product-offers", "price-history"):
            self.assertContains(response, f'href="#{destination}"')
            self.assertContains(response, f'id="{destination}"')
        content = response.content.decode()
        self.assertLess(content.index('id="product-offers"'), content.index('id="price-history"'))

    def test_chart_and_table_have_accessible_responsive_structure(self):
        response = self.detail()
        for fragment in ('name="viewport"', 'viewBox="0 0 760 290"', 'role="img"', f'aria-labelledby="chart-title-{self.market.pk}-1 chart-description-{self.market.pk}-1"', '<caption>', 'class="table-scroll"', 'tabindex="0"'):
            with self.subTest(fragment=fragment):
                self.assertContains(response, fragment)

    def test_analytics_views_do_not_modify_prices_history_or_saved_entries(self):
        before_observations = list(PriceObservation.objects.order_by("pk").values())
        before_offers = list(Offer.objects.order_by("pk").values())
        before_watchlist = list(WatchlistEntry.objects.order_by("pk").values())
        self.client.get(reverse("core:dashboard"))
        self.client.get(reverse("core:analytics"))
        self.detail()
        self.assertEqual(list(PriceObservation.objects.order_by("pk").values()), before_observations)
        self.assertEqual(list(Offer.objects.order_by("pk").values()), before_offers)
        self.assertEqual(list(WatchlistEntry.objects.order_by("pk").values()), before_watchlist)


class ObservationChartTests(SimpleTestCase):
    def observation(self, pk, price, timestamp, offer_id=1):
        return SimpleNamespace(pk=pk, price=Decimal(price), observed_at=timestamp, offer_id=offer_id, offer=SimpleNamespace(pk=offer_id))

    def test_no_observations_means_no_chart(self):
        self.assertIsNone(observation_chart([]))

    def test_single_time_and_price_are_centered_without_synthetic_points(self):
        observation = self.observation(1, "100.00", timezone.now())
        chart = observation_chart([observation])
        self.assertTrue(chart["single_time"])
        self.assertTrue(chart["single_price"])
        self.assertEqual(len(chart["points"]), 1)
        self.assertEqual(chart["points"][0]["x"], "416.00")
        self.assertEqual(chart["points"][0]["y"], "122.00")

    def test_coordinate_order_comes_from_timestamps_and_keeps_equal_time_points(self):
        now = timezone.now()
        first = self.observation(1, "100.00", now - timedelta(hours=1))
        equal_time = self.observation(2, "200.00", first.observed_at, offer_id=2)
        last = self.observation(3, "150.00", now)
        chart = observation_chart([last, equal_time, first])
        self.assertEqual([p["observation"].pk for p in chart["points"]], [1, 2, 3])
        self.assertEqual(chart["points"][0]["x"], chart["points"][1]["x"])
        self.assertLess(float(chart["points"][0]["x"]), float(chart["points"][2]["x"]))
        self.assertEqual(len(chart["series"]), 2)
        for point in chart["points"]:
            self.assertTrue(112 <= float(point["x"]) <= 720)
            self.assertTrue(24 <= float(point["y"]) <= 220)
