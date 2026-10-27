"""Additive fixtures with source identities, deliberately separate from acquisition."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.marketplaces import MARKETPLACES, initialize_marketplaces
from core.models import DataSource, Marketplace, Offer, Product, SourceOffer, SourceProduct


class Command(BaseCommand):
    help = "Add fictional offers for Halyk Market, Ozon, Wildberries and Teez. No network or invented history."

    @transaction.atomic
    def handle(self, *args, **options):
        initialize_marketplaces()
        products_added = offers_added = 0
        loaded_at = timezone.now()
        # Kaspi's fixtures remain owned by load_demo_data. Keep seed prices stable
        # even if the display order changes; existing values are never reset.
        base_prices = {"ozon": 10000, "wildberries": 10300, "halyk": 10600, "teez": 11500}
        for key, name, _ in MARKETPLACES[1:]:
            market = Marketplace.objects.get(name=name)
            source, created = DataSource.objects.get_or_create(
                key=f"mvp-demo-{key}-v1", defaults={
                    "marketplace": market, "provider": DataSource.Provider.DEMO, "is_demo": True,
                },
            )
            if (source.marketplace_id, source.provider, source.is_demo) != (market.pk, DataSource.Provider.DEMO, True):
                raise CommandError(f"Reserved demo source collision: mvp-demo-{key}-v1. Nothing saved.")
            changed = created
            for variant, title in (("solo", "MiraLab Desk Light Solo"), ("bundle", "MiraLab Desk Light + Stand Bundle")):
                identity = SourceProduct.objects.filter(source=source, external_id=variant).first()
                if identity is None:
                    product = Product.objects.create(
                        name=f"Demo · {title}", brand="MiraLab Demo", category="Demo office accessories",
                        description=f"Fictional {name} example. No real seller or marketplace price. "
                                    "Same names on other platforms do not establish product identity.",
                    )
                    identity = SourceProduct.objects.create(source=source, external_id=variant, product=product)
                    products_added += 1
                    changed = True
                product = identity.product
                for seller in range(2 if variant == "solo" else 1):
                    external_id = f"{variant}-seller-{seller + 1}"
                    mapping = SourceOffer.objects.filter(source=source, external_id=external_id).select_related("offer").first()
                    if mapping:
                        if (mapping.offer.product_id, mapping.offer.marketplace_id, mapping.offer.is_demo) != (product.pk, market.pk, True):
                            raise CommandError(f"Demo identity conflict in {source.key}; nothing saved.")
                        continue  # Never reset prices, manual reviews, timestamps or history.
                    price = Decimal(base_prices[key] + seller * 750 + (4000 if variant == "bundle" else 0))
                    url = f"https://{key}.example/demo/{external_id}"
                    offer = Offer(
                        product=product, marketplace=market, seller_name=f"Demo Seller {seller + 1} · {name}",
                        price=price, delivery_cost=Decimal("0") if seller == 0 else None,
                        discount=Decimal("500") if variant == "solo" and seller == 0 else None,
                        product_url=url, is_demo=True,
                    )
                    offer.full_clean()
                    offer.save()
                    SourceOffer.objects.create(source=source, external_id=external_id, offer=offer,
                                               source_url=url, imported_at=loaded_at)
                    offers_added += 1
                    changed = True
            if changed:
                source.status = DataSource.Status.SUCCESS
                source.last_attempt_at = source.last_success_at = loaded_at
                source.last_error = ""
                source.save(update_fields=["status", "last_attempt_at", "last_success_at", "last_error"])
        self.stdout.write(f"Created {products_added} products and {offers_added} offers. DEMO ONLY. "
                          "Existing values preserved; no observations or marketplace requests created.")
