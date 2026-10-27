"""Navigation and data presentation boundaries for the redesigned workspace."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import DataSource, Marketplace, Offer, Product, SourceOffer, SourceProduct, WatchlistEntry


class WorkspacePresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")
        cls.product = Product.objects.create(name="Test variant " + "L" * 170, category="Test category", brand="Test brand")
        cls.demo = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Demo seller", price="9999999999.99")
        cls.manual = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Manual seller", price="100", is_demo=False, delivery_cost="0", discount="0")
        cls.source = DataSource.objects.create(key="test-import", marketplace=cls.market, last_success_at=timezone.now(), status="success")
        cls.imported = Offer.objects.create(product=cls.product, marketplace=cls.market, seller_name="Imported seller", price="200", is_demo=False)
        SourceProduct.objects.create(source=cls.source, product=cls.product, external_id="variant-1")
        SourceOffer.objects.create(source=cls.source, offer=cls.imported, external_id="offer-1", imported_at=cls.source.last_success_at, source_url="https://catalog.example/test/")
        demo_product = Product.objects.create(name="Fictional imported demo", category="Test")
        demo_offer = Offer.objects.create(product=demo_product, marketplace=cls.market, seller_name="Imported demo seller", price="1", is_demo=True)
        demo_source = DataSource.objects.create(key="demo-import", marketplace=cls.market, is_demo=True)
        SourceProduct.objects.create(source=demo_source, product=demo_product, external_id="demo-variant")
        SourceOffer.objects.create(source=demo_source, offer=demo_offer, external_id="demo-offer", imported_at=timezone.now(), source_url="https://catalog.example/demo/")
        cls.user = get_user_model().objects.create_user(username="presentation-user")
        cls.other = get_user_model().objects.create_user(username="other-presentation-user")

    def test_dashboard_composition_is_disjoint_and_uses_actual_records(self):
        response = self.client.get("/")
        self.assertEqual(response.context["data_mix"], {"demo": 2, "imported": 1, "manual": 1})
        self.assertEqual(sum(response.context["data_mix"].values()), response.context["metrics"]["offers"])
        self.assertEqual(response.context["source_summary"], {"total": 2, "errors": 0, "blocked": 0, "never": 1})

    def test_dashboard_counts_failed_and_never_successful_sources_separately(self):
        self.source.status = "error"
        self.source.save()
        response = self.client.get("/")
        self.assertEqual(response.context["source_summary"]["errors"], 1)
        self.assertEqual(response.context["source_summary"]["never"], 1)
        self.assertContains(response, "failed latest import")

    def test_sources_are_public_read_only_and_do_not_expose_staff_errors(self):
        self.source.status = "error"
        self.source.last_error = "Row 3: discount: invalid amount."
        self.source.save()
        url = reverse("core:data_sources")
        response = self.client.get(url)
        self.assertContains(response, "No successful import")
        self.assertContains(response, "--dry-run")
        self.assertContains(response, "--apply")
        self.assertNotContains(response, 'type="file"')
        self.assertNotContains(response, self.source.last_error)
        self.assertEqual(self.client.post(url).status_code, 405)
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(url), self.source.last_error)
        self.user.is_staff = True
        self.user.save()
        self.assertContains(self.client.get(url), self.source.last_error)

    def test_sources_navigation_is_present_and_marks_only_current_page(self):
        response = self.client.get(reverse("core:data_sources"))
        self.assertContains(response, 'href="/data-sources/" aria-current="page"', count=1)
        self.assertContains(response, 'aria-current="page"', count=1)

    def test_active_filters_use_validated_values_and_keep_get_navigation(self):
        response = self.client.get(reverse("core:product_search"), {"q": "Test variant", "marketplace": self.market.pk, "sort": "total_desc", "product": self.product.pk})
        active = response.context["active_filters"]
        self.assertEqual(active["query"], "Test variant")
        self.assertEqual(active["marketplace"], self.market)
        self.assertEqual(active["sort"], "Buyer total: high to low")
        self.assertContains(response, f"Exact product #{self.product.pk}")
        self.assertContains(response, 'method="get"')
        invalid = self.client.get(reverse("core:product_search"), {"marketplace": 999999})
        self.assertIsNone(invalid.context["active_filters"])
        self.assertNotContains(invalid, 'aria-label="Active search filters"')

    def test_comparison_retains_large_money_unknowns_and_provenance(self):
        for url in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
            response = self.client.get(url)
            self.assertTemplateUsed(response, "core/includes/offer_table.html")
            self.assertContains(response, "9,999,999,999.99")
            self.assertContains(response, self.product.name)
            self.assertContains(response, "Unknown")
            self.assertContains(response, "0.00")
            self.assertContains(response, "Unavailable")
            self.assertContains(response, "Source: test-import")
            self.assertContains(response, "Last imported:")
            self.assertContains(response, "not a marketplace update time")
            self.assertContains(response, 'scope="col"')
            self.assertContains(response, 'aria-label="Scrollable offer comparison"')
        self.assertEqual(self.manual.total_buyer_cost, Decimal("100"))

    def test_watchlist_summaries_remain_private_and_removal_is_a_csrf_post(self):
        WatchlistEntry.objects.create(user=self.user, product=self.product)
        other_product = Product.objects.create(name="Other user's private saved item", category="Test")
        WatchlistEntry.objects.create(user=self.other, product=other_product)
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:watchlist"))
        self.assertContains(response, "3 stored offers")
        self.assertContains(response, "Saved to your account")
        self.assertNotContains(response, other_product.name)
        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertEqual(response.context["entries"][0].offer_count, 3)
