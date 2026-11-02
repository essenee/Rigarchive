from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from reference.models import Manufacturer, VehicleModel


class VehicleQuickSelectorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = Manufacturer.objects.create(name="Maker & Company")
        cls.model = VehicleModel.objects.create(manufacturer=cls.maker, name="Long <model> name " * 5)
        VehicleModel.objects.create(manufacturer=cls.maker, name="Inactive quick model", is_active=False)
        hidden = Manufacturer.objects.create(name="Inactive quick maker", is_active=False)
        VehicleModel.objects.create(manufacturer=hidden, name="Hidden quick model")
        Manufacturer.objects.create(name="No eligible quick models")

    def render_header(self):
        return Template('{% extends "base.html" %}').render(Context())

    def test_split_control_routes_and_progressive_enhancement(self):
        html = self.render_header()
        destination = reverse("reference:vehicle-selector") + "?destination=generations"
        self.assertIn(f'href="{destination}" class="nav-link', html)
        self.assertIn(f'href="{destination}">Browse all vehicles →</a>', html)
        self.assertIn('aria-label="Choose a vehicle"', html)
        self.assertIn('aria-expanded="false" aria-controls="vehicle-quick-panel" hidden', html)
        self.assertIn('id="vehicle-quick-panel" class="vehicle-quick-panel" hidden', html)
        self.assertIn('</a>\n                <button', html)
        self.assertNotIn('role="menu"', html)
        self.assertIn(f'href="{reverse("reference:manufacturer-list")}?view=measurements"', html)
        self.assertIn(f'href="{reverse("about")}"', html)

    def test_canonical_active_data_without_generation_coverage_and_escaping(self):
        html = self.render_header()
        self.assertIn(f'href="{self.model.get_absolute_url()}"', html)
        self.assertIn('Maker &amp; Company', html)
        self.assertIn('Long &lt;model&gt; name', html)
        for excluded in ['Inactive quick model', 'Inactive quick maker', 'Hidden quick model', 'No eligible quick models']:
            self.assertNotIn(excluded, html)
        self.assertNotIn('<model>', html)

    def test_header_queries_do_not_scale_with_models(self):
        with self.assertNumQueries(2):
            self.render_header()
        for index in range(4):
            maker = Manufacturer.objects.create(name=f"Maker {index}")
            VehicleModel.objects.create(manufacturer=maker, name="Model")
        with self.assertNumQueries(2):
            self.render_header()

    def test_empty_catalogue_and_defensive_empty_manufacturer_state(self):
        VehicleModel.objects.update(is_active=False)
        self.assertIn('No active manufacturers with eligible models are available.', self.render_header())
        # Discovery excludes empty manufacturers; the partial still handles an empty group.
        self.maker.active_vehicle_models = []
        html = Template('{% include "reference/partials/vehicle_quick_selector.html" %}').render(
            Context({"quick_manufacturers": [self.maker]})
        )
        self.assertIn('No eligible models are available for this manufacturer.', html)
