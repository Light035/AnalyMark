"""Database-backed queue and sequential worker. No synthetic or network provider."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .importing import run_import
from .models import DataSource, Marketplace, RefreshRun
from .providers import InvalidSourceData, SourceBlocked, SourceError, provider_for

ACTIVE = (RefreshRun.Status.QUEUED, RefreshRun.Status.RUNNING)


def enqueue_refresh(source_id, *, requested_by=None, scheduled=False, now=None):
    now = now or timezone.now()
    try:
        with transaction.atomic():
            source = DataSource.objects.select_for_update().get(pk=source_id)
            if not Marketplace.objects.active().filter(pk=source.marketplace_id).exists():
                raise InvalidSourceData("Marketplace is archived or outside the five-marketplace MVP scope.")
            if source.provider != DataSource.Provider.KASPI:
                raise InvalidSourceData("CSV and demo fixtures have no automatic feed. Use the explicit fallback or demo command.")
            if scheduled and (not source.refresh_enabled or (source.next_refresh_at and source.next_refresh_at > now)):
                return None, False
            active = source.refresh_runs.filter(status__in=ACTIVE).first()
            if active:
                return active, False
            run = RefreshRun.objects.create(source=source, scheduled=scheduled, requested_by=requested_by)
            source.next_refresh_at = now + timedelta(minutes=source.refresh_interval_minutes) if source.refresh_enabled else None
            source.save(update_fields=["next_refresh_at"])
            return run, True
    except IntegrityError:
        # The conditional unique constraint is authoritative for simultaneous clicks.
        active = RefreshRun.objects.filter(source_id=source_id, status__in=ACTIVE).first()
        if active:
            return active, False
        raise


def enqueue_due(now=None):
    now = now or timezone.now()
    from django.db.models import Q
    due = DataSource.objects.filter(refresh_enabled=True, marketplace__in=Marketplace.objects.active()).exclude(provider="csv").filter(
        Q(next_refresh_at__isnull=True) | Q(next_refresh_at__lte=now)
    ).exclude(refresh_runs__status__in=ACTIVE).order_by("next_refresh_at", "pk")
    queued = 0
    for pk in list(due.values_list("pk", flat=True)[:100]):
        _, created = enqueue_refresh(pk, scheduled=True, now=now)
        queued += int(created)
    return queued


def execute_refresh(run_id):
    started = timezone.now()
    with transaction.atomic():
        # Conditional update prevents two workers claiming the same queued run.
        if not RefreshRun.objects.filter(pk=run_id, status=RefreshRun.Status.QUEUED).update(
                status=RefreshRun.Status.RUNNING, started_at=started):
            return False
        run = RefreshRun.objects.select_related("source__marketplace").get(pk=run_id)
        if not run.source.marketplace.is_supported or (run.scheduled and not run.source.refresh_enabled):
            run.status, run.finished_at = RefreshRun.Status.CANCELLED, timezone.now()
            run.save(update_fields=["status", "finished_at"])
            return True
        DataSource.objects.filter(pk=run.source_id).update(last_attempt_at=started)
    try:
        provider = provider_for(run.source)
        run_import(provider, key=run.source.key, marketplace=run.source.marketplace,
                   is_demo=run.source.is_demo, apply=True, refresh_run=run)
    except Exception as error:
        # Never persist exception strings, URLs, response bodies or credentials.
        public = error.public_message if isinstance(error, SourceError) else "Refresh failed safely. No catalog changes were saved."
        status = RefreshRun.Status.BLOCKED if isinstance(error, SourceBlocked) else RefreshRun.Status.FAILED
        with transaction.atomic():
            if RefreshRun.objects.filter(pk=run.pk, status=RefreshRun.Status.RUNNING).update(
                    status=status, finished_at=timezone.now(), error=public):
                DataSource.objects.filter(pk=run.source_id).update(
                    status=DataSource.Status.BLOCKED if status == RefreshRun.Status.BLOCKED else DataSource.Status.ERROR,
                    last_error=public)
    return True


def recover_stuck(minutes):
    """Explicit operator recovery, with a write fence against late catalog writes."""
    cutoff = timezone.now() - timedelta(minutes=minutes)
    recovered = 0
    for pk in list(RefreshRun.objects.filter(status=RefreshRun.Status.RUNNING, started_at__lt=cutoff).values_list("pk", flat=True)[:100]):
        with transaction.atomic():
            run = RefreshRun.objects.get(pk=pk)
            message = "Worker interrupted or expired; operation recovered. Inspect the source before retrying."
            if RefreshRun.objects.filter(pk=pk, status=RefreshRun.Status.RUNNING, started_at__lt=cutoff).update(
                    status=RefreshRun.Status.FAILED, error=message, finished_at=timezone.now()):
                DataSource.objects.filter(pk=run.source_id).update(status=DataSource.Status.ERROR, last_error=message)
                recovered += 1
    return recovered


def worker_pass():
    queued = enqueue_due()
    completed = 0
    for pk in list(RefreshRun.objects.filter(status=RefreshRun.Status.QUEUED).order_by("queued_at", "pk").values_list("pk", flat=True)[:50]):
        completed += int(execute_refresh(pk))
    return queued, completed
