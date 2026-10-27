"""Exactly five approved MVP labels. Archiving never deletes catalog/history."""

MARKETPLACES = (
    ("kaspi", "Kaspi.kz", "https://kaspi.kz/"),
    ("halyk", "Halyk Market", "https://halykmarket.kz/"),
    ("ozon", "Ozon", "https://ozon.kz/"),
    ("wildberries", "Wildberries", "https://www.wildberries.kz/"),
    ("teez", "Teez", "https://teez.kz/"),
)
APPROVED_NAMES = tuple(name for _, name, _ in MARKETPLACES)


def initialize_marketplaces():
    from django.db import transaction
    from django.utils import timezone
    from .models import DataSource, Marketplace, RefreshRun

    # Retain the old primary key, source namespaces and relationships. If both
    # labels exist, archive the alias instead of guessing how to merge records.
    with transaction.atomic():
        if not Marketplace.objects.filter(name="Ozon").exists():
            Marketplace.objects.filter(name="Ozon Kazakhstan").update(name="Ozon")
        Marketplace.objects.exclude(name__in=APPROVED_NAMES).update(is_active=False)
        Marketplace.objects.filter(name__in=APPROVED_NAMES).update(is_active=True)
        archived_sources = DataSource.objects.exclude(marketplace__name__in=APPROVED_NAMES)
        archived_sources.update(refresh_enabled=False, next_refresh_at=None)
        RefreshRun.objects.filter(source__in=archived_sources, status__in=["queued", "running"]).update(
            status="cancelled", finished_at=timezone.now(), error="Marketplace archived: outside the five-marketplace MVP scope.")
        return _create_approved()


def _create_approved():
    from .models import Marketplace
    created = 0
    for _, name, url in MARKETPLACES:
        _, added = Marketplace.objects.get_or_create(name=name, defaults={"website_url": url, "is_active": True})
        created += added
    return created
