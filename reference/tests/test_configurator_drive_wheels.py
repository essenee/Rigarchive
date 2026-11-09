"""Presentation-only drive categories; no canonical mutation or mode inference."""
from django.test import SimpleTestCase, TestCase
from reference.models import VehicleDefinition, Manufacturer, VehicleModel, Generation
from reference.services import _label_configuration_choices


class DriveWheelChoiceLabelTests(SimpleTestCase):
    def choice(self, drivetrain, engine="4.0L V6", trim="Sport", **extra):
        return VehicleDefinition(model_year=2021, trim_name=trim, engine_name=engine,
                                 drivetrain=drivetrain, market="US", **extra)

    def labels(self, records):
        return [r.choice_label for r in _label_configuration_choices(records)]

    def test_shared_category_remains_visible_across_different_engines(self):
        for drive in ("2WD", "4WD", "AWD"):
            with self.subTest(drive=drive):
                labels = self.labels([self.choice(drive), self.choice(drive, engine="4.7L V8")])
                self.assertEqual(labels, [f"4.0L V6 · {drive}", f"4.7L V8 · {drive}"])
                self.assertTrue(all(label.split(" · ").count(drive) == 1 for label in labels))

    def test_drive_only_alternatives_do_not_repeat_engine_or_drive(self):
        self.assertEqual(self.labels([self.choice("2WD"), self.choice("4WD"), self.choice("AWD")]),
                         ["2WD", "4WD", "AWD"])

    def test_single_choice_and_different_trims_keep_drive_category(self):
        self.assertEqual(self.labels([self.choice("4WD")]), ["4.0L V6 · 4WD"])
        self.assertEqual(self.labels([self.choice("4WD", trim="Sport"), self.choice("4WD", trim="Limited")]),
                         ["Sport · 4WD", "Limited · 4WD"])

    def test_unknown_or_missing_values_are_explicit_without_guessing(self):
        for drive in ("UNK", "", None):
            with self.subTest(drive=drive):
                self.assertEqual(self.labels([self.choice(drive, trim="AWD edition")]),
                                 ["4.0L V6 · Drive wheels not specified"])

    def test_conflicting_or_unsupported_values_require_review(self):
        # FWD/RWD are not accepted canonical enum values; do not silently map them.
        for drive in ("2WD/4WD", "FWD", "RWD", "4x4", "unexpected"):
            with self.subTest(drive=drive):
                self.assertEqual(self.labels([self.choice(drive)]),
                                 ["4.0L V6 · Drive wheels require review"])

    def test_front_or_rear_wording_is_not_inferred_from_trim_engine_or_notes(self):
        for wording in ("FWD", "RWD", "Front-wheel drive", "Rear-wheel drive"):
            with self.subTest(wording=wording):
                record = self.choice("2WD", trim=wording, notes=wording)
                self.assertEqual(self.labels([record]), ["4.0L V6 · 2WD"])
                self.assertEqual(record.trim_name, wording)
                self.assertEqual(record.notes, wording)
                self.assertEqual(record.drivetrain, "2WD")

    def test_multiple_modes_remain_separate_from_canonical_4wd(self):
        notes = "Full-time 4WD; selectable 2H, 4H, 4L; low range; locking center differential."
        record = self.choice("4WD", notes=notes)
        self.assertEqual(self.labels([record]), ["4.0L V6 · 4WD"])
        self.assertEqual(record.notes, notes)
        self.assertEqual(record.drivetrain, "4WD")

    def test_empty_set_and_market_disambiguation_are_preserved(self):
        self.assertEqual(self.labels([]), [])
        a = self.choice("AWD")
        b = self.choice("AWD")
        b.market = "CA"
        self.assertEqual(self.labels([a, b]),
                         ["4.0L V6 · AWD · United States (US)", "4.0L V6 · AWD · Canada (CA)"])


class DriveWheelConfiguratorPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Drive display test")
        model = VehicleModel.objects.create(manufacturer=maker, name="Factory choices")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Test generation", start_year=2021)
        cls.choices = [VehicleDefinition.objects.create(
            generation=cls.generation, model_year=2021, trim_name="Sport",
            engine_name=engine, drivetrain=drive, market="US")
            for engine, drive in [("2.0L I4", "4WD"), ("3.6L V6", "4WD"), ("4.0L V6", "2WD"), ("5.0L V8", "AWD"), ("1.0L I3", "UNK")]]

    def test_trim_and_exact_deep_links_show_each_drive_once_without_losing_siblings(self):
        for params in [{"year": 2021, "trim": "Sport"}, {"configuration": self.choices[0].slug}]:
            response = self.client.get(self.generation.get_absolute_url(), params)
            choices = response.context["configuration_browser_choices"]
            self.assertEqual({c.pk for c in choices}, {c.pk for c in self.choices})
            for choice in choices:
                expected = "Drive wheels not specified" if choice.drivetrain == "UNK" else choice.drivetrain
                self.assertEqual(choice.choice_label.split(" · ").count(expected), 1)
                self.assertContains(response, choice.choice_label)
                self.assertContains(response, '?year=2021&amp;configuration=' + choice.slug)
            self.assertEqual(response.context["selected_trim"], "Sport")
            if "configuration" in params:
                self.assertEqual(response.context["selected_config"].pk, self.choices[0].pk)
                self.assertContains(response, 'aria-current="true"')
