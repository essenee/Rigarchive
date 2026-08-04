from django.core.exceptions import ValidationError
from django.test import TestCase

from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class ReferenceModelTests(TestCase):
    def setUp(self) -> None:
        self.toyota = Manufacturer.objects.create(
            name="Toyota",
            country_code="JP",
        )

        self.four_runner = VehicleModel.objects.create(
            manufacturer=self.toyota,
            name="4Runner",
        )

        self.fourth_generation = Generation.objects.create(
            vehicle_model=self.four_runner,
            name="Fourth Generation",
            generation_number=4,
            start_year=2003,
            end_year=2009,
        )

    def test_manufacturer_string_representation(self) -> None:
        self.assertEqual(str(self.toyota), "Toyota")

    def test_vehicle_model_string_representation(self) -> None:
        self.assertEqual(str(self.four_runner), "Toyota 4Runner")

    def test_generation_rejects_invalid_year_range(self) -> None:
        generation = Generation(
            vehicle_model=self.four_runner,
            name="Invalid Generation",
            slug="invalid-generation",
            start_year=2010,
            end_year=2009,
        )

        with self.assertRaises(ValidationError):
            generation.full_clean()

    def test_vehicle_definition_accepts_valid_model_year(self) -> None:
        vehicle = VehicleDefinition(
            generation=self.fourth_generation,
            model_year=2007,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            slug="2007-sr5-v6-4wd-us",
        )

        vehicle.full_clean()
        vehicle.save()

        self.assertEqual(vehicle.generation, self.fourth_generation)

    def test_vehicle_definition_rejects_year_outside_generation(self) -> None:
        vehicle = VehicleDefinition(
            generation=self.fourth_generation,
            model_year=2010,
            trim_name="SR5",
            slug="2010-sr5",
        )

        with self.assertRaises(ValidationError):
            vehicle.full_clean()

def test_manufacturer_slug_is_generated(self) -> None:
    self.assertEqual(self.toyota.slug, "toyota")


def test_vehicle_model_slug_is_generated(self) -> None:
    self.assertEqual(self.four_runner.slug, "4runner")


def test_generation_slug_is_generated(self) -> None:
    self.assertEqual(
        self.fourth_generation.slug,
        "fourth-generation",
    )


def test_vehicle_definition_slug_is_generated(self) -> None:
    vehicle = VehicleDefinition.objects.create(
        generation=self.fourth_generation,
        model_year=2007,
        trim_name="SR5",
        engine_name="4.0L V6",
        drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
        market=VehicleDefinition.Market.UNITED_STATES,
    )

    self.assertEqual(
        vehicle.slug,
        "2007-sr5-40l-v6-4wd-us",
    )


def test_existing_slug_does_not_change_after_edit(self) -> None:
    vehicle = VehicleDefinition.objects.create(
        generation=self.fourth_generation,
        model_year=2007,
        trim_name="SR5",
        engine_name="4.0L V6",
        drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
        market=VehicleDefinition.Market.UNITED_STATES,
    )

    original_slug = vehicle.slug

    vehicle.trim_name = "Limited"
    vehicle.save()
    vehicle.refresh_from_db()

    self.assertEqual(vehicle.slug, original_slug)