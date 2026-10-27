"""Cross-feature workflows and security boundaries for the local MVP."""
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.models import Offer, PriceObservation, Product, WatchlistEntry


class ReadinessWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="readiness-user", password="Tests-only-password-573!")
        cls.other = get_user_model().objects.create_user(username="another-user")

    def command(self, name):
        output = StringIO()
        call_command(name, stdout=output)
        return output.getvalue()

    def test_empty_to_demo_search_watchlist_and_recorded_history(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "No products loaded")
        self.assertEqual(response.context["metrics"]["products"], 0)
        self.command("load_demo_data")
        original_ids = list(Offer.objects.order_by("pk").values_list("pk", flat=True))
        self.command("load_demo_data")
        self.assertEqual(list(Offer.objects.order_by("pk").values_list("pk", flat=True)), original_ids)
        self.assertEqual(Offer.objects.count(), 18)
        self.assertFalse(PriceObservation.objects.exists())
        product = Product.objects.get(name="Luma L1 — white, single lamp")
        response = self.client.get(reverse("core:product_search"), {"product": product.pk, "q": "white, single lamp", "sort": "total_desc"})
        offers = response.context["offers"]
        self.assertEqual(len(offers), 3)
        self.assertTrue(all(o.product_id == product.pk for o in offers))
        self.assertTrue(all(o.total_buyer_cost is None for o in offers[2:]))
        self.assertEqual(self.client.get(reverse("core:product_detail", args=[product.pk])).status_code, 200)

        client = Client(enforce_csrf_checks=True)
        login = reverse("core:login")
        client.get(login)
        invalid = client.post(login, {"username": self.user.username, "password": "wrong", "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertContains(invalid, "Please enter a correct username and password")
        response = client.post(login, {"username": self.user.username, "password": "Tests-only-password-573!", "csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertRedirects(response, reverse("core:watchlist"))
        detail = reverse("core:product_detail", args=[product.pk])
        client.get(detail)
        token = client.cookies["csrftoken"].value
        add = reverse("core:watchlist_add", args=[product.pk])
        self.assertEqual(client.post(add).status_code, 403)
        client.post(add, {"csrfmiddlewaretoken": token})
        client.post(add, {"csrfmiddlewaretoken": token})
        self.assertEqual(WatchlistEntry.objects.filter(user=self.user).count(), 1)
        bob_product = Product.objects.exclude(pk=product.pk).first()
        WatchlistEntry.objects.create(user=self.other, product=bob_product)
        self.assertNotContains(client.get(reverse("core:watchlist")), bob_product.name)
        client.post(reverse("core:watchlist_remove", args=[product.pk]), {"csrfmiddlewaretoken": token})
        self.assertFalse(WatchlistEntry.objects.filter(user=self.user).exists())
        self.assertTrue(WatchlistEntry.objects.filter(user=self.other).exists())
        self.assertIn("Recorded 18", self.command("record_demo_observations"))
        self.assertIn("Recorded 0", self.command("record_demo_observations"))
        self.assertEqual(PriceObservation.objects.count(), 18)
        response = client.get(detail)
        self.assertEqual(sum(len(group["chart"]["points"]) for group in response.context["charts"]), 3)
        self.assertContains(response, "Demonstration observation · not live")
        self.assertEqual(client.get(reverse("core:product_detail", args=[99999])).status_code, 404)
        self.assertEqual(client.get(reverse("core:price_history", args=[99999])).status_code, 404)
        client.get(reverse("core:watchlist"))
        self.assertRedirects(client.post(reverse("core:logout"), {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}), login)

    def test_expired_session_returns_to_a_readable_page_without_replaying_mutations(self):
        product = Product.objects.create(name="Session test product", category="Office")
        for action, destination in (
            ("watchlist_add", reverse("core:product_detail", args=[product.pk])),
            ("watchlist_remove", reverse("core:watchlist")),
        ):
            with self.subTest(action=action):
                self.client.force_login(self.user)
                session = self.client.session
                session.flush()  # Expired server session while an old form remains open.
                response = self.client.post(reverse(f"core:{action}", args=[product.pk]))
                next_url = parse_qs(urlsplit(response["Location"]).query)["next"][0]
                self.assertEqual(next_url, destination)
                response = self.client.post(reverse("core:login"), {"username": self.user.username, "password": "Tests-only-password-573!", "next": next_url})
                self.assertRedirects(response, destination)
                self.assertFalse(WatchlistEntry.objects.filter(user=self.user).exists())

    def test_mutation_gets_are_never_executed_even_for_anonymous_users(self):
        for action in ("watchlist_add", "watchlist_remove"):
            self.assertEqual(self.client.get(reverse(f"core:{action}", args=[1])).status_code, 405)

    def test_csrf_rejects_a_foreign_origin_even_with_a_valid_token(self):
        product = Product.objects.create(name="CSRF test product", category="Office")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse("core:product_detail", args=[product.pk]))
        response = client.post(reverse("core:watchlist_add", args=[product.pk]), {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}, HTTP_ORIGIN="https://untrusted.example")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(WatchlistEntry.objects.exists())

    def test_login_and_logout_reject_external_return_urls(self):
        for target in ("https://untrusted.example/", "//untrusted.example/", "///untrusted.example/", "javascript:alert(1)", "http://testserver.untrusted.example/"):
            with self.subTest(target=target):
                self.client.logout()
                response = self.client.post(reverse("core:login"), {"username": self.user.username, "password": "Tests-only-password-573!", "next": target})
                self.assertRedirects(response, reverse("core:watchlist"))
                self.assertRedirects(self.client.post(reverse("core:logout"), {"next": target}), reverse("core:login"))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["localhost", "127.0.0.1"])
    def test_unapproved_hosts_are_rejected(self):
        self.assertEqual(self.client.get("/", HTTP_HOST="untrusted.example").status_code, 400)
        self.assertEqual(self.client.get("/", HTTP_HOST="localhost").status_code, 200)

    @override_settings(DEBUG=False)
    def test_local_files_and_configuration_are_not_public_routes(self):
        for path in ("/db.sqlite3", "/.env", "/.git/config", "/config/settings/local.py", "/Reports/AnalyMark_Assignment3.docx", "/.venv/pyvenv.cfg"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertNotContains(response, "DJANGO_SECRET_KEY", status_code=404)

    def test_private_responses_have_cache_and_standard_browser_protection_headers(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:watchlist"))
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("Cookie", response.headers["Vary"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")


class LocalConfigurationTests(SimpleTestCase):
    def test_debug_disabled_requires_a_private_secret_and_keeps_loopback_hosts(self):
        env = os.environ.copy()
        env.pop("DJANGO_SECRET_KEY", None)
        env.pop("DJANGO_ALLOWED_HOSTS", None)
        env["DJANGO_DEBUG"] = "false"
        code = "import config.settings.local"
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set DJANGO_SECRET_KEY", result.stderr)
        # A disposable test value is never printed or used by the development database.
        env["DJANGO_SECRET_KEY"] = "configuration-test-only-" * 4
        code = "import config.settings.local as s; import json; print(json.dumps({'debug':s.DEBUG,'hosts':s.ALLOWED_HOSTS}))"
        result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {"debug": False, "hosts": ["localhost", "127.0.0.1", "[::1]"]})
