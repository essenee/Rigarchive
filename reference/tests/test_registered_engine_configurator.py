"""Registered Engine presentation must survive drivetrain-only alternatives."""
from decimal import Decimal

from django.test import TestCase

from reference.models import Engine, Generation, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import _label_configuration_choices


class RegisteredEngineConfiguratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Toyota")
        model = VehicleModel.objects.create(manufacturer=maker, name="4Runner")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Sixth Generation", start_year=2025)
        cls.engine = Engine.objects.create(
            manufacturer=maker, engine_code="T24A-FTS", name="2.4L 4-Cyl. Turbo",
            engine_displacement_liters=Decimal("2.4"), engine_cylinders=4,
            engine_aspiration="turbocharged", fuel_type="gasoline", electrification_type="none")
        cls.rows = [VehicleDefinition.objects.create(
            generation=cls.generation, model_year=2026, trim_name="TRD Sport Premium",
            engine=cls.engine, engine_name="2.4L Turbo I4", drivetrain=drive, market="US",
            engine_aspiration="turbocharged") for drive in ("2WD", "4WD")]

    def test_rendered_year_trim_and_exact_links_keep_registry_engine_and_drive(self):
        before = list(VehicleDefinition.objects.values())
        for params in ({"year": 2026, "trim": "TRD Sport Premium"},
                       {"configuration": self.rows[1].slug}):
            response = self.client.get(self.generation.get_absolute_url(), params)
            self.assertEqual(response.status_code, 200)
            choices = response.context["configuration_browser_choices"]
            self.assertEqual({row.pk for row in choices}, {row.pk for row in self.rows})
            for row in choices:
                self.assertEqual(row.choice_label, f"2.4L 4-Cyl. · Turbocharged · {row.drivetrain}")
                self.assertContains(response, row.choice_label)
                self.assertNotIn("Turbo I4", row.choice_label)
                self.assertFalse(row.choice_ambiguous)
            if "configuration" in params:
                self.assertEqual(response.context["selected_config"].pk, self.rows[1].pk)
                self.assertContains(response, 'aria-current="true"')
        self.assertEqual(list(VehicleDefinition.objects.values()), before)

    def test_distinct_registered_engines_same_trim_and_drive_remain_distinct(self):
        other = Engine.objects.create(manufacturer=self.engine.manufacturer,
                                      engine_code="OTHER", name="Other registered Engine")
        row = VehicleDefinition(engine=other, engine_name="Historical", drivetrain="4WD", trim_name="TRD Sport Premium")
        choices = _label_configuration_choices([self.rows[1], row])
        self.assertEqual(len(choices), 2)
        self.assertIn("Other registered Engine", choices[1].choice_label)
        self.assertTrue(all("4WD" in choice.choice_label for choice in choices))
        self.assertTrue(all(not choice.choice_ambiguous for choice in choices))

    def test_missing_optional_fields_and_legacy_fallback(self):
        linked = VehicleDefinition(engine=self.engine, engine_name="Old", drivetrain="UNK")
        legacy = VehicleDefinition(engine_name="Legacy wording", drivetrain="4WD")
        labels = _label_configuration_choices([linked, legacy])
        self.assertIn("2.4L 4-Cyl. Turbo", labels[0].choice_label)
        self.assertIn("Drive wheels not specified", labels[0].choice_label)
        self.assertEqual(labels[1].choice_label, "Legacy wording · 4WD")
