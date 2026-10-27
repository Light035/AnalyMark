"""Five-marketplace scope is visibility and ingestion policy, never deletion."""
from importlib import import_module
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.forms import ComparisonScopeForm
from core.importing import run_import
from core.marketplaces import APPROVED_NAMES, initialize_marketplaces
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, RefreshRun, SourceOffer, SourceProduct, WatchlistEntry
from core.providers import InvalidSourceData
from core.refreshing import enqueue_due, enqueue_refresh, execute_refresh
from core.tests.test_importing import sample
from core.tests.test_refresh import Provider


class MarketplaceScopeTests(TestCase):
    def setUp(self):
        self.market = Marketplace.objects.create(name="ForteMarket")
        self.source = DataSource.objects.create(key="user-supplied", marketplace=self.market, provider="csv", is_demo=False)
        self.product = Product.objects.create(name="User-owned historical product", category="Office")
        self.offer = Offer.objects.create(product=self.product, marketplace=self.market, seller_name="User seller",
                                          price="1200", is_demo=False, match_status="confirmed", match_notes="Verified exact variant")
        self.product_id = SourceProduct.objects.create(source=self.source, product=self.product, external_id="source-product")
        self.offer_id = SourceOffer.objects.create(source=self.source, offer=self.offer, external_id="source-offer",
                                                   source_url="https://reference.example/item", imported_at=timezone.now())
        self.observation = PriceObservation.objects.create(offer=self.offer, price="1100", is_demo=False)
        self.user = get_user_model().objects.create_user(username="scope-owner", password="test-only")
        self.entry = WatchlistEntry.objects.create(user=self.user, product=self.product)

    def initialize(self):
        call_command("init_marketplaces", stdout=StringIO())

    def test_exactly_five_active_labels_with_unknown_labels_retained(self):
        Marketplace.objects.create(name="Other user marketplace")
        self.initialize()
        self.initialize()
        self.assertEqual(set(Marketplace.objects.active().values_list("name", flat=True)), set(APPROVED_NAMES))
        self.assertEqual(Marketplace.objects.count(), 7)
        self.market.refresh_from_db()
        self.assertFalse(self.market.is_active)
        self.assertFalse(self.market.is_supported)

    def test_archive_preserves_user_records_and_observations_exactly(self):
        models = (Product, Offer, PriceObservation, SourceProduct, SourceOffer, WatchlistEntry)
        before = [list(model.objects.order_by("pk").values()) for model in models]
        self.initialize()
        self.assertEqual(before, [list(model.objects.order_by("pk").values()) for model in models])
        self.assertEqual(self.source.offers.count(), 1)

    def test_ozon_alias_is_renamed_without_new_identity(self):
        old = Marketplace.objects.create(name="Ozon Kazakhstan", website_url="https://custom.example/")
        source = DataSource.objects.create(key="ozon-supplied", marketplace=old)
        self.initialize()
        old.refresh_from_db(); source.refresh_from_db()
        self.assertEqual(old.name, "Ozon")
        self.assertEqual(old.website_url, "https://custom.example/")
        self.assertEqual(source.marketplace_id, old.pk)
        self.assertFalse(Marketplace.objects.filter(name="Ozon Kazakhstan").exists())

    def test_ozon_collision_archives_alias_without_merging(self):
        old = Marketplace.objects.create(name="Ozon Kazakhstan")
        canonical = Marketplace.objects.create(name="Ozon")
        source = DataSource.objects.create(key="ozon-old-source", marketplace=old)
        self.initialize()
        old.refresh_from_db(); source.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertEqual(source.marketplace_id, old.pk)
        self.assertEqual(Marketplace.objects.active().get(name="Ozon").pk, canonical.pk)

    def test_migration_preserves_identities_and_archives_even_without_commands(self):
        old = Marketplace.objects.create(name="Ozon Kazakhstan")
        migrate = import_module("core.migrations.0009_marketplace_is_active").enforce_scope
        migrate(apps, SimpleNamespace(connection=connection))
        self.market.refresh_from_db(); old.refresh_from_db()
        self.assertFalse(self.market.is_active)
        self.assertEqual(old.name, "Ozon")
        self.assertTrue(PriceObservation.objects.filter(pk=self.observation.pk).exists())
        self.assertTrue(WatchlistEntry.objects.filter(pk=self.entry.pk).exists())

    def test_scope_excludes_unknown_labels_even_before_initialization(self):
        self.assertTrue(self.market.is_active)  # Raw flag is not the allowlist.
        self.assertFalse(self.market.is_supported)
        self.assertEqual(list(ComparisonScopeForm().fields["marketplace"].queryset), [])
        self.assertFalse(Offer.objects.active().exists())

    def test_dashboard_search_catalog_and_sources_hide_archived_records(self):
        self.initialize()
        for route in ("dashboard", "product_search", "analytics", "data_sources"):
            response = self.client.get(reverse(f"core:{route}"))
            self.assertNotContains(response, "ForteMarket")
            self.assertNotContains(response, self.product.name)
            self.assertNotContains(response, self.source.key)
        metrics = self.client.get(reverse("core:dashboard")).context["metrics"]
        self.assertEqual((metrics["products"], metrics["offers"], metrics["observations"], metrics["marketplaces"]), (0, 0, 0, 5))

    def test_archived_filter_id_cannot_restore_archived_offers(self):
        self.initialize()
        for route in (reverse("core:product_search"), reverse("core:product_detail", args=[self.product.pk])):
            response = self.client.get(route, {"marketplace": self.market.pk})
            self.assertEqual(response.context["offers"], [])
            self.assertEqual(response.context["summary"]["count"], 0)

    def test_shared_product_keeps_only_approved_offers_in_comparisons(self):
        kaspi = Marketplace.objects.create(name="Kaspi.kz")
        active = Offer.objects.create(product=self.product, marketplace=kaspi, seller_name="Demo seller", price="2000")
        PriceObservation.objects.create(offer=active, price="2000")
        self.initialize()
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertEqual([o.pk for o in response.context["offers"]], [active.pk])
        self.assertEqual([o.offer_id for o in response.context["observations"]], [active.pk])
        self.assertEqual(response.context["summary"]["count"], 1)
        self.assertTrue(Product.objects.active().filter(pk=self.product.pk).exists())
        self.assertEqual(PriceObservation.objects.count(), 2)

    def test_old_history_link_remains_readable_with_archive_warning(self):
        self.initialize()
        response = self.client.get(reverse("core:price_history", args=[self.offer.pk]))
        self.assertContains(response, "Archived marketplace")
        self.assertContains(response, "1,100.00")
        self.assertEqual([o.pk for o in response.context["observations"]], [self.observation.pk])

    def test_private_watchlist_retains_archived_saved_entry_and_remove_action(self):
        self.initialize()
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:watchlist"))
        self.assertContains(response, "Archived product · saved entry preserved")
        self.assertContains(response, self.product.name)
        self.assertEqual(response.context["entries"][0].offer_count, 0)
        self.assertEqual(self.client.post(reverse("core:watchlist_add", args=[self.product.pk])).status_code, 404)
        self.client.post(reverse("core:watchlist_remove", args=[self.product.pk]))
        self.assertFalse(WatchlistEntry.objects.filter(user=self.user).exists())
        self.assertTrue(PriceObservation.objects.filter(pk=self.observation.pk).exists())

    def test_archived_product_direct_link_is_explicit_not_an_active_listing(self):
        self.initialize()
        response = self.client.get(reverse("core:product_detail", args=[self.product.pk]))
        self.assertContains(response, "Archived catalog record")
        self.assertNotContains(response, "Log in to save product")
        self.assertEqual(response.context["offers"], [])

    def test_archived_csv_rejected_before_provider_access(self):
        self.initialize()
        provider = Provider([sample()])
        with patch.object(provider, "fetch", side_effect=AssertionError("Must not fetch")):
            with self.assertRaises(InvalidSourceData):
                run_import(provider, key=self.source.key, marketplace=self.market, apply=True)
        with self.assertRaises(CommandError):
            call_command("import_offers_csv", "not-used.csv", source=self.source.key, marketplace=self.market.name, apply=True)
        self.assertEqual(Offer.objects.count(), 1)

    def test_marketplace_deactivated_during_fetch_aborts_batch(self):
        kaspi = Marketplace.objects.create(name="Kaspi.kz")
        provider = Provider([sample()])
        def deactivate():
            Marketplace.objects.filter(pk=kaspi.pk).update(is_active=False)
            return [sample()]
        with patch.object(provider, "fetch", side_effect=deactivate), self.assertRaises(InvalidSourceData):
            run_import(provider, key="late-import", marketplace=kaspi, apply=True)
        self.assertEqual(Offer.objects.count(), 1)
        self.assertEqual(PriceObservation.objects.count(), 1)

    def test_archiving_cancels_jobs_and_prevents_queue_or_provider_execution(self):
        self.source.provider = "kaspi"
        self.source.refresh_enabled = True
        self.source.next_refresh_at = timezone.now()
        self.source.save()
        run = RefreshRun.objects.create(source=self.source)
        self.initialize()
        self.source.refresh_from_db(); run.refresh_from_db()
        self.assertFalse(self.source.refresh_enabled)
        self.assertIsNone(self.source.next_refresh_at)
        self.assertEqual(run.status, "cancelled")
        with self.assertRaises(InvalidSourceData):
            enqueue_refresh(self.source.pk)
        self.assertEqual(enqueue_due(), 0)
        another = RefreshRun.objects.create(source=self.source)
        with patch("core.refreshing.provider_for", side_effect=AssertionError("Must not fetch")):
            execute_refresh(another.pk)
        another.refresh_from_db()
        self.assertEqual(another.status, "cancelled")

    def test_archived_source_cannot_be_managed_through_active_ui(self):
        self.initialize()
        admin = get_user_model().objects.create_superuser(username="scope-admin", password="test-only")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("core:source_manage", args=[self.source.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("core:source_refresh", args=[self.source.pk])).status_code, 404)

    def test_admin_retains_readonly_imported_identity_and_filters_new_offer_choices(self):
        from core.admin import OfferReviewForm
        self.initialize()
        form = OfferReviewForm()
        self.assertEqual(set(form.fields["marketplace"].queryset.values_list("name", flat=True)), set(APPROVED_NAMES))
        user = get_user_model().objects.create_superuser(username="archive-reviewer", password="test-only")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:core_offer_change", args=[self.offer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.source.key)

    def test_demo_observation_capture_skips_archived_offers(self):
        self.offer.is_demo = True
        self.offer.save()
        call_command("record_demo_observations", stdout=StringIO())
        self.assertEqual(PriceObservation.objects.count(), 1)


class FreshFiveMarketplaceDemoTests(TestCase):
    def test_both_loaders_are_repeatable_and_never_seed_excluded_platforms(self):
        for _ in range(2):
            call_command("load_demo_data", stdout=StringIO())
            call_command("load_marketplace_demo", stdout=StringIO())
        self.assertEqual(set(Marketplace.objects.values_list("name", flat=True)), set(APPROVED_NAMES))
        self.assertEqual((Product.objects.count(), Offer.objects.count(), PriceObservation.objects.count()), (21, 30, 0))
        self.assertEqual(DataSource.objects.count(), 4)
        self.assertEqual(Product.objects.active().count(), 21)
        self.assertEqual(Offer.objects.active().count(), 30)
        self.assertFalse(Offer.objects.filter(is_demo=False).exists())
        before = list(Offer.objects.order_by("pk").values())
        call_command("load_marketplace_demo", stdout=StringIO())
        self.assertEqual(before, list(Offer.objects.order_by("pk").values()))
