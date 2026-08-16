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

    def test_1_manufacturer_page_lists_its_vehicle_models(self) -> None:
        """1. Manufacturer page lists its VehicleModels."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4Runner")

    def test_2_manufacturer_page_does_not_list_models_belonging_to_another_manufacturer(self) -> None:
        """2. Manufacturer page does not list models belonging to another manufacturer."""
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4Runner")
        self.assertNotContains(response, "Bronco")

    def test_3_vehicle_model_page_lists_its_generations(self) -> None:
        """3. VehicleModel page lists its Generations."""
        response = self.client.get(self.four_runner.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fourth Generation")
        self.assertContains(response, "Fifth Generation")

    def test_4_vehicle_model_page_does_not_list_generations_belonging_to_another_model(self) -> None:
        """4. VehicleModel page does not list generations belonging to another model."""
        response = self.client.get(self.four_runner.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "First Generation")

    def test_5_generation_links_resolve_correctly(self) -> None:
        """5. Generation links resolve correctly."""
        gen_url = self.fourth_generation.get_absolute_url()
        response = self.client.get(gen_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota 4Runner — Fourth Generation")

    def test_6_breadcrumbs_contain_the_correct_hierarchy(self) -> None:
        """6. Breadcrumbs contain the correct hierarchy across all navigation levels."""
        # Manufacturer List
        res_mfr_list = self.client.get(reverse("reference:manufacturer-list"))
        self.assertContains(res_mfr_list, "Vehicles")

        # Manufacturer Detail
        res_mfr_detail = self.client.get(self.toyota.get_absolute_url())
        self.assertContains(res_mfr_detail, "Vehicles")
        self.assertContains(res_mfr_detail, "Toyota")

        # Model Detail
        res_model_detail = self.client.get(self.four_runner.get_absolute_url())
        self.assertContains(res_model_detail, "Vehicles")
        self.assertContains(res_model_detail, "Toyota")
        self.assertContains(res_model_detail, "4Runner")

        # Generation Detail
        res_gen_detail = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertContains(res_gen_detail, "Vehicles")
        self.assertContains(res_gen_detail, "Toyota")
        self.assertContains(res_gen_detail, "4Runner")
        self.assertContains(res_gen_detail, "Fourth Generation")

        # VehicleDefinition Detail
        res_vd_detail = self.client.get(self.vehicle_definition.get_absolute_url())
        self.assertContains(res_vd_detail, "Vehicles")
        self.assertContains(res_vd_detail, "Toyota")
        self.assertContains(res_vd_detail, "4Runner")
        self.assertContains(res_vd_detail, "Fourth Generation")
        self.assertContains(res_vd_detail, "2007 Toyota 4Runner SR5 4.0L V6 4WD")

    def test_7_generation_page_lists_only_vehicle_definitions_from_that_generation(self) -> None:
        """7. Generation page lists only VehicleDefinitions from that generation."""
        response = self.client.get(self.fourth_generation.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2007 Toyota 4Runner SR5 4.0L V6 4WD")
        self.assertNotContains(response, "2020 Toyota 4Runner TRD Pro 4.0L V6 4WD")

    def test_8_superseded_inactive_vehicle_definitions_do_not_appear(self) -> None:
        """8. Superseded/inactive VehicleDefinitions do not appear."""
        # Generation detail page excludes inactive definitions
        res_gen = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertNotContains(res_gen, "Limited")
        self.assertNotContains(res_gen, self.superseded_definition.slug)

        # VehicleDefinition detail page returns 404 for superseded record
        res_superseded_detail = self.client.get(self.superseded_definition.get_absolute_url())
        self.assertEqual(res_superseded_detail.status_code, 404)

    def test_9_empty_hierarchy_states_render_without_error(self) -> None:
        """9. Empty manufacturer/model/generation states render without error."""
        empty_mfr = Manufacturer.objects.create(name="Subaru", country_code="JP")
        res_mfr = self.client.get(empty_mfr.get_absolute_url())
        self.assertEqual(res_mfr.status_code, 200)
        self.assertContains(res_mfr, "No vehicle models are currently available.")

        empty_model = VehicleModel.objects.create(manufacturer=empty_mfr, name="Outback")
        res_model = self.client.get(empty_model.get_absolute_url())
        self.assertEqual(res_model.status_code, 200)
        self.assertContains(res_model, "No generations are currently available.")

        empty_gen = Generation.objects.create(
            vehicle_model=empty_model,
            name="First Generation",
            start_year=1995,
            end_year=1999,
        )
        res_gen = self.client.get(empty_gen.get_absolute_url())
        self.assertEqual(res_gen.status_code, 200)
        self.assertContains(res_gen, "No vehicle definitions are currently available.")

    def test_10_existing_custom_404_500_public_navigation_tests_remain_intact(self) -> None:
        """10. Existing custom 404/500/public navigation tests remain intact."""
        # Inactive manufacturer 404 check
        self.toyota.is_active = False
        self.toyota.save()
        res_inactive_mfr = self.client.get(self.toyota.get_absolute_url())
        self.assertEqual(res_inactive_mfr.status_code, 404)

        # Nested URL wrong manufacturer 404 check
        incorrect_url = reverse(
            "reference:vehicle-model-detail",
            kwargs={
                "manufacturer_slug": "not-toyota",
                "vehicle_model_slug": self.four_runner.slug,
            },
        )
        res_wrong_path = self.client.get(incorrect_url)
        self.assertEqual(res_wrong_path.status_code, 404)