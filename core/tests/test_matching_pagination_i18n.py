from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone, translation

from core.admin import OfferReviewForm, ProductAdmin
from core.comparison import queryset_price_summary
from core.importing import run_import
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, SourceOffer, SourceProduct, WatchlistEntry
from core.tests.test_importing import sample


class MatchingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")
        cls.product = Product.objects.create(name="Exact variant", brand="Brand", category="Lighting")
        cls.staff = get_user_model().objects.create_superuser(username="reviewer", password="test-only")
        cls.user = get_user_model().objects.create_user(username="ordinary")

    def offer(self, **values):
        return Offer.objects.create(product=self.product, marketplace=self.market, seller_name="Seller", price="100.10", **values)

    def test_default_is_unreviewed_and_review_requires_reason(self):
        offer = self.offer()
        self.assertEqual(offer.match_status, "unreviewed")
        self.assertIsNone(offer.match_reviewed_at)
        for status in ("confirmed", "rejected"):
            offer.match_status, offer.match_notes = status, "   "
            with self.assertRaises(ValidationError):
                offer.full_clean()
            offer.match_notes = "Compared variant, model and bundle against source reference."
            offer.full_clean()

    def test_database_rejects_unknown_status(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.offer(match_status="verified-by-ai")

    def test_rejected_offers_remain_visible_but_leave_benchmarks_and_product_chart(self):
        rejected = self.offer(match_status="rejected", match_notes="Wrong variant")
        valid = Offer.objects.create(product=self.product, marketplace=self.market, seller_name="Other", price="200.20")
        PriceObservation.objects.create(offer=rejected, price="100.10")
        PriceObservation.objects.create(offer=valid, price="200.20")
        for url in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
            response = self.client.get(url)
            self.assertEqual(response.context["summary"]["count"], 1)
            self.assertEqual(response.context["summary"]["average"], Decimal("200.20"))
            self.assertEqual(len(response.context["offers"]), 2)
            self.assertContains(response, "Rejected association")
            self.assertContains(response, "Provisional benchmarks")
        detail = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertEqual(len(detail.context["chart"]["points"]), 1)
        self.assertEqual(PriceObservation.objects.count(), 2)
        self.assertContains(self.client.get(reverse("core:price_history", args=[rejected.pk])), "100.10")

    def test_confirmation_does_not_change_demo_flag_totals_or_identity(self):
        offer = self.offer(match_status="confirmed", match_notes="Exact model checked", delivery_cost=None, discount="0")
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertContains(response, "Manually confirmed match")
        self.assertContains(response, "Demonstration data · not live")
        self.assertContains(response, "price and source remain unverified")
        self.assertIsNone(offer.total_buyer_cost)
        self.assertEqual(Offer.objects.get().product_id, self.product.pk)

    def test_admin_review_requires_authorization_and_csrf_and_records_reviewer(self):
        offer = self.offer()
        url = reverse("admin:core_offer_change", args=[offer.pk])
        data = {"product": self.product.pk, "marketplace": self.market.pk, "seller_name": "Seller", "price": "100.10",
                "is_demo": "on", "match_status": "confirmed", "match_notes": "Exact variant and bundle checked", "_save": "Save"}
        data.update(match_reviewed_by=self.user.pk, match_reviewed_at="2099-01-01")
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(Offer.objects.get(pk=offer.pk).match_status, "unreviewed")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        client.get(url)
        self.assertEqual(client.post(url, data).status_code, 403)
        self.assertEqual(Offer.objects.get(pk=offer.pk).match_status, "unreviewed")
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertEqual(client.post(url, data).status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "confirmed")
        self.assertEqual(offer.match_reviewed_by, self.staff)
        self.assertIsNotNone(offer.match_reviewed_at)

    def test_admin_refuses_unconfirmed_reassignment(self):
        offer = self.offer()
        other = Product.objects.create(name="Similar name but different bundle", category="Lighting")
        form = OfferReviewForm(instance=offer, data={"product": other.pk, "marketplace": self.market.pk,
            "seller_name": "Seller", "price": "100.10", "is_demo": True, "match_status": "unreviewed"})
        self.assertFalse(form.is_valid())
        self.assertIn("confirmed manual review", str(form.errors))
        self.assertEqual(Offer.objects.get().product_id, self.product.pk)

    def test_import_price_changes_keep_review_identity_changes_reset_it(self):
        class Provider:
            kind = "csv"
            record = sample()
            def fetch(self):
                return [self.record]
        from dataclasses import replace
        provider = Provider()
        run_import(provider, key="review-test", marketplace=self.market, apply=True)
        imported = SourceOffer.objects.get().offer
        imported.match_status, imported.match_notes = "confirmed", "Exact variant checked"
        imported.save()
        provider.record = replace(provider.record, listed_price=Decimal("1300"))
        run_import(provider, key="review-test", marketplace=self.market, apply=True)
        imported.refresh_from_db()
        self.assertEqual(imported.match_status, "confirmed")
        provider.record = replace(provider.record, product_name="Changed variant")
        run_import(provider, key="review-test", marketplace=self.market, apply=True)
        imported.refresh_from_db()
        self.assertEqual(imported.match_status, "unreviewed")
        self.assertEqual(SourceProduct.objects.get().external_id, "variant-1")
        self.assertIsNone(imported.match_reviewed_by)
        provider.record = replace(provider.record, seller_name="Changed seller")
        run_import(provider, key="review-test", marketplace=self.market, apply=True)
        self.assertEqual(Offer.objects.filter(product_id=imported.product_id).count(), 1)

    def test_manual_product_metadata_edit_resets_existing_reviews(self):
        offer = self.offer(match_status="rejected", match_notes="Old variant evidence")
        product = Product.objects.get(pk=self.product.pk)
        product.name = "Changed identity"
        model_admin = ProductAdmin(Product, admin.site)
        model_admin.save_model(RequestFactory().post("/admin/"), product, SimpleNamespace(changed_data=["name"]), True)
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "unreviewed")

    def test_rejected_history_has_an_honest_excluded_empty_state(self):
        offer = self.offer(match_status="rejected", match_notes="Different variant")
        PriceObservation.objects.create(offer=offer, price="100.10")
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertContains(response, "No eligible observations")
        self.assertNotContains(response, "No observations recorded")
        self.assertEqual(PriceObservation.objects.count(), 1)

    def test_imported_source_identity_cannot_be_reassigned_in_admin(self):
        source = DataSource.objects.create(key="stable-source", marketplace=self.market, is_demo=True)
        SourceProduct.objects.create(source=source, product=self.product, external_id="source-variant")
        offer = self.offer()
        SourceOffer.objects.create(source=source, offer=offer, external_id="source-offer", imported_at=timezone.now(), source_url="https://catalog.example/a")
        other = Product.objects.create(name="Unrelated", category="Other")
        self.client.force_login(self.staff)
        response = self.client.post(reverse("admin:core_offer_change", args=[offer.pk]), {
            "product":other.pk,"marketplace":self.market.pk,"seller_name":"Seller","price":"100.10",
            "match_status":"confirmed","match_notes":"Source variant checked","_save":"Save"})
        self.assertEqual(response.status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(offer.product_id, self.product.pk)
        self.assertEqual(offer.match_status, "confirmed")
        self.assertTrue(offer.is_demo)
        self.assertEqual(SourceProduct.objects.get().external_id, "source-variant")

    def test_dry_run_identity_update_rolls_back_review_reset(self):
        class Provider:
            kind = "csv"
            record = sample()
            def fetch(self): return [self.record]
        from dataclasses import replace
        provider = Provider()
        run_import(provider, key="dry-review", marketplace=self.market, apply=True)
        offer = SourceOffer.objects.get().offer
        offer.match_status, offer.match_notes = "confirmed", "Exact source model"
        offer.save()
        provider.record = replace(provider.record, product_name="A different variant")
        run_import(provider, key="dry-review", marketplace=self.market, apply=False)
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "confirmed")
        self.assertEqual(offer.product.name, sample().product_name)


class PaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")
        cls.product = Product.objects.create(name="Тестовый товар", brand="БРЕНД", category="Test")
        Offer.objects.bulk_create([Offer(product=cls.product, marketplace=cls.market, seller_name=f"Seller {i:03}",
            price=Decimal(i) + Decimal("0.01"), delivery_cost=None if i % 2 else Decimal("0"), discount=Decimal("0")) for i in range(1, 62)])

    def test_search_pages_are_bounded_and_statistics_cover_all_results(self):
        responses = [self.client.get("/products/", {"sort": "price", "page": p}) for p in range(1, 5)]
        ids = [o.pk for r in responses for o in r.context["offers"]]
        self.assertEqual(len(ids), 61)
        self.assertEqual(len(set(ids)), 61)
        self.assertEqual([len(r.context["offers"]) for r in responses], [20, 20, 20, 1])
        for response in responses:
            self.assertEqual(response.context["summary"]["count"], 61)
            self.assertEqual(response.context["summary"]["median"], Decimal("31.01"))
            self.assertEqual(response.context["summary"]["average"], Decimal("31.01"))

    def test_pagination_queries_do_not_load_unbounded_offer_rows(self):
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get("/products/", {"page": 2, "sort": "price"})
        self.assertEqual(len(response.context["offers"]), 20)
        row_queries = [q["sql"] for q in captured if 'SELECT "core_offer"."id"' in q["sql"]]
        self.assertTrue(row_queries)
        self.assertTrue(all("LIMIT 20" in q for q in row_queries))
        median_queries = [q["sql"] for q in captured if "AS \"_cents\"" in q["sql"] and "ORDER BY" in q["sql"]]
        self.assertTrue(any("LIMIT 1" in q for q in median_queries))

    def test_safe_invalid_and_out_of_range_pages(self):
        for raw in ("bad", "0", "-1", "1.5", "9" * 5000, "٢"):
            with self.subTest(raw=raw[:10]):
                self.assertEqual(self.client.get("/products/", {"page": raw}).context["page_obj"].number, 1)
        self.assertEqual(self.client.get("/products/", {"page": "999"}).context["page_obj"].number, 4)

    def test_links_preserve_filters_sort_review_and_exact_product(self):
        params = {"q": "товар", "marketplace": self.market.pk, "sort": "total_desc", "product": self.product.pk, "review": "unreviewed"}
        response = self.client.get("/products/", params)
        from html.parser import HTMLParser
        class Links(HTMLParser):
            next_url = None
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("rel") == "next": self.next_url = attrs["href"]
        links = Links(); links.feed(response.content.decode())
        self.assertIsNotNone(links.next_url)
        parsed = parse_qs(urlsplit(links.next_url).query)
        for key, value in params.items(): self.assertEqual(parsed[key], [str(value)])
        self.assertEqual(parsed["page"], ["2"])

    def test_unicode_search_is_case_insensitive_without_python_catalog_scan(self):
        response = self.client.get("/products/", {"q": "тЕсТоВыЙ"})
        self.assertEqual(response.context["page_obj"].paginator.count, 61)
        self.assertEqual(self.client.get("/products/", {"q": "бренд"}).context["summary"]["count"], 61)

    def test_empty_results_and_invalid_review_do_not_fall_back_to_all_offers(self):
        for params in ({"q": "absent", "page": 999}, {"review": "invented"}):
            response = self.client.get("/products/", params)
            self.assertEqual(response.context["offers"], [])
            self.assertEqual(response.context["page_obj"].paginator.count, 0)
            self.assertIsNone(response.context["summary"]["median"])

    def test_total_sort_keeps_unknowns_last_across_pages(self):
        offers = [o for page in range(1, 5) for o in self.client.get("/products/", {"sort": "total_desc", "page": page}).context["offers"]]
        self.assertTrue(all(o.total_buyer_cost is not None for o in offers[:30]))
        self.assertTrue(all(o.total_buyer_cost is None for o in offers[30:]))
        self.assertEqual(offers[0].total_buyer_cost, Decimal("60.01"))

    def test_product_offers_and_history_have_independent_bounded_pages(self):
        offer = Offer.objects.first()
        PriceObservation.objects.bulk_create([PriceObservation(offer=offer, price="10.01", observed_at=timezone.now()) for _ in range(55)])
        url = reverse("core:product_detail", args=[self.product.pk])
        response = self.client.get(url, {"offers_page": 2, "history_page": 2})
        self.assertEqual(len(response.context["offers"]), 20)
        self.assertEqual(len(response.context["observations"]), 5)
        self.assertEqual(len(response.context["chart"]["points"]), 5)
        self.assertEqual(response.context["summary"]["count"], 61)
        self.assertContains(response, "this history page only")
        self.assertContains(response, "history_page=2")
        history = self.client.get(reverse("core:price_history", args=[offer.pk]), {"page": 2})
        self.assertEqual(len(history.context["observations"]), 5)

    def test_catalog_watchlist_and_sources_paginate_in_stable_order(self):
        user = get_user_model().objects.create_user(username="paged-watchlist")
        products = Product.objects.bulk_create([Product(name=f"Product {i:03}", category="Test") for i in range(25)])
        WatchlistEntry.objects.bulk_create([WatchlistEntry(user=user, product=p) for p in products])
        self.client.force_login(user)
        response = self.client.get("/watchlist/", {"page": 2})
        self.assertEqual(len(response.context["entries"]), 5)
        response = self.client.get("/analytics/", {"page": 2})
        self.assertEqual(len(response.context["products"]), 6)
        DataSource.objects.bulk_create([DataSource(key=f"source-{i:03}", marketplace=self.market) for i in range(25)])
        self.assertEqual(len(self.client.get("/data-sources/", {"page": 2}).context["data_sources"]), 5)
        self.assertEqual(len(self.client.get("/").context["data_sources"]), 5)

    def test_sql_money_aggregates_round_half_up_without_float_drift(self):
        Offer.objects.all().delete()
        Offer.objects.bulk_create([Offer(product=self.product, marketplace=self.market, seller_name=str(i), price=p) for i,p in enumerate(("0.10", "0.11"))])
        summary = queryset_price_summary(Offer.objects.all())
        self.assertEqual(summary["average"], Decimal("0.11"))
        self.assertEqual(summary["median"], Decimal("0.11"))


