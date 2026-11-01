"""Navigation contracts for the photographic hierarchy; no production data."""
from django.test import TestCase
from django.urls import reverse
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition
from reference.tests.test_experimental_hub import ConfiguratorParser


class VehicleVisualContinuityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.make = Manufacturer.objects.create(name='Toyota')
        cls.model = VehicleModel.objects.create(manufacturer=cls.make, name='4Runner')
        # Deliberately insert out of chronological order.
        cls.second = Generation.objects.create(vehicle_model=cls.model, name='Second Generation', start_year=1990, end_year=1995)
        cls.first = Generation.objects.create(vehicle_model=cls.model, name='First Generation', start_year=1984, end_year=1989)
        VehicleDefinition.objects.create(generation=cls.second, model_year=1990, trim_name='SR5', engine_name='V6', drivetrain='4WD', market='US')

    def test_photographic_cards_keep_canonical_links_and_chronology(self):
        response = self.client.get(self.model.get_absolute_url())
        self.assertContains(response, 'generation-photo-card', count=2)
        self.assertContains(response, 'Explore Generation →', count=2)
        cards = [a for a in ConfiguratorParser(response.text).links if a['attrs'].get('class') == 'generation-photo-card']
        self.assertEqual([a['attrs']['href'] for a in cards], [self.first.get_absolute_url(), self.second.get_absolute_url()])
        self.assertIn('1984–1989', cards[0]['text'])
        self.assertNotContains(response, 'class="archive-nav-card"')

    def test_breadcrumbs_return_to_explore_and_preserve_ancestry(self):
        selector = reverse('reference:vehicle-selector') + '?destination=generations'
        for path in [self.model.get_absolute_url(), self.second.get_absolute_url()]:
            response = self.client.get(path)
            # The header and breadcrumb both use the same selector destination.
            links = ConfiguratorParser(response.text).links
            vehicles = [a for a in links if a['text'].strip() == 'Vehicles']
            self.assertEqual(len(vehicles), 2)
            self.assertTrue(all(a['attrs']['href'] == selector for a in vehicles))
            self.assertContains(response, self.make.get_absolute_url())

    def test_overview_is_noninteractive_but_real_navigation_remains(self):
        response = self.client.get(self.second.get_absolute_url())
        self.assertContains(response, 'Coming later')
        links = ConfiguratorParser(response.text).links
        for fragment in ['#history', '#platform-design', '#powertrains', '#year-changes', '#production-numbers']:
            self.assertFalse(any(a['attrs'].get('href') == fragment for a in links))
        self.assertTrue(any('data-generation-filter' in a['attrs'] and '?year=1990' in a['attrs']['href'] for a in links))
        self.assertTrue(any('/measurements/' in a['attrs'].get('href', '') for a in links))
        self.assertEqual(response.text.count('class="gen-identity-block"'), 1)
        self.assertLess(response.text.index('class="gen-identity-block"'), response.text.index('class="gen-hero-photo-wrap"'))

    def test_legacy_manufacturer_cards_keep_their_existing_variant(self):
        response = self.client.get(self.make.get_absolute_url())
        self.assertContains(response, 'generation-nav-card')
        self.assertNotContains(response, 'class="generation-photo-card"')
