"""Local authentic logos render consistently without network dependencies."""
from pathlib import Path
import xml.etree.ElementTree as ET

from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from core.marketplaces import MARKETPLACES


class BrandAssetTests(SimpleTestCase):
    def test_supported_brands_render_local_images_with_accessible_names(self):
        for key, name, _ in MARKETPLACES:
            with self.subTest(marketplace=name):
                filename = f'{key}-icon.png' if key in ('kaspi', 'wildberries') else ('halyk-app.webp' if key == 'halyk' else f'{key}.webp')
                asset = f'images/marketplaces/{filename}'
                self.assertTrue(finders.find(asset))
                html = render_to_string('core/includes/marketplace_identity.html', {'market': name})
                self.assertIn(f'src="/static/{asset}"', html)
                self.assertIn(f'alt="{name}"', html)
                self.assertNotIn('<svg', html)
                image_tag = html.split('<img', 1)[1].split('>', 1)[0]
                self.assertNotIn('aria-hidden', image_tag)

    def test_svg_assets_are_self_contained_and_passive(self):
        for key in ('kaspi', 'halyk', 'wildberries'):
            root = ET.parse(finders.find(f'images/marketplaces/{key}.svg')).getroot()
            for element in root.iter():
                self.assertNotIn(element.tag.split('}')[-1], ('script', 'foreignObject', 'image'))
                for attribute in element.attrib:
                    self.assertFalse(attribute.lower().startswith('on'))
                    self.assertFalse(attribute.endswith('href'))
        for key in ('ozon', 'teez'):
            data = Path(finders.find(f'images/marketplaces/{key}.webp')).read_bytes()
            self.assertEqual(data[:4], b'RIFF')
            self.assertEqual(data[8:12], b'WEBP')

    def test_unknown_brand_uses_neutral_fallback_not_an_invented_logo(self):
        html = render_to_string('core/includes/marketplace_identity.html', {'market': 'Archived example'})
        self.assertIn('market-archive', html)
        self.assertIn('Archived example', html)
        self.assertNotIn('<img', html)
