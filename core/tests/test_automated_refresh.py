"""Worker contract tests use fictional providers only in the isolated test DB."""
import io
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from core.forms import DataSourceConfigureForm
from core.importing import run_import
from core.models import DataSource, Marketplace, Offer, PriceObservation, Product, RefreshRun, SourceOffer
from core.providers import InvalidSourceData, KaspiPendingProvider, SourceBlocked
from core.refreshing import enqueue_due, enqueue_refresh, execute_refresh, recover_stuck, worker_pass
from core.tests.test_importing import sample


class FixtureProvider:
    """No runtime registration; cannot be selected in UI or real worker."""
    kind = "kaspi"

    def __init__(self, *records):
        self.records = list(records or [sample()])

    def fetch(self):
        return self.records


class AutomatedRefreshTests(TestCase):
    def setUp(self):
        self.market = Marketplace.objects.create(name="Kaspi.kz")
        self.source = DataSource.objects.create(key="approved-access-pending", marketplace=self.market, provider="kaspi")

    def execute(self, *records):
        run, _ = enqueue_refresh(self.source.pk)
        with patch("core.refreshing.provider_for", return_value=FixtureProvider(*records)):
            self.assertTrue(execute_refresh(run.pk))
        run.refresh_from_db()
        self.source.refresh_from_db()
        return run

    def test_real_kaspi_adapter_is_explicitly_blocked_and_makes_no_request(self):
        with patch("urllib.request.urlopen") as request:
            with self.assertRaises(SourceBlocked):
                KaspiPendingProvider().fetch()
            run, _ = enqueue_refresh(self.source.pk)
            execute_refresh(run.pk)
            request.assert_not_called()
        run.refresh_from_db()
        self.source.refresh_from_db()
        self.assertEqual(run.status, "blocked")
        self.assertEqual(self.source.status, "blocked")
        self.assertIsNone(self.source.last_success_at)
        self.assertIsNotNone(self.source.last_attempt_at)
        self.assertEqual(run.counts, {})
        self.assertFalse(Product.objects.exists())
        self.assertFalse(Offer.objects.exists())
        self.assertFalse(PriceObservation.objects.exists())
        self.assertEqual(self.client.get('/').context['source_summary']['blocked'], 1)

    def test_queue_idempotency_and_database_active_constraint(self):
        first, created = enqueue_refresh(self.source.pk)
        self.assertTrue(created)
        second, created = enqueue_refresh(self.source.pk)
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RefreshRun.objects.create(source=self.source)
        execute_refresh(first.pk)
        third, created = enqueue_refresh(self.source.pk)
        self.assertTrue(created)
        self.assertNotEqual(first.pk, third.pk)

    def test_one_claim_only_and_no_duplicate_execution(self):
        run, _ = enqueue_refresh(self.source.pk)
        with patch("core.refreshing.provider_for", return_value=FixtureProvider()) as factory:
            self.assertTrue(execute_refresh(run.pk))
            self.assertFalse(execute_refresh(run.pk))
            factory.assert_called_once()
        self.assertEqual(Offer.objects.count(), 1)

    def test_refresh_price_history_review_optional_values_and_unchanged_prices(self):
        first = self.execute()
        self.assertEqual(first.status, "succeeded")
        self.assertEqual(first.counts["offers_created"], 1)
        self.assertFalse(PriceObservation.objects.exists())
        offer = Offer.objects.get()
        offer.match_status, offer.match_notes = "confirmed", "Exact variant checked in test fixture"
        offer.save()
        changed = self.execute(sample(listed_price=Decimal("1400"), brand="", delivery_cost=None, discount=None))
        self.assertEqual(changed.counts["observations_created"], 1)
        observation = PriceObservation.objects.get()
        self.assertEqual(observation.refresh_run_id, changed.pk)
        self.assertFalse(observation.recorded_by_import)
        self.assertFalse(observation.is_demo)
        self.assertEqual(observation.price, Decimal("1400"))
        self.assertEqual(observation.observed_at, self.source.last_success_at)
        offer.refresh_from_db()
        self.assertEqual((offer.delivery_cost, offer.discount, offer.match_status), (Decimal("100"), Decimal("50"), "confirmed"))
        unchanged = self.execute(sample(listed_price=Decimal("1400")))
        self.assertEqual(unchanged.counts["offers_unchanged"], 1)
        self.assertEqual(PriceObservation.objects.count(), 1)
        for url in (f"/products/{offer.product_id}/", f"/offers/{offer.pk}/history/"):
            self.assertContains(self.client.get(url), "Provider refresh · unverified")

    def test_identity_change_resets_manual_review_and_retains_source_ids(self):
        self.execute()
        offer = Offer.objects.get()
        offer.match_status, offer.match_notes = "confirmed", "Original variant test"
        offer.save()
        run = self.execute(sample(product_name="Different test variant"))
        offer.refresh_from_db()
        self.assertEqual(offer.match_status, "unreviewed")
        self.assertIn("name", offer.match_notes)
        self.assertEqual(run.counts["reviews_reset"], 1)
        self.assertEqual(SourceOffer.objects.get().external_id, "offer-1")

    def test_failure_after_price_write_rolls_back_catalog_history_and_success_ledger(self):
        self.execute()
        previous = self.source.last_success_at
        run = self.execute(sample(listed_price=Decimal("1400")), sample(offer_id="conflicting-same-seller"))
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.counts, {})
        self.assertEqual(Offer.objects.get().price, Decimal("1200"))
        self.assertEqual(self.source.last_success_at, previous)
        self.assertEqual(self.source.status, "error")
        self.assertFalse(PriceObservation.objects.exists())

    def test_timeout_malformed_response_and_secrets_are_safe(self):
        self.execute()
        original = self.source.last_success_at
        for error in (TimeoutError("SECRET token"), RuntimeError("SECRET body")):
            run, _ = enqueue_refresh(self.source.pk)
            with patch.object(FixtureProvider, "fetch", side_effect=error), patch("core.refreshing.provider_for", return_value=FixtureProvider()):
                execute_refresh(run.pk)
            run.refresh_from_db()
            self.source.refresh_from_db()
            self.assertEqual(run.status, "failed")
            self.assertNotIn("SECRET", run.error + self.source.last_error)
            self.assertEqual(self.source.last_success_at, original)
        run = self.execute(sample(currency="USD"))
        self.assertEqual(run.status, "failed")
        self.assertEqual(Offer.objects.count(), 1)

    def test_provider_factory_failure_also_sets_safe_source_error(self):
        run, _ = enqueue_refresh(self.source.pk)
        with patch("core.refreshing.provider_for", side_effect=RuntimeError("PRIVATE setting")):
            execute_refresh(run.pk)
        self.source.refresh_from_db()
        run.refresh_from_db()
        self.assertEqual(self.source.status, "error")
        self.assertNotIn("PRIVATE", run.error)
        self.assertIsNotNone(self.source.last_attempt_at)

    def test_due_schedules_intervals_disable_and_no_catchup_storm(self):
        now = timezone.now()
        self.assertEqual(enqueue_due(now), 0)
        self.source.refresh_enabled = True
        self.source.refresh_interval_minutes = 30
        self.source.save()
        self.assertEqual(enqueue_due(now), 1)
        self.assertEqual(enqueue_due(now), 0)
        self.source.refresh_from_db()
        self.assertEqual(self.source.next_refresh_at, now + timedelta(minutes=30))
        execute_refresh(RefreshRun.objects.get().pk)
        self.assertEqual(enqueue_due(now + timedelta(minutes=29)), 0)
        self.assertEqual(enqueue_due(now + timedelta(days=30)), 1)
        self.assertEqual(RefreshRun.objects.count(), 2)

    def test_disabled_scheduled_task_cancelled_but_explicit_manual_attempt_allowed(self):
        self.source.refresh_enabled = True
        self.source.save()
        enqueue_due()
        self.source.refresh_enabled = False
        self.source.save()
        run = RefreshRun.objects.get()
        execute_refresh(run.pk)
        run.refresh_from_db()
        self.assertEqual(run.status, "cancelled")
        self.source.refresh_from_db()
        self.assertIsNone(self.source.last_attempt_at)
        manual, _ = enqueue_refresh(self.source.pk)
        execute_refresh(manual.pk)
        manual.refresh_from_db()
        self.assertEqual(manual.status, "blocked")

    def test_csv_cannot_be_scheduled_or_queued(self):
        csv_source = DataSource.objects.create(key="fallback", marketplace=self.market)
        with self.assertRaises(InvalidSourceData):
            enqueue_refresh(csv_source.pk)
        csv_source.refresh_enabled = True
        with self.assertRaises(ValidationError):
            csv_source.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            csv_source.save()

    def test_interval_validation(self):
        for interval in (0, 4, 10081):
            self.source.refresh_interval_minutes = interval
            with self.assertRaises(ValidationError):
                self.source.full_clean()
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.source.save()

    def test_recovery_releases_active_slot_and_fences_late_worker(self):
        run = RefreshRun.objects.create(source=self.source, status="running", started_at=timezone.now()-timedelta(hours=1))
        self.assertEqual(recover_stuck(15), 1)
        with self.assertRaises(InvalidSourceData):
            run_import(FixtureProvider(), key=self.source.key, marketplace=self.market, apply=True, refresh_run=run)
        self.assertFalse(Offer.objects.exists())
        run.refresh_from_db()
        self.assertEqual(run.status, "failed")
        self.assertTrue(enqueue_refresh(self.source.pk)[1])

    def test_worker_command_once_and_invalid_arguments(self):
        self.source.refresh_enabled = True
        self.source.save()
        out = io.StringIO()
        call_command("refresh_sources", once=True, stdout=out)
        self.assertEqual(RefreshRun.objects.get().status, "blocked")
        self.assertIn("BLOCKED", out.getvalue())
        call_command("refresh_sources", once=True, stdout=out)
        self.assertEqual(RefreshRun.objects.count(), 1)
        for options in ({"poll_seconds":0}, {"poll_seconds":301}, {"recover_stuck_minutes":0}):
            with self.assertRaises(CommandError):
                call_command("refresh_sources", once=True, **options)

    def test_continuous_worker_polls_and_stops_cleanly(self):
        with patch("core.management.commands.refresh_sources.time.sleep", side_effect=KeyboardInterrupt), patch(
                "core.management.commands.refresh_sources.worker_pass", return_value=(0, 0)) as work:
            out = io.StringIO()
            call_command("refresh_sources", stdout=out)
            work.assert_called_once()
            self.assertIn("Worker stopped", out.getvalue())


