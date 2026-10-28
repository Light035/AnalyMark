"""Coverage cards present database facts without relabelling imported data as demo."""
from django.test import TestCase
from django.urls import reverse

from core.marketplaces import initialize_marketplaces, APPROVED_NAMES
from core.models import Marketplace, Offer, Product


class MarketplacePresentationTests(TestCase):
    def setUp(self):
        initialize_marketplaces()
        self.market = Marketplace.objects.get(name="Kaspi.kz")
        self.product = Product.objects.create(name="Specific test variant", category="Test")

    def add_offer(self, seller, *, demo=True):
        return Offer.objects.create(product=self.product, marketplace=self.market,
                                    seller_name=seller, price="100", is_demo=demo)

    def card(self, response, market=None):
        market = market or self.market
        return response.content.decode().split(f'aria-labelledby="market-title-{market.pk}">', 1)[1].split("</article>", 1)[0]

    def test_card_counts_distinct_products_and_all_stored_offers(self):
        self.add_offer("Demo A")
        self.add_offer("Demo B")
        rejected = self.add_offer("Demo rejected")
        rejected.match_status = "rejected"
        rejected.save()
        response = self.client.get(reverse("core:data_sources"))
        market = next(m for m in response.context["marketplace_coverage"] if m.pk == self.market.pk)
        self.assertEqual((market.product_count, market.offer_count, market.demo_count), (1, 3, 3))
        card = self.card(response)
        self.assertIn('<dt>Products</dt><dd>1</dd>', card)
        self.assertIn('<dt>Offers</dt><dd>3</dd>', card)
        self.assertIn('DEMO', card)

    def test_mixed_and_supplied_records_are_not_badged_demo_only(self):
        demo = self.add_offer("Demo")
        self.add_offer("Supplied", demo=False)
        response = self.client.get(reverse("core:data_sources"))
        self.assertIn('Mixed data', self.card(response))
        self.assertNotIn('>DEMO<', self.card(response))
        demo.delete()
        response = self.client.get(reverse("core:data_sources"))
        self.assertIn('Supplied data', self.card(response))
        self.assertNotIn('>DEMO<', self.card(response))

    def test_empty_markets_have_zero_counts_and_no_demo_claim(self):
        response = self.client.get(reverse("core:data_sources"))
        self.assertIn('No offers', self.card(response))
        self.assertIn('<dt>Products</dt><dd>0</dd>', self.card(response))
        self.assertIn('<dt>Offers</dt><dd>0</dd>', self.card(response))
        self.assertNotIn('>DEMO<', self.card(response))

    def test_five_cards_in_target_order_and_working_filter_links(self):
        archived = Marketplace.objects.create(name="Outside scope", is_active=False)
        Offer.objects.create(product=self.product, marketplace=archived, seller_name="Archived", price="900")
        response = self.client.get(reverse("core:data_sources"))
        self.assertTemplateUsed(response, 'core/includes/marketplace_cards.html')
        self.assertContains(response, 'class="marketplace-card market-', count=5)
        html = response.content.decode()
        positions = [html.index(f'id="market-title-{Marketplace.objects.get(name=name).pk}"') for name in APPROVED_NAMES]
        self.assertEqual(positions, sorted(positions))
        self.assertNotContains(response, 'Outside scope')
        for name in APPROVED_NAMES:
            market = Marketplace.objects.get(name=name)
            self.assertIn(f'?marketplace={market.pk}', self.card(response, market))
            filtered = self.client.get(reverse('core:product_search'), {'marketplace': market.pk})
            self.assertEqual(filtered.status_code, 200)
            self.assertEqual(filtered.context['offers'], [])

    def test_no_marketplace_rows_keeps_honest_empty_state(self):
        Marketplace.objects.all().delete()
        response = self.client.get(reverse('core:data_sources'))
        self.assertContains(response, 'No marketplace labels loaded.')
        self.assertNotContains(response, 'class="marketplace-card market-')

    def test_global_search_and_language_form_keep_existing_get_contract(self):
        self.add_offer('Demo')
        target = reverse('core:product_search') + f'?q=Specific&marketplace={self.market.pk}&sort=price_desc&page=1'
        response = self.client.get(target)
        self.assertContains(response, 'class="workspace-search" method="get" action="/products/"')
        self.assertContains(response, 'label class="visually-hidden" for="workspace-query"')
        self.assertContains(response, 'id="workspace-query" name="q" type="search"')
        self.assertContains(response, 'name="next" value="' + target.replace('&', '&amp;') + '"')
        self.assertEqual(len(response.context['offers']), 1)

    def test_russian_card_labels_keep_market_names_and_real_counts(self):
        self.add_offer('Demo')
        response = self.client.get(reverse('core:data_sources'), HTTP_ACCEPT_LANGUAGE='ru')
        self.assertIn('ДЕМО', self.card(response))
        self.assertIn('Kaspi.kz', self.card(response))
        self.assertContains(response, 'Онлайн-данные не подключены.', count=1)
        self.assertContains(response, 'Как данные попадают в систему')

    def test_watchlist_preview_is_bounded_active_and_keeps_provenance(self):
        from django.contrib.auth import get_user_model
        from core.models import WatchlistEntry
        user = get_user_model().objects.create_user(username='card-owner')
        other = get_user_model().objects.create_user(username='other-card-owner')
        private = Product.objects.create(name='Other private saved product', category='Test')
        WatchlistEntry.objects.create(user=user, product=self.product)
        WatchlistEntry.objects.create(user=other, product=private)
        self.add_offer('A supplied', demo=False)
        for index in range(5):
            self.add_offer(f'Demo {index}')
        archive = Marketplace.objects.create(name='Archived test', is_active=False)
        Offer.objects.create(product=self.product, marketplace=archive, seller_name='Archive seller', price='9')
        self.client.force_login(user)
        response = self.client.get(reverse('core:watchlist'))
        preview = response.context['entries'][0].product.watchlist_preview
        self.assertEqual(len(preview), 3)
        self.assertTrue(all(offer.marketplace_id == self.market.pk for offer in preview))
        self.assertContains(response, 'Supplied data')
        self.assertContains(response, '>DEMO<')
        self.assertContains(response, 'Listed prices only.')
        self.assertContains(response, '100.00')
        self.assertNotContains(response, private.name)
        self.assertNotContains(response, 'Archive seller')

    def test_russian_demo_count_uses_correct_plural_forms(self):
        for count, expected in [(1, '1 демопредложение'), (2, '2 демопредложения'),
                                (5, '5 демопредложений'), (21, '21 демопредложение')]:
            while self.product.offers.count() < count:
                self.add_offer(f'Demo {self.product.offers.count()}')
            with self.subTest(count=count):
                response = self.client.get(reverse('core:data_sources'), HTTP_ACCEPT_LANGUAGE='ru')
                self.assertIn(expected, self.card(response))

    def test_russian_csv_instructions_identify_the_destination_file(self):
        response = self.client.get(reverse('core:data_sources'), HTTP_ACCEPT_LANGUAGE='ru')
        self.assertContains(response, 'в файл')
        self.assertContains(response, 'offers.local.csv')

    def test_dashboard_does_not_label_imported_observations_as_only_manual(self):
        from core.models import PriceObservation
        offer = self.add_offer('Supplied', demo=False)
        PriceObservation.objects.create(offer=offer, price='100', is_demo=False, recorded_by_import=True)
        response = self.client.get(reverse('core:dashboard'))
        self.assertContains(response, 'manually recorded or imported, unverified')
        self.assertNotContains(response, 'manually recorded, unverified')

    def test_sidebar_has_one_text_label_per_market_and_no_wide_wordmarks(self):
        response = self.client.get(reverse('core:data_sources'))
        sidebar = response.content.decode().split('class="market-navigation"', 1)[1].split('</nav>', 1)[0]
        for name in APPROVED_NAMES:
            market = Marketplace.objects.get(name=name)
            self.assertIn(f'?marketplace={market.pk}', sidebar)
            self.assertEqual(sidebar.count(f'class="market-sidebar-label">{name}</span>'), 1)
        self.assertNotIn('kaspi.svg', sidebar)
        self.assertNotIn('halyk.svg', sidebar)
        self.assertNotIn('market-sidebar-fallback', sidebar)
        self.assertEqual(sidebar.count('alt=""'), 5)
        for filename in ('kaspi-icon.png', 'halyk-app.webp', 'wildberries-icon.png', 'ozon.webp', 'teez.webp'):
            self.assertIn('/static/images/marketplaces/' + filename, sidebar)
        # The right-hand cards and sidebar must use the same non-seasonal assets.
        for name, filename in [('Kaspi.kz', 'kaspi-icon.png'), ('Halyk Market', 'halyk-app.webp'),
                               ('Wildberries', 'wildberries-icon.png')]:
            self.assertIn('/static/images/marketplaces/' + filename,
                          self.card(response, Marketplace.objects.get(name=name)))
        self.assertNotIn('kaspi-app.webp', response.content.decode())
        self.assertNotIn('wildberries-app.webp', response.content.decode())
        self.assertContains(response, 'aria-current="page"')

    def test_sidebar_selected_market_keeps_filter_link_and_current_state(self):
        response = self.client.get(reverse('core:product_search'), {'marketplace': self.market.pk})
        sidebar = response.content.decode().split('class="market-navigation"', 1)[1].split('</nav>', 1)[0]
        self.assertIn(f'href="/products/?marketplace={self.market.pk}" aria-current="page"', sidebar)
        self.assertEqual(sidebar.count('aria-current="page"'), 1)

    def test_sources_keep_one_top_notice_and_detailed_provenance_below(self):
        self.add_offer('Demo')
        response = self.client.get(reverse('core:data_sources'))
        self.assertContains(response, 'class="data-notice"', count=1)
        self.assertContains(response, 'No live data connected.', count=1)
        self.assertNotContains(response, 'class="connection-card"')
        self.assertNotContains(response, 'Marketplace labels are not integrations.')
        self.assertContains(response, 'Fictional examples, clearly labelled. No marketplace prices were fetched.')
        self.assertContains(response, 'Supplied records with validation, a preview and actual import times.')
        self.assertContains(response, 'Competitor feed blocked pending approved access')
        self.assertIn('DEMO', self.card(response))