class RussianInterfaceTests(TestCase):
    def test_switch_language_requires_csrf_and_preserves_current_query(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/products/?q=Luma&sort=price&page=2")
        target = "/products/?q=Luma&sort=price&page=2"
        self.assertEqual(client.post(reverse("set_language"), {"language":"ru", "next":target}).status_code, 403)
        response = client.post(reverse("set_language"), {"language":"ru", "next":target, "csrfmiddlewaretoken":client.cookies["csrftoken"].value})
        self.assertEqual(response["Location"], target)
        response = client.get(target)
        self.assertContains(response, '<html lang="ru">')
        self.assertContains(response, "Поиск товаров")
        self.assertContains(response, "Онлайн-данные не подключены.")
        self.assertContains(response, "Страница 1 из 1")
        client.post(reverse("set_language"), {"language":"en", "next":target, "csrfmiddlewaretoken":client.cookies["csrftoken"].value})
        self.assertContains(client.get(target), '<html lang="en">')

    def test_russian_public_pages_and_watchlist_render_without_changing_records(self):
        product = Product.objects.create(name="Original product name", category="Original category")
        market = Marketplace.objects.create(name="Kaspi.kz")
        offer = Offer.objects.create(product=product, marketplace=market, seller_name="Demo seller", price="100.10")
        for url in ("/", "/products/", "/analytics/", "/data-sources/", "/accounts/login/", f"/products/{product.pk}/", f"/offers/{offer.pk}/history/"):
            response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="ru")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, '<html lang="ru">')
            self.assertContains(response, "Онлайн-данные не подключены.")
        self.assertContains(self.client.get("/products/", HTTP_ACCEPT_LANGUAGE="ru"), "Связь не проверена")
        product.refresh_from_db()
        self.assertEqual(product.name, "Original product name")
        self.assertFalse(PriceObservation.objects.exists())

    def test_russian_plural_forms_and_compiled_catalog_are_current(self):
        from tools.compile_translations import compile_catalog
        path = Path(__file__).resolve().parents[2] / "locale/ru/LC_MESSAGES/django.po"
        self.assertEqual(compile_catalog(path), path.with_suffix(".mo").read_bytes())
        with translation.override("ru"):
            for count, ending in ((1,"предложение"),(2,"предложения"),(5,"предложений"),(22,"предложения")):
                self.assertTrue(translation.ngettext("%(count)s offer", "%(count)s offers", count).endswith(ending))
            self.assertEqual(str(Offer.MatchStatus.CONFIRMED.label), "Соответствие подтверждено вручную")

    def test_language_redirect_does_not_accept_external_destination(self):
        response = self.client.post(reverse("set_language"), {"language":"ru", "next":"https://untrusted.example/"})
        self.assertFalse(response["Location"].startswith("https://untrusted.example"))

    def test_static_translation_keys_are_present_in_the_russian_catalog(self):
        import ast
        import gettext
        from django.template.base import Lexer, TokenType
        from django.utils.text import unescape_string_literal
        root = Path(__file__).resolve().parents[2]
        with (root / "locale/ru/LC_MESSAGES/django.mo").open("rb") as stream:
            catalog = gettext.GNUTranslations(stream)._catalog
        keys = set()
        for relative in ("core/forms.py","core/models.py","core/admin.py","core/views.py","core/urls.py"):
            for node in ast.walk(ast.parse((root / relative).read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_" and node.args and isinstance(node.args[0], ast.Constant):
                    keys.add(node.args[0].value)
        for path in [*(root / "templates").rglob("*.html"), *(root / "core/templates").rglob("*.html")]:
            for token in Lexer(path.read_text(encoding="utf-8")).tokenize():
                if token.token_type == TokenType.BLOCK:
                    parts = token.split_contents()
                    if parts[0] == "translate" and parts[1][0] in "\"'":
                        keys.add(unescape_string_literal(parts[1]))
        self.assertEqual(sorted(keys - catalog.keys()), [])