class RefreshInterfaceTests(TestCase):
    def setUp(self):
        self.market = Marketplace.objects.create(name="Kaspi.kz")
        self.source = DataSource.objects.create(key="kaspi-pending", marketplace=self.market, provider="kaspi")
        self.staff = get_user_model().objects.create_user(username="operator", is_staff=True)
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=["add_datasource", "change_datasource"], content_type__app_label="core"))
        self.manage = f"/data-sources/{self.source.pk}/manage/"
        self.refresh = f"/data-sources/{self.source.pk}/refresh/"

    def config(self, **changes):
        return {"key":"kaspi-new", "marketplace":self.market.pk, "provider":"kaspi",
                "refresh_interval_minutes":"60", "stale_after_hours":"24", **changes}

    def test_private_management_requires_staff_and_explicit_permissions(self):
        for path in (self.manage, "/data-sources/new/"):
            self.assertEqual(self.client.get(path).status_code, 302)
        self.assertEqual(self.client.post(self.refresh).status_code, 302)
        user = get_user_model().objects.create_user(username="ordinary")
        user.user_permissions.add(*self.staff.user_permissions.all())
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.manage).status_code, 403)
        user.is_staff = True
        user.user_permissions.clear()
        user.save()
        self.assertEqual(self.client.get(self.manage).status_code, 403)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(self.manage), "Kaspi competitor acquisition is blocked.")

    def test_csrf_post_only_duplicate_clicks_and_no_inline_execution(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        self.assertEqual(client.get(self.refresh).status_code, 405)
        client.get(self.manage)
        self.assertEqual(client.post(self.refresh).status_code, 403)
        data = {"csrfmiddlewaretoken":client.cookies['csrftoken'].value}
        self.assertEqual(client.post(self.refresh, data).status_code, 302)
        client.post(self.refresh, data)
        self.assertEqual(RefreshRun.objects.count(), 1)
        run = RefreshRun.objects.get()
        self.assertEqual(run.status, "queued")
        self.assertEqual(run.requested_by, self.staff)
        self.assertFalse(Offer.objects.exists())

    def test_create_validate_and_save_schedule_without_network_settings(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post("/data-sources/new/", self.config(refresh_interval_minutes="1")).status_code, 200)
        self.assertEqual(DataSource.objects.count(), 1)
        response = self.client.post("/data-sources/new/", self.config(refresh_enabled="on", endpoint="https://PRIVATE", token="SECRET"))
        self.assertEqual(response.status_code, 302)
        source = DataSource.objects.get(key="kaspi-new")
        self.assertTrue(source.refresh_enabled)
        self.assertIsNotNone(source.next_refresh_at)
        self.assertEqual(source.status, "never")
        page = self.client.get(response['Location'])
        self.assertNotContains(page, "SECRET")
        self.assertNotContains(page, "PRIVATE")

    def test_source_identity_cannot_be_reassigned_and_interval_can_change(self):
        self.client.force_login(self.staff)
        response = self.client.post(self.manage, self.config(key="tampered", provider="csv", refresh_enabled="on", refresh_interval_minutes="30"))
        self.assertEqual(response.status_code, 302)
        self.source.refresh_from_db()
        self.assertEqual((self.source.key, self.source.provider), ("kaspi-pending", "kaspi"))
        self.assertEqual(self.source.refresh_interval_minutes, 30)
        self.assertIsNotNone(self.source.next_refresh_at)

    def test_configuration_save_does_not_overwrite_new_worker_status(self):
        self.client.force_login(self.staff)
        original_save = DataSourceConfigureForm.save
        completed = timezone.now()

        def worker_finished_while_form_was_open(form, *args, **kwargs):
            DataSource.objects.filter(pk=self.source.pk).update(status="success", last_success_at=completed)
            return original_save(form, *args, **kwargs)

        with patch.object(DataSourceConfigureForm, "save", worker_finished_while_form_was_open):
            self.client.post(self.manage, self.config())
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, "success")
        self.assertEqual(self.source.last_success_at, completed)

    def test_unknown_source_and_blocked_run_status(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/data-sources/99999/manage/').status_code, 404)
        self.assertEqual(self.client.post('/data-sources/99999/refresh/').status_code, 404)
        run, _ = enqueue_refresh(self.source.pk)
        execute_refresh(run.pk)
        page = self.client.get(self.manage)
        self.assertContains(page, "Blocked — provider access required")
        self.assertContains(page, "no marketplace request was made")

    def test_public_page_keeps_errors_private_and_describes_fallback_truthfully(self):
        self.source.last_error = "Operator-only detail"
        self.source.save()
        page = self.client.get('/data-sources/')
        self.assertContains(page, "CSV is a fallback")
        self.assertContains(page, "Kaspi competitor feed · access not verified")
        self.assertNotContains(page, self.source.last_error)
        self.assertNotContains(page, self.manage)
