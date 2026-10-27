"""Add an invented workspace catalog; never refresh or overwrite existing data."""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Marketplace, Offer, PriceObservation, Product
from core.marketplaces import initialize_marketplaces


class Command(BaseCommand):
    help = "Add missing fictional demo products/offers, preserving all existing records and edits."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-illustrative-history", action="store_true",
            help="Once only, simulate and capture three demo price changes now for the designated pristine offer. No backdating.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        initialize_marketplaces()
        kaspi, _ = Marketplace.objects.get_or_create(
            name="Kaspi.kz", defaults={"website_url": "https://kaspi.kz/"}
        )
        # Names encode the variant and bundle. Mapping is curated, not automatically matched.
        products = [
            ("Luma L1 — white, single lamp", "AspanLab", "Desk lighting", "White lamp; one unit. Fictional demonstration product."),
            ("Luma L1 — black, single lamp", "AspanLab", "Desk lighting", "Fictional demonstration product. Black lamp; one unit. A different variant from the white lamp."),
            ("Luma L1 — white, lamp + cable bundle", "AspanLab", "Desk lighting", "Fictional demonstration product. One white lamp plus an extra cable. Not equivalent to the single-lamp package."),
            ("Focus F2 — graphite, single lamp", "ArqaLite", "Desk lighting", "Fictional demonstration product. Graphite lamp; one unit. A different model and brand."),
            ("Focus F2 — white, single lamp (demo)", "ArqaLite", "Desk lighting", "Fictional demonstration product. White finish; one lamp. Only one sample seller; discount information is missing."),
            ("Orbit O3 — mint, single lamp (demo)", "DalaGlow", "Desk lighting", "Fictional demonstration product. Mint lamp; one unit. Review this model separately from Luma and Focus."),
            ("Orbit O3 — mint, lamp + stand bundle (demo)", "DalaGlow", "Desk lighting", "Fictional demonstration product. Mint lamp with an extra stand. Not the single-lamp package."),
            ("Keyra K1 — compact, EN layout (demo)", "QalamLab", "Keyboards", "Fictional demonstration product. Compact keyboard; EN layout. The illustrative-history seller can have three deliberately changed sample prices captured within one command run, not real marketplace history or an elapsed market trend."),
            ("Keyra K1 — compact, RU/EN layout (demo)", "QalamLab", "Keyboards", "Fictional demonstration product. Compact keyboard; RU/EN layout. A separate variant from the EN-only keyboard."),
            ("Portiq H4 — four-port hub (demo)", "OrnekPort", "USB hubs", "Fictional demonstration product. Four-port hub; one unit. No verified compatibility or real product specification is claimed."),
            ("Portiq H7 — seven-port hub (demo)", "OrnekPort", "USB hubs", "Fictional demonstration product. Seven-port hub; one unit. A different model from H4; prices are illustrative."),
            ("Portiq H4 — hub + cable bundle (demo)", "OrnekPort", "USB hubs", "Fictional demonstration product. Four-port hub plus an extra cable; not equivalent to the hub-only package."),
            ("Matra M1 — large grey desk mat (demo)", "JolDesk", "Workspace accessories", "Fictional demonstration product. Large grey desk mat; one unit. Invented seller offers include incomplete delivery and discount data."),
        ]
        catalog = []
        created_products = created_offers = 0
        for name, brand, category, description in products:
            product, created = Product.objects.get_or_create(
                name=name, brand=brand,
                defaults={"category": category, "description": description},
            )
            created_products += int(created)
            catalog.append(product)

        # Listed price, delivery and discount are KZT amounts. None is unknown; 0 is known.
        rows = [
            (0, kaspi, "Cedar Desk Demo", "12000.00", "800.00", "500.00", "https://catalog.example/luma-white"),
            (0, kaspi, "Mosaic Lamp Demo", "12500.00", "0.00", "0.00", ""),
            (0, kaspi, "Tumar Workspace Demo", "11800.00", None, "300.00", ""),
            (1, kaspi, "Cedar Desk Demo", "12300.00", "900.00", "0.00", ""),
            (2, kaspi, "Mosaic Lamp Demo", "14000.00", "700.00", "1000.00", "https://catalog.example/luma-bundle"),
            (3, kaspi, "Tumar Workspace Demo", "15600.00", "0.00", "600.00", ""),
            (4, kaspi, "Tumar Workspace Demo", "15900.00", "800.00", None, ""),
            (5, kaspi, "Cedar Desk Demo", "18900.00", "0.00", "900.00", ""),
            (6, kaspi, "Mosaic Lamp Demo", "21300.00", "1000.00", "1300.00", ""),
            (7, kaspi, "Steppe Keys Demo — illustrative history", "22500.00", "700.00", "500.00", ""),
            (7, kaspi, "Mosaic Keys Demo", "21900.00", "0.00", "0.00", ""),
            (8, kaspi, "Steppe Keys Demo", "23900.00", "600.00", "900.00", ""),
            (9, kaspi, "Ornek Cables Demo", "7900.00", "500.00", "400.00", ""),
            (10, kaspi, "Ornek Cables Demo", "12900.00", "700.00", "1000.00", ""),
            (10, kaspi, "Tumar Ports Demo", "12500.00", None, None, ""),
            (11, kaspi, "Ornek Cables Demo", "9600.00", "500.00", "600.00", ""),
            (12, kaspi, "Jol Workspace Demo", "6500.00", "500.00", "0.00", ""),
            (12, kaspi, "Tumar Workspace Demo", "6200.00", None, "200.00", ""),
        ]
        history_offer = history_values = None
        for index, marketplace, seller, price, delivery, discount, url in rows:
            identity = dict(product=catalog[index], marketplace=marketplace, seller_name=seller, is_demo=True)
            values = dict(
                price=Decimal(price), delivery_cost=Decimal(delivery) if delivery is not None else None,
                discount=Decimal(discount) if discount is not None else None, product_url=url,
            )
            Offer(**identity, **values).full_clean(validate_unique=False, validate_constraints=False)
            offer, created = Offer.objects.get_or_create(**identity, defaults=values)
            created_offers += int(created)
            if index == 7 and seller == "Steppe Keys Demo — illustrative history":
                history_offer, history_values = offer, values

        self.stdout.write(self.style.SUCCESS(
            f"Kaspi demo scope: 1 marketplace, {len(products)} fictional products, and {len(rows)} demonstration offers. "
            f"Created {created_products} products and {created_offers} offers; existing records were preserved. "
            "Prices are invented, not live Kaspi observations."
        ))
        if options["with_illustrative_history"]:
            self._record_illustrative_history(history_offer, history_values, products[7][3])

    def _record_illustrative_history(self, offer, seed_values, description):
        """A one-time, explicit simulation, with real capture times and no backfill."""
        offer = Offer.objects.select_for_update().get(pk=offer.pk)
        if offer.observations.exists():
            self.stdout.write("Illustrative history: recorded 0; existing observations preserved.")
            return
        if offer.product.description != description or any(
            getattr(offer, field) != value for field, value in seed_values.items()
        ):
            self.stdout.write("Illustrative history: recorded 0; edited sample offer/product preserved.")
            return
        # Deliberately change the demo state and capture it immediately at each step.
        # The final price equals the seed price. No time offsets, delays or past dates.
        for price in (Decimal("23500.00"), Decimal("21900.00"), seed_values["price"]):
            offer.price = price
            offer.full_clean()
            offer.save(update_fields=["price"])
            observation = PriceObservation(offer=offer, price=offer.price, observed_at=timezone.now(), is_demo=True)
            observation.full_clean()
            observation.save()
        self.stdout.write(self.style.SUCCESS(
            "Illustrative history: recorded 3 demo observations for Keyra K1 / Steppe Keys Demo "
            "(23500 -> 21900 -> 22500 KZT) during this run. "
            "Timestamps are actual capture times, not backdated market history or continuous monitoring."
        ))
