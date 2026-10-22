from django.contrib.staticfiles import finders
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse


class ApplicationShellTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="shell-user")

    def setUp(self):
        self.client.force_login(self.user)

    routes = {
        "dashboard": "/",
        "product_search": "/products/",
        "watchlist": "/watchlist/",
        "analytics": "/analytics/",
    }

    def test_dashboard_renders_the_shared_shell(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Dashboard | AnalyMark")
        self.assertContains(response, "Skip to content")
        self.assertContains(response, "core/css/app.css")

    def test_named_routes_resolve_and_render(self):
        for name, url in self.routes.items():
            with self.subTest(route=name):
                self.assertEqual(reverse(f"core:{name}"), url)
                self.assertEqual(resolve(url).view_name, f"core:{name}")
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_every_page_links_to_all_workspace_sections(self):
        for url in self.routes.values():
            with self.subTest(url=url):
                response = self.client.get(url)
                for destination in self.routes.values():
                    self.assertContains(response, f'href="{destination}"')
                self.assertContains(response, 'aria-current="page"', count=1)

    def test_every_page_discloses_that_live_data_is_unavailable(self):
        for url in self.routes.values():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "No live data connected.")
                self.assertContains(response, "Demonstration MVP")

    def test_analytics_is_a_product_selection_page(self):
        response = self.client.get(reverse("core:analytics"))
        self.assertTemplateUsed(response, "core/analytics.html")
        self.assertContains(response, "Product analytics")
        self.assertContains(response, "No products to analyze")

    def test_pages_accept_head_but_reject_post(self):
        for url in self.routes.values():
            with self.subTest(url=url):
                self.assertEqual(self.client.head(url).status_code, 200)
                self.assertEqual(self.client.post(url).status_code, 405)

    def test_unknown_route_returns_not_found(self):
        self.assertEqual(self.client.get("/does-not-exist/").status_code, 404)

    def test_local_stylesheet_is_discoverable(self):
        self.assertIsNotNone(finders.find("core/css/app.css"))
