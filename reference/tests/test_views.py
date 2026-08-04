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
        cls.toyota = Manufacturer.objects.create(
            name="Toyota",
            country_code="JP",
        )

        cls.four_runner = VehicleModel.objects.create(
            manufacturer=cls.toyota,
            name="4Runner",
        )

        cls.fourth_generation = Generation.objects.create(
            vehicle_model=cls.four_runner,
            name="Fourth Generation",
            generation_number=4,
            start_year=2003,
            end_year=2009,
        )

        cls.vehicle_definition = VehicleDefinition.objects.create(
            generation=cls.fourth_generation,
            model_year=2007,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
        )

    def test_manufacturer_list_displays_active_manufacturer(self) -> None:
        response = self.client.get(
            reverse("reference:manufacturer-list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota")

    def test_manufacturer_detail_displays_vehicle_model(self) -> None:
        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4Runner")

    def test_vehicle_model_detail_displays_generation(self) -> None:
        response = self.client.get(self.four_runner.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fourth Generation")

    def test_generation_detail_displays_vehicle_definition(self) -> None:
        response = self.client.get(
            self.fourth_generation.get_absolute_url()
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2007")
        self.assertContains(response, "SR5")
        self.assertContains(response, "4.0L V6")

    def test_vehicle_definition_detail_displays_configuration(self) -> None:
        response = self.client.get(
            self.vehicle_definition.get_absolute_url()
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota")
        self.assertContains(response, "4Runner")
        self.assertContains(response, "Fourth Generation")
        self.assertContains(response, "2007")
        self.assertContains(response, "SR5")
        self.assertContains(response, "4.0L V6")
        self.assertContains(response, "Four-wheel drive")
        self.assertContains(response, "United States")

    def test_inactive_manufacturer_is_not_public(self) -> None:
        self.toyota.is_active = False
        self.toyota.save()

        response = self.client.get(self.toyota.get_absolute_url())

        self.assertEqual(response.status_code, 404)

    def test_nested_url_rejects_wrong_manufacturer(self) -> None:
        incorrect_url = reverse(
            "reference:vehicle-model-detail",
            kwargs={
                "manufacturer_slug": "not-toyota",
                "vehicle_model_slug": self.four_runner.slug,
            },
        )

        response = self.client.get(incorrect_url)

        self.assertEqual(response.status_code, 404)