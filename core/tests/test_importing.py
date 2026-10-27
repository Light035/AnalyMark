import csv
import io
import tempfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.importing import run_import
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, SourceOffer, SourceProduct
from core.providers import COLUMNS, CSVOfferProvider, InvalidSourceData, MAX_BYTES, MAX_ROWS, OfferRecord, SourceError


def sample(**changes):
    # Fictional test input only; never loaded into the development database.
    return replace(OfferRecord(
        product_id="variant-1", product_name="Fictional test lamp", brand="Test brand",
        category="Lighting", offer_id="offer-1", seller_name="Test seller",
        listed_price=Decimal("1200.00"), currency="KZT", delivery_cost=Decimal("100"),
        discount=Decimal("50"), source_url="https://catalog.example/products/test-lamp/",
    ), **changes)


class ImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.market = Marketplace.objects.create(name="Kaspi.kz")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "offers.csv"

    def write(self, *records, bom=False):
        with self.path.open("w", encoding="utf-8-sig" if bom else "utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow({field: getattr(record, field) for field in COLUMNS})
        return CSVOfferProvider(self.path)

    def run_import(self, *records, apply=True, **options):
        return run_import(self.write(*(records or [sample()])), key=options.pop("key", "seller-file"),
                          marketplace=self.market, apply=apply, **options)

    def test_valid_import_normalizes_money_urls_identity_and_actual_timestamp(self):
        before = timezone.now()
        result = self.run_import()
        after = timezone.now()
        self.assertEqual((result.products_created, result.offers_created), (1, 1))
        offer = Offer.objects.get()
        self.assertFalse(offer.is_demo)
        self.assertEqual(offer.total_buyer_cost, Decimal("1250.00"))
        mapping = SourceOffer.objects.get()
        source = DataSource.objects.get()
        self.assertEqual(mapping.source_url, offer.product_url)
        self.assertEqual(mapping.external_id, "offer-1")
        self.assertTrue(before <= mapping.imported_at <= after)
        self.assertEqual(source.last_success_at, mapping.imported_at)
        self.assertEqual(source.status, "success")
        self.assertFalse(PriceObservation.objects.exists())

    def test_idempotent_same_source_and_identical_rows(self):
        self.run_import(sample(), sample())
        result = self.run_import()
        self.assertEqual((result.products_created, result.offers_created, result.offers_unchanged), (0, 0, 1))
        self.assertEqual((Product.objects.count(), Offer.objects.count(), SourceOffer.objects.count()), (1, 1, 1))

    def test_changed_price_records_only_new_price_at_import_time(self):
        self.run_import()
        result = self.run_import(sample(listed_price=Decimal("1300")))
        self.assertEqual(result.offers_updated, 1)
        self.assertEqual(Offer.objects.get().price, Decimal("1300"))
        observation = PriceObservation.objects.get()
        self.assertEqual(observation.price, Decimal("1300"))
        self.assertEqual(observation.observed_at, SourceOffer.objects.get().imported_at)
        self.assertTrue(observation.recorded_by_import)
        self.assertFalse(observation.is_demo)

    def test_unknown_values_stay_unknown_on_create(self):
        self.run_import(sample(delivery_cost=None, discount=None))
        offer = Offer.objects.get()
        self.assertIsNone(offer.delivery_cost)
        self.assertIsNone(offer.discount)
        self.assertIsNone(offer.total_buyer_cost)

    def test_blank_values_preserve_known_data_but_explicit_zero_updates(self):
        self.run_import()
        self.run_import(sample(brand="", delivery_cost=None, discount=None))
        offer = Offer.objects.get()
        self.assertEqual((offer.delivery_cost, offer.discount, offer.product.brand), (Decimal("100"), Decimal("50"), "Test brand"))
        self.run_import(sample(delivery_cost=Decimal("0"), discount=Decimal("0")))
        self.assertEqual(Offer.objects.get().total_buyer_cost, Decimal("1200"))

    def test_retained_discount_cannot_exceed_new_listed_price(self):
        self.run_import()
        with self.assertRaises(InvalidSourceData):
            self.run_import(sample(listed_price=Decimal("20"), discount=None))
        self.assertEqual(Offer.objects.get().price, Decimal("1200"))

    def test_namespace_never_merges_existing_demo_or_manual_products_by_name(self):
        existing = Product.objects.create(name=sample().product_name, brand=sample().brand, category="Lighting")
        demo = Offer.objects.create(product=existing, marketplace=self.market, seller_name="Test seller", price="999", is_demo=True)
        self.run_import()
        self.run_import(key="different-source")
        self.assertEqual(Product.objects.count(), 3)
        demo.refresh_from_db()
        self.assertEqual(demo.price, Decimal("999"))
        self.assertFalse(SourceProduct.objects.filter(product=existing).exists())

    def test_source_marketplace_and_demo_mode_cannot_be_reassigned(self):
        self.run_import()
        with self.assertRaises(InvalidSourceData):
            self.run_import(is_demo=True)
        other = Marketplace.objects.create(name="Ozon")
        with self.assertRaises(InvalidSourceData):
            run_import(self.write(sample()), key="seller-file", marketplace=other, apply=True)
        self.assertEqual(DataSource.objects.get().marketplace, self.market)

    def test_demo_csv_import_is_explicitly_flagged(self):
        self.run_import(is_demo=True)
        self.assertTrue(Offer.objects.get().is_demo)
        self.assertTrue(DataSource.objects.get().is_demo)
        self.assertFalse(PriceObservation.objects.exists())

    def test_distinct_seller_offers_share_only_exact_source_product_id(self):
        self.run_import(sample(), sample(offer_id="offer-2", seller_name="Second test seller", listed_price=Decimal("1400")))
        self.assertEqual((Product.objects.count(), Offer.objects.count()), (1, 2))
        page = self.client.get(reverse("core:product_detail", args=[Product.objects.get().pk]))
        self.assertEqual(page.context["summary"]["average"], Decimal("1300"))

    def test_offer_id_cannot_move_to_a_different_product_and_rolls_back_new_product(self):
        self.run_import()
        with self.assertRaises(InvalidSourceData):
            self.run_import(sample(product_id="variant-2"))
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(SourceProduct.objects.get().external_id, "variant-1")

    def test_database_conflict_rolls_back_entire_batch(self):
        with self.assertRaises(InvalidSourceData):
            self.run_import(sample(), sample(offer_id="offer-2"))  # Existing one-offer-per-seller rule.
        for model in (Product, Offer, SourceProduct, SourceOffer):
            self.assertEqual(model.objects.count(), 0)
        self.assertEqual(DataSource.objects.get().status, "error")
        self.assertIsNone(DataSource.objects.get().last_success_at)

    def test_row_errors_retain_original_location_after_identical_duplicates(self):
        with self.assertRaisesMessage(InvalidSourceData, "Row 4: offer"):
            self.run_import(sample(), sample(), sample(offer_id="different-offer-same-seller"))
        self.assertFalse(Offer.objects.exists())

    def test_dry_run_rolls_back_every_record_and_source_status(self):
        result = self.run_import(apply=False)
        self.assertEqual(result.offers_created, 1)
        for model in (Product, Offer, DataSource, SourceProduct, SourceOffer):
            self.assertEqual(model.objects.count(), 0)
        self.run_import()
        original = DataSource.objects.values().get()
        old_provenance = SourceOffer.objects.values().get()
        self.run_import(sample(listed_price=Decimal("1500")), apply=False)
        self.assertEqual(DataSource.objects.values().get(), original)
        self.assertEqual(SourceOffer.objects.values().get(), old_provenance)
        self.assertEqual(Offer.objects.get().price, Decimal("1200"))

    def test_failed_dry_run_does_not_change_previous_status(self):
        self.run_import()
        original = DataSource.objects.values().get()
        with self.assertRaises(InvalidSourceData):
            self.run_import(sample(currency="USD"), apply=False)
        self.assertEqual(DataSource.objects.values().get(), original)

    def test_failure_preserves_last_success_and_hides_raw_cells(self):
        self.run_import()
        original = DataSource.objects.get().last_success_at
        with self.assertRaises(InvalidSourceData) as caught:
            self.run_import(sample(listed_price="PRIVATE_TOKEN_NOT_A_PRICE"))
        source = DataSource.objects.get()
        self.assertEqual(source.last_success_at, original)
        self.assertEqual(source.status, "error")
        self.assertNotIn("PRIVATE_TOKEN", source.last_error + str(caught.exception))
        self.run_import()
        self.assertEqual(DataSource.objects.get().last_error, "")

    def test_money_validation_and_currency(self):
        for changes in (
            {"listed_price": "0"}, {"listed_price": "-1"}, {"listed_price": "NaN"},
            {"listed_price": "Infinity"}, {"listed_price": "1.234"}, {"listed_price": "10000000000"},
            {"delivery_cost": "-0.01"}, {"discount": "-2"}, {"discount": "1200.01"}, {"currency": "USD"},
        ):
            with self.subTest(changes=changes), self.assertRaises(InvalidSourceData):
                self.run_import(sample(**changes), apply=False)
        self.assertFalse(Offer.objects.exists())

    def test_invalid_urls_and_required_fields(self):
        for changes in (
            {"source_url": "javascript:alert(1)"}, {"source_url": "https://user:SECRET@example.com/a"},
            {"source_url": "https://example.com/a?token=SECRET"}, {"source_url": "file:///tmp/a"},
            {"product_id": ""}, {"offer_id": "invalid ID"}, {"seller_name": ""},
            {"product_name": ""}, {"category": ""}, {"source_url": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(InvalidSourceData):
                self.run_import(sample(**changes), apply=False)

    def test_conflicting_duplicate_offer_or_product_metadata_rejected(self):
        for second in (sample(listed_price=Decimal("1201")), sample(offer_id="offer-2", product_name="Other variant")):
            with self.subTest(second=second), self.assertRaises(InvalidSourceData):
                self.run_import(sample(), second)
        self.assertFalse(Product.objects.exists())

    def test_csv_handles_bom_unicode_and_quoted_commas(self):
        provider = self.write(sample(product_name="Тест, fictional product"), bom=True)
        self.assertEqual(provider.fetch()[0].product_name, "Тест, fictional product")

    def test_malformed_empty_and_oversized_files(self):
        for data in (b"", b"wrong,headers\n1,2", b"\xff\xfe", (",".join(COLUMNS) + "\nshort,row").encode(),
                     (",".join(COLUMNS) + '\n"unterminated').encode(), b"x" * (MAX_BYTES + 1)):
            with self.subTest(length=len(data)), self.assertRaises(InvalidSourceData):
                self.path.write_bytes(data)
                CSVOfferProvider(self.path).fetch()

    def test_duplicate_headers_extra_cells_and_row_limit(self):
        for headers, row in ((list(COLUMNS[:-1]) + ["discount"], [""] * len(COLUMNS)),
                             (COLUMNS, [""] * (len(COLUMNS) + 1))):
            with self.path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerow(row)
            with self.assertRaises(InvalidSourceData):
                CSVOfferProvider(self.path).fetch()
        self.write(*([sample()] * (MAX_ROWS + 1)))
        with self.assertRaisesMessage(InvalidSourceData, "row limit"):
            CSVOfferProvider(self.path).fetch()

    def test_invalid_namespace_and_unsupported_provider_do_not_write(self):
        provider = self.write(sample())
        for key in ("bad key", "Uppercase", "../private", "x" * 81):
            with self.subTest(key=key), self.assertRaises(InvalidSourceData):
                run_import(provider, key=key, marketplace=self.market, apply=True)
        provider.kind = "unverified-api"
        with self.assertRaises(InvalidSourceData):
            run_import(provider, key="seller-file", marketplace=self.market, apply=True)
        self.assertFalse(DataSource.objects.exists())

    def test_unexpected_provider_exception_is_redacted(self):
        provider = self.write(sample())
        with patch.object(provider, "fetch", side_effect=RuntimeError("PRIVATE_EXCEPTION_BODY")):
            with self.assertRaises(SourceError) as caught:
                run_import(provider, key="seller-file", marketplace=self.market, apply=True)
        self.assertNotIn("PRIVATE", DataSource.objects.get().last_error + str(caught.exception))

    def test_source_timeout_and_unavailable_file_are_safe(self):
        provider = self.write(sample())
        with patch.object(provider, "fetch", side_effect=TimeoutError("PRIVATE_PROVIDER_RESPONSE")):
            with self.assertRaises(SourceError) as caught:
                run_import(provider, key="seller-file", marketplace=self.market, apply=True)
        self.assertIn("timed out", caught.exception.public_message)
        self.assertNotIn("PRIVATE", DataSource.objects.get().last_error)
        self.path.unlink()
        with self.assertRaises(SourceError):
            run_import(provider, key="seller-file", marketplace=self.market, apply=True)
        self.assertFalse(Offer.objects.exists())

    def test_future_provider_malformed_result_rejected_at_shared_boundary(self):
        provider = self.write(sample())
        for bad in (None, {}, [{"unexpected": "SECRET"}], [sample(listed_price=None)]):
            with self.subTest(bad=bad), patch.object(provider, "fetch", return_value=bad), self.assertRaises(SourceError):
                run_import(provider, key="seller-file", marketplace=self.market, apply=True)
        self.assertFalse(Product.objects.exists())

    def test_cli_defaults_to_preview_and_requires_explicit_apply(self):
        self.write(sample())
        output = io.StringIO()
        args = ["import_offers_csv", str(self.path), "--source", "seller-file", "--marketplace", "Kaspi.kz"]
        call_command(*args, stdout=output)
        self.assertIn("PREVIEW ONLY", output.getvalue())
        self.assertFalse(DataSource.objects.exists())
        call_command(*args, "--apply", stdout=output)
        self.assertEqual(Offer.objects.count(), 1)
        call_command(*args, "--apply", stdout=output)
        self.assertEqual(Offer.objects.count(), 1)

    def test_cli_missing_marketplace_and_row_errors_are_readable(self):
        self.write(sample(currency="USD"))
        with self.assertRaisesMessage(CommandError, "Marketplace not found"):
            call_command("import_offers_csv", str(self.path), source="x", marketplace="Missing")
        with self.assertRaisesMessage(CommandError, "Row 2: currency: only KZT"):
            call_command("import_offers_csv", str(self.path), source="x", marketplace="Kaspi.kz")

    def test_database_source_identity_constraints(self):
        self.run_import()
        mapping = SourceProduct.objects.get()
        extra = Product.objects.create(name="Other", category="Lighting")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SourceProduct.objects.create(source=mapping.source, external_id=mapping.external_id, product=extra)
        offer_mapping = SourceOffer.objects.get()
        offer = Offer.objects.create(product=extra, marketplace=self.market, seller_name="Test", price="1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            SourceOffer.objects.create(source=offer_mapping.source, external_id=offer_mapping.external_id,
                                       offer=offer, source_url=sample().source_url, imported_at=timezone.now())

    def test_dashboard_counts_provenance_and_does_not_expose_errors_to_public(self):
        self.assertContains(self.client.get("/"), "No CSV imports recorded")
        self.run_import()
        source = DataSource.objects.get()
        source.last_error = "Row 2: discount: invalid amount."
        source.status = "error"
        source.save()
        response = self.client.get("/")
        data_source = response.context["data_sources"][0]
        self.assertEqual((data_source.product_count, data_source.offer_count), (1, 1))
        self.assertContains(response, "Manual CSV · unverified · not live")
        self.assertContains(response, "Last import failed")
        self.assertNotContains(response, source.last_error)
        user = get_user_model().objects.create_user(username="ordinary-user")
        self.client.force_login(user)
        self.assertNotContains(self.client.get("/"), source.last_error)
        user.is_staff = True
        user.save()
        self.assertContains(self.client.get("/"), source.last_error)

    def test_search_and_product_page_show_import_provenance_and_unverified_matching(self):
        self.run_import()
        for url in (reverse("core:product_search"), reverse("core:product_detail", args=[Product.objects.get().pk])):
            response = self.client.get(url)
            self.assertContains(response, "CSV import · unverified · not live")
            self.assertContains(response, "Source: seller-file")
            self.assertContains(response, "Last imported:")
            self.assertContains(response, "marketplace update time")
        history = self.client.get(reverse("core:price_history", args=[Offer.objects.get().pk]))
        self.assertContains(history, "No observations recorded")
