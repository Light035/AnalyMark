from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Marketplace, Offer, Product, WatchlistEntry


class WatchlistTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = get_user_model().objects.create_user(username="alice", password="Only-for-tests-724!")
        cls.bob = get_user_model().objects.create_user(username="bob")
        cls.lamp = Product.objects.create(name="Shared lamp", brand="DemoBrand", category="Lighting")
        cls.other = Product.objects.create(name="Bob-only saved product", category="Office")
        marketplace = Marketplace.objects.create(name="Demo market")
        Offer.objects.create(product=cls.lamp, marketplace=marketplace, seller_name="Demo", price="100.00")

    def test_anonymous_users_are_redirected_for_private_routes(self):
        for route, kwargs, method, destination in (
            ("watchlist", {}, "get", reverse("core:watchlist")),
            ("watchlist_add", {"product_id": self.lamp.pk}, "post", reverse("core:product_detail", args=[self.lamp.pk])),
            ("watchlist_remove", {"product_id": self.lamp.pk}, "post", reverse("core:watchlist")),
        ):
            with self.subTest(route=route):
                url = reverse(f"core:{route}", kwargs=kwargs)
                response = getattr(self.client, method)(url)
                self.assertRedirects(response, f"{reverse('core:login')}?next={destination}", fetch_redirect_response=False)
        self.assertFalse(WatchlistEntry.objects.exists())

    def test_search_remains_public(self):
        response = self.client.get(reverse("core:product_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in to save product")

    def test_watchlist_only_displays_the_current_users_entries(self):
        WatchlistEntry.objects.create(user=self.alice, product=self.lamp)
        WatchlistEntry.objects.create(user=self.bob, product=self.other)
        self.client.force_login(self.alice)
        response = self.client.get(reverse("core:watchlist"), {"user": self.bob.pk})
        self.assertContains(response, self.lamp.name)
        self.assertContains(response, "DemoBrand")
        self.assertContains(response, "Lighting")
        self.assertNotContains(response, self.other.name)
        self.assertContains(response, reverse("core:product_detail", args=[self.lamp.pk]))
        self.assertContains(response, 'aria-label="Remove product: Shared lamp"')
        self.assertContains(response, f'<a href="{reverse("core:product_detail", args=[self.lamp.pk])}">Shared lamp</a>', html=True)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_add_uses_session_owner_ignoring_posted_user_id(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("core:watchlist_add", args=[self.lamp.pk]), {"user": self.bob.pk}, follow=True)
        self.assertContains(response, "Saved Shared lamp to your Watchlist.")
        self.assertTrue(WatchlistEntry.objects.filter(user=self.alice, product=self.lamp).exists())
        self.assertFalse(WatchlistEntry.objects.filter(user=self.bob).exists())

    def test_repeat_save_is_idempotent_and_feedback_is_visible(self):
        self.client.force_login(self.alice)
        url = reverse("core:watchlist_add", args=[self.lamp.pk])
        self.client.post(url)
        response = self.client.post(url, follow=True)
        self.assertContains(response, "already in your Watchlist")
        self.assertEqual(WatchlistEntry.objects.count(), 1)

    def test_database_prevents_duplicate_user_product_entries(self):
        WatchlistEntry.objects.create(user=self.alice, product=self.lamp)
        with self.assertRaises(IntegrityError), transaction.atomic():
            WatchlistEntry.objects.create(user=self.alice, product=self.lamp)
        WatchlistEntry.objects.create(user=self.bob, product=self.lamp)
        self.assertEqual(WatchlistEntry.objects.count(), 2)

    def test_remove_only_deletes_the_current_users_entry(self):
        WatchlistEntry.objects.create(user=self.alice, product=self.lamp)
        WatchlistEntry.objects.create(user=self.bob, product=self.lamp)
        self.client.force_login(self.alice)
        response = self.client.post(reverse("core:watchlist_remove", args=[self.lamp.pk]), follow=True)
        self.assertContains(response, "Product removed")
        self.assertFalse(WatchlistEntry.objects.filter(user=self.alice).exists())
        self.assertTrue(WatchlistEntry.objects.filter(user=self.bob).exists())

    def test_cannot_remove_another_users_saved_product(self):
        entry = WatchlistEntry.objects.create(user=self.bob, product=self.other)
        self.client.force_login(self.alice)
        response = self.client.post(reverse("core:watchlist_remove", args=[self.other.pk]), follow=True)
        self.assertContains(response, "That product is not in your Watchlist.")
        self.assertTrue(WatchlistEntry.objects.filter(pk=entry.pk).exists())

    def test_mutation_routes_reject_get(self):
        self.client.force_login(self.alice)
        for name in ("watchlist_add", "watchlist_remove"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(f"core:{name}", args=[self.lamp.pk])).status_code, 405)
        self.assertFalse(WatchlistEntry.objects.exists())

    def test_invalid_product_is_not_saved(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.post(reverse("core:watchlist_add", args=[99999])).status_code, 404)
        self.assertFalse(WatchlistEntry.objects.exists())

    def test_empty_state_and_saved_status_are_user_specific(self):
        WatchlistEntry.objects.create(user=self.bob, product=self.lamp)
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("core:watchlist")), "Your Watchlist is empty")
        self.assertContains(self.client.get(reverse("core:product_search")), "Save product")
        self.client.force_login(self.bob)
        self.assertContains(self.client.get(reverse("core:product_search")), "Saved to your Watchlist")

    def test_csrf_protection_rejects_missing_tokens_and_accepts_real_forms(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.alice)
        add_url = reverse("core:watchlist_add", args=[self.lamp.pk])
        remove_url = reverse("core:watchlist_remove", args=[self.lamp.pk])
        self.assertEqual(client.post(add_url).status_code, 403)
        self.assertEqual(client.post(remove_url).status_code, 403)
        response = client.get(reverse("core:product_search"))
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        token = client.cookies["csrftoken"].value
        self.assertRedirects(client.post(add_url, {"csrfmiddlewaretoken": token}), reverse("core:watchlist"))
        response = client.get(reverse("core:watchlist"))
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertRedirects(client.post(remove_url, {"csrfmiddlewaretoken": token}), reverse("core:watchlist"))
        self.assertFalse(WatchlistEntry.objects.exists())

    def test_login_logout_and_safe_next_redirects(self):
        login = reverse("core:login")
        response = self.client.get(login)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, "Log in to AnalyMark")
        response = self.client.post(login, {"username": "alice", "password": "wrong"})
        self.assertContains(response, "Please enter a correct username and password")
        response = self.client.post(login, {
            "username": "alice", "password": "Only-for-tests-724!", "next": "https://untrusted.example/"
        })
        self.assertRedirects(response, reverse("core:watchlist"))
        logout = reverse("core:logout")
        self.assertEqual(self.client.get(logout).status_code, 405)
        self.assertRedirects(self.client.post(logout), login)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_and_logout_also_enforce_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("core:login"), {"username": "alice"}).status_code, 403)
        client.get(reverse("core:login"))
        response = client.post(reverse("core:login"), {
            "username": "alice", "password": "Only-for-tests-724!",
            "next": reverse("core:product_search"), "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("core:product_search"))
        self.assertEqual(client.post(reverse("core:logout")).status_code, 403)
        client.get(reverse("core:watchlist"))
        self.assertRedirects(client.post(reverse("core:logout"), {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}), reverse("core:login"))
