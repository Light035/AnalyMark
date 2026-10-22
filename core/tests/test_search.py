from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.comparison import listed_price_summary
from core.models import Marketplace, Offer, Product


class ListedPriceSummaryTests(SimpleTestCase):
    def test_empty_prices_produce_unavailable_statistics(self):
        self.assertEqual(listed_price_summary([]), dict(count=0, minimum=None, maximum=None, average=None, median=None))

    def test_invalid_prices_are_excluded(self):
        summary = listed_price_summary([None, Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), Decimal("0"), Decimal("12.50")])
        self.assertEqual(summary, dict(count=1, minimum=Decimal("12.50"), maximum=Decimal("12.50"), average=Decimal("12.50"), median=Decimal("12.50")))

    def test_average_and_even_median_round_half_up_to_cents(self):
        summary = listed_price_summary([Decimal("0.10"), Decimal("0.11")])
        self.assertEqual(summary["average"], Decimal("0.11"))
        self.assertEqual(summary["median"], Decimal("0.11"))


class ProductSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.kaspi = Marketplace.objects.create(name="Kaspi.kz")
        cls.practice = Marketplace.objects.create(name="Practice market")
        cls.alpha = Product.objects.create(name="Alpha Lamp", brand="NuraLab", category="Lighting")
        cls.beta = Product.objects.create(name="Beta Lamp", brand="OtherBrand", category="Lighting")
        cls.a = Offer.objects.create(product=cls.alpha, marketplace=cls.kaspi, seller_name="One", price=Decimal("100.10"), delivery_cost=Decimal("200"), discount=Decimal("0"), product_url="https://catalog.example/alpha")
        cls.b = Offer.objects.create(product=cls.alpha, marketplace=cls.practice, seller_name="Two", price=Decimal("200.20"), delivery_cost=Decimal("0"), discount=Decimal("20.20"))
        cls.c = Offer.objects.create(product=cls.alpha, marketplace=cls.kaspi, seller_name="Three", price=Decimal("300.30"), delivery_cost=None, discount=Decimal("0"))
        cls.d = Offer.objects.create(product=cls.beta, marketplace=cls.practice, seller_name="Four", price=Decimal("400.40"), delivery_cost=Decimal("0"), discount=None)

    def search(self, **params):
        return self.client.get(reverse("core:product_search"), params)

    def test_search_by_product_name(self):
        response = self.search(q="aLpHa")
        self.assertEqual({offer.pk for offer in response.context["offers"]}, {self.a.pk, self.b.pk, self.c.pk})
        self.assertEqual(response.context["form"]["q"].value(), "aLpHa")

    def test_search_by_brand_and_ignore_surrounding_whitespace(self):
        response = self.search(q=" nuralab ")
        self.assertEqual({offer.product_id for offer in response.context["offers"]}, {self.alpha.pk})
        self.assertEqual(len(response.context["offers"]), 3)

    def test_marketplace_filter(self):
        response = self.search(marketplace=self.kaspi.pk)
        self.assertEqual({offer.pk for offer in response.context["offers"]}, {self.a.pk, self.c.pk})

    def test_combined_filters_use_only_the_intersection(self):
        response = self.search(q="Alpha", marketplace=self.practice.pk)
        self.assertEqual([offer.pk for offer in response.context["offers"]], [self.b.pk])
        self.assertEqual(response.context["summary"]["average"], Decimal("200.20"))

    def test_saved_product_comparison_uses_exact_identity(self):
        similar = Product.objects.create(name="Alpha Lamp bundle", brand="NuraLab", category="Lighting")
        Offer.objects.create(product=similar, marketplace=self.kaspi, seller_name="Bundle", price="999")
        response = self.search(product=self.alpha.pk)
        self.assertEqual({offer.product_id for offer in response.context["offers"]}, {self.alpha.pk})
        self.assertEqual(response.context["summary"]["count"], 3)
        self.assertContains(response, "Comparing this saved product")

    def test_invalid_saved_product_filter_is_explained(self):
        response = self.search(product=99999)
        self.assertContains(response, "Check your filters")
        self.assertEqual(response.context["offers"], [])

    def test_name_sorting_in_both_directions(self):
        for sort, descending in (("name", False), ("name_desc", True)):
            with self.subTest(sort=sort):
                names = [offer.product.name for offer in self.search(sort=sort).context["offers"]]
                self.assertEqual(names, sorted(names, reverse=descending))

    def test_listed_price_sorting_in_both_directions(self):
        for sort, expected in (("price", [self.a, self.b, self.c, self.d]), ("price_desc", [self.d, self.c, self.b, self.a])):
            with self.subTest(sort=sort):
                self.assertEqual([o.pk for o in self.search(sort=sort).context["offers"]], [o.pk for o in expected])

    def test_total_sorting_uses_totals_and_keeps_unknowns_last(self):
        for sort, expected in (("total", [self.b, self.a]), ("total_desc", [self.a, self.b])):
            with self.subTest(sort=sort):
                offers = self.search(sort=sort).context["offers"]
                self.assertEqual([o.pk for o in offers[:2]], [o.pk for o in expected])
                self.assertEqual({o.pk for o in offers[2:]}, {self.c.pk, self.d.pk})

    def test_summary_uses_listed_prices_not_buyer_totals(self):
        summary = self.search().context["summary"]
        self.assertEqual(summary, dict(count=4, minimum=Decimal("100.10"), maximum=Decimal("400.40"), average=Decimal("250.25"), median=Decimal("250.25")))

    def test_odd_median_and_filtered_benchmarks(self):
        summary = self.search(q="Alpha").context["summary"]
        self.assertEqual(summary, dict(count=3, minimum=Decimal("100.10"), maximum=Decimal("300.30"), average=Decimal("200.20"), median=Decimal("200.20")))
        self.assertEqual(self.search(marketplace=self.kaspi.pk).context["summary"]["count"], 2)

    def test_empty_search_results_do_not_display_zero_benchmarks(self):
        response = self.search(q="No such product")
        self.assertContains(response, "No matching offers")
        self.assertEqual(response.context["summary"]["count"], 0)
        self.assertIsNone(response.context["summary"]["minimum"])
        self.assertContains(response, "Unavailable", count=4)

    def test_invalid_filters_are_explained_without_showing_unfiltered_data(self):
        for params in ({"marketplace": "bad"}, {"marketplace": 9999}, {"sort": "unsafe"}, {"q": "x" * 201}):
            with self.subTest(params=params):
                response = self.search(**params)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Check your filters")
                self.assertEqual(response.context["offers"], [])

    def test_error_summary_links_to_visible_fields_but_not_hidden_filters(self):
        response = self.search(marketplace=99999, sort="invalid")
        for name in ("marketplace", "sort"):
            self.assertContains(response, f'href="#id_{name}"')
            self.assertContains(response, f'id="id_{name}_error"')
        self.assertContains(response, 'aria-invalid="true"')
        response = self.search(product=99999)
        self.assertContains(response, "The saved product filter is invalid")
        self.assertNotContains(response, 'href="#id_product"')

    def test_demo_disclosures_and_statistic_scope_are_visible(self):
        response = self.search()
        self.assertContains(response, "Demonstration data · not live", count=4)
        self.assertContains(response, "invented demonstration data")
        self.assertContains(response, "not the entire marketplace")
        self.assertContains(response, "Listed-price benchmarks")
        self.assertContains(response, "Delivery and discounts are excluded")
        self.assertContains(response, "automatic product matching is not implemented")

    def test_missing_amounts_and_example_urls_are_explained(self):
        response = self.search()
        self.assertContains(response, "Total unavailable: delivery information missing.")
        self.assertContains(response, "Total unavailable: discount information missing.")
        self.assertContains(response, "https://catalog.example/alpha")
        self.assertContains(response, "Illustrative link; may not resolve.")
        self.assertContains(response, "Product URL not provided")

    def test_zero_total_is_displayed_as_known(self):
        offer = Offer.objects.create(product=self.beta, marketplace=self.kaspi, seller_name="Free sample", price=Decimal("5"), delivery_cost=Decimal("0"), discount=Decimal("5"))
        response = self.search(q="Beta", marketplace=self.kaspi.pk)
        self.assertEqual(response.context["offers"][0].pk, offer.pk)
        self.assertContains(response, '0.00 <small>KZT</small>', count=2)
        self.assertNotContains(response, "Total unavailable:")

    def test_manual_records_are_not_labeled_live_or_demo(self):
        Offer.objects.filter(pk=self.d.pk).update(is_demo=False)
        response = self.search(q="Beta")
        self.assertContains(response, "Manually entered · unverified")
        self.assertNotContains(response, "Demonstration data · not live")
