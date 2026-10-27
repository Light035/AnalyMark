from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Marketplace, Offer, Product


class CatalogModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.marketplace = Marketplace.objects.create(name="Kaspi.kz")
        cls.product = Product.objects.create(name="Test lamp", category="Lighting")

    def offer(self, **overrides):
        values = dict(
            product=self.product, marketplace=self.marketplace, seller_name="Test seller",
            price=Decimal("10000.25"), delivery_cost=Decimal("299.75"), discount=Decimal("100.00"),
        )
        values.update(overrides)
        return Offer(**values)

    def test_optional_fields_and_string_representations(self):
        self.marketplace.full_clean()
        self.product.full_clean()
        offer = self.offer(delivery_cost=None, discount=None)
        offer.full_clean()
        self.assertTrue(offer.is_demo)
        self.assertEqual(str(self.product), "Test lamp")
        self.assertEqual(str(self.marketplace), "Kaspi.kz")
        self.assertIn("Test seller", str(offer))

    def test_required_names_and_category_reject_whitespace(self):
        instances = [
            Marketplace(name="  "), Product(name="  ", category="Lighting"),
            Product(name="Lamp", category="  "), self.offer(seller_name="  "),
        ]
        for instance in instances:
            with self.subTest(model=instance.__class__.__name__):
                with self.assertRaises(ValidationError):
                    instance.full_clean()

    def test_invalid_monetary_values_raise_validation_errors(self):
        cases = [
            ("price", "0"), ("price", "-1"), ("price", "10.001"),
            ("price", "NaN"), ("price", "Infinity"), ("price", "invalid"),
            ("delivery_cost", "-0.01"), ("delivery_cost", "1.001"),
            ("discount", "-0.01"), ("discount", "10001"),
            ("discount", "NaN"), ("discount", "invalid"),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValidationError):
                    self.offer(**{field: value}).full_clean()

    def test_only_http_and_https_urls_are_allowed(self):
        for url in ("javascript:alert(1)", "ftp://files.example/lamp", "not a URL"):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    self.offer(product_url=url).full_clean()
                with self.assertRaises(ValidationError):
                    Marketplace(name="New market", website_url=url).full_clean()
        self.offer(product_url="https://catalog.example/lamp").full_clean()

    def test_total_uses_exact_decimal_arithmetic(self):
        self.assertEqual(self.offer().total_buyer_cost, Decimal("10200.00"))

    def test_known_zero_delivery_and_discount_allow_a_total(self):
        offer = self.offer(delivery_cost=Decimal("0"), discount=Decimal("0"))
        self.assertEqual(offer.total_buyer_cost, Decimal("10000.25"))

    def test_missing_delivery_or_discount_makes_total_unavailable(self):
        for values in (
            {"delivery_cost": None}, {"discount": None},
            {"delivery_cost": None, "discount": None},
        ):
            with self.subTest(values=values):
                self.assertIsNone(self.offer(**values).total_buyer_cost)

    def test_full_discount_can_produce_a_known_zero_total(self):
        offer = self.offer(discount=Decimal("10000.25"), delivery_cost=Decimal("0"))
        offer.full_clean()
        self.assertEqual(offer.total_buyer_cost, Decimal("0.00"))

    def test_invalid_unsaved_amounts_do_not_produce_a_total(self):
        for values in ({"discount": Decimal("20000")}, {"price": "invalid"}, {"price": Decimal("NaN")}):
            with self.subTest(values=values):
                self.assertIsNone(self.offer(**values).total_buyer_cost)

    def test_database_enforces_monetary_constraints(self):
        for values in (
            {"price": Decimal("0")}, {"price": Decimal("-1")},
            {"delivery_cost": Decimal("-1")}, {"discount": Decimal("-1")},
            {"discount": Decimal("20000")},
        ):
            with self.subTest(values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.offer(**values).save()

    def test_one_offer_per_seller_product_marketplace_and_demo_status(self):
        self.offer().save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.offer().save()
        # A manually entered record remains distinct from its demonstration counterpart.
        self.offer(is_demo=False).save()
        self.assertEqual(Offer.objects.count(), 2)
