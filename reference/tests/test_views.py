from django.test import TestCase
from django.urls import reverse

from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class ReferenceViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.toyota, _ = Manufacturer.objects.get_or_create(
            name="Toyota",
            defaults={"country_code": "JP"},
        )

        cls.ford, _ = Manufacturer.objects.get_or_create(
            name="Ford",
            defaults={"country_code": "US"},
        )

        cls.four_runner, _ = VehicleModel.objects.get_or_create(
            manufacturer=cls.toyota,
            name="4Runner",
        )

        cls.bronco, _ = VehicleModel.objects.get_or_create(
            manufacturer=cls.ford,
            name="Bronco",
        )

        cls.fourth_generation, _ = Generation.objects.get_or_create(
            vehicle_model=cls.four_runner,
            name="Fourth Generation",
            defaults={
                "generation_number": 4,
                "start_year": 2003,
                "end_year": 2009,
            },
        )

        cls.fifth_generation, _ = Generation.objects.get_or_create(
            vehicle_model=cls.four_runner,
            name="Fifth Generation",
            defaults={
                "generation_number": 5,
                "start_year": 2010,
            },
        )

        cls.bronco_gen1, _ = Generation.objects.get_or_create(
            vehicle_model=cls.bronco,
            name="First Generation",
            defaults={
                "generation_number": 1,
                "start_year": 1966,
                "end_year": 1977,
            },
        )

        cls.vehicle_definition, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fourth_generation,
            model_year=2007,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.superseded_definition, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fourth_generation,
            model_year=2007,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.ALL_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=False,
        )

        cls.fifth_gen_definition, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fifth_generation,
            model_year=2020,
            trim_name="TRD Pro",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

    def test_1_vehicles_index_lists_active_manufacturers_and_their_models(self) -> None:
        """1 & 2. /vehicles/ lists active Manufacturers and includes their populated model links directly."""
        response = self.client.get(reverse("reference:manufacturer-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota")
        self.assertContains(response, "4Runner")
        self.assertContains(response, "Ford")
        self.assertContains(response, "Bronco")
        self.assertContains(response, self.four_runner.get_absolute_url())

    def test_3_models_do_not_appear_under_wrong_manufacturer_on_vehicles_index(self) -> None:
        """3. Models belonging to Manufacturer B do not appear under Manufacturer A on /vehicles/."""
        response = self.client.get(reverse("reference:manufacturer-list"))

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        ford_pos = html.find("Ford")
        bronco_pos = html.find("Bronco")
        toyota_pos = html.find("Toyota")
        four_runner_pos = html.find("4Runner")
        self.assertTrue(ford_pos < bronco_pos < toyota_pos < four_runner_pos)

    def test_4_unpopulated_or_inactive_models_do_not_appear(self) -> None:
        """4. Unpopulated or inactive models/manufacturers do not appear as available archive links."""
        inactive_mfr = Manufacturer.objects.create(name="InactiveAuto", is_active=False)
        VehicleModel.objects.create(manufacturer=inactive_mfr, name="Phantom", is_active=True)

        inactive_model = VehicleModel.objects.create(manufacturer=self.toyota, name="InactiveModel", is_active=False)

        response = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "InactiveAuto")
        self.assertNotContains(response, "Phantom")
        self.assertNotContains(response, "InactiveModel")

    def test_5_and_6_manufacturer_detail_uses_combined_heading_and_no_separate_models_heading(self) -> None:
        """5 & 6. /vehicles/toyota/ uses combined 'Toyota Models' heading and no separate 'Models' heading."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h1>Toyota Models</h1>")
        self.assertNotContains(response, "<h2>Models</h2>")

    def test_7_and_8_manufacturer_detail_lists_models_and_their_generations(self) -> None:
        """7 & 8. Manufacturer page lists its populated models and each model group lists active generations."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4Runner")
        self.assertContains(response, "Fourth Generation")
        self.assertContains(response, "Fifth Generation")

    def test_9_generations_do_not_appear_under_wrong_model(self) -> None:
        """9. Generations from another model do not appear under the wrong model."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "First Generation")  # Bronco's generation

    def test_10_generation_year_spans_render_correctly(self) -> None:
        """10. Generation year spans render correctly."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2003–2009")
        self.assertContains(response, "2010–present")

    def test_11_model_and_generation_urls_resolve_correctly(self) -> None:
        """11. Model and generation URLs resolve correctly."""
        model_res = self.client.get(self.four_runner.get_absolute_url())
        self.assertEqual(model_res.status_code, 200)

        gen_res = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(gen_res.status_code, 200)

    def test_12_inactive_superseded_canonical_content_does_not_leak(self) -> None:
        """12. Inactive/superseded canonical content does not leak into availability navigation."""
        gen_res = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertNotContains(gen_res, "Limited")
        self.assertNotContains(gen_res, self.superseded_definition.slug)

        vd_res = self.client.get(self.superseded_definition.get_absolute_url())
        self.assertEqual(vd_res.status_code, 404)

    def test_13_empty_hierarchy_states_render_without_error(self) -> None:
        """13. Empty manufacturer/model/generation states render without error."""
        empty_mfr = Manufacturer.objects.create(name="Subaru", country_code="JP")
        res_mfr = self.client.get(empty_mfr.get_absolute_url())
        self.assertEqual(res_mfr.status_code, 200)
        self.assertContains(res_mfr, "No vehicle models are currently available.")

        empty_model = VehicleModel.objects.create(manufacturer=empty_mfr, name="Outback")
        res_model = self.client.get(empty_model.get_absolute_url())
        self.assertEqual(res_model.status_code, 200)
        self.assertContains(res_model, "No generations are currently available.")

    def test_14_existing_breadcrumbs_and_deeper_routes_continue_to_work(self) -> None:
        """14. Existing breadcrumbs and deeper routes continue to work."""
        res_vd = self.client.get(self.vehicle_definition.get_absolute_url())
        self.assertEqual(res_vd.status_code, 200)
        self.assertContains(res_vd, "Vehicles")
        self.assertContains(res_vd, "Toyota")
        self.assertContains(res_vd, "4Runner")
        self.assertContains(res_vd, "Fourth Generation")
        self.assertContains(res_vd, "2007 Toyota 4Runner SR5 4.0L V6 4WD")