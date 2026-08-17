from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from reference.models import Generation, Manufacturer, VehicleModel
from measurements.models import (
    ApplicabilityFeature,
    ApplicabilityState,
    MeasurementDefinition,
    MeasurementResult,
    MeasurementResultCondition,
)


class MeasurementsViewTests(TestCase):
    def setUp(self):
        self.manufacturer = Manufacturer.objects.create(
            name="Toyota",
            country_code="JP",
        )
        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="4Runner",
        )
        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Fourth Generation",
            start_year=2003,
            end_year=2009,
        )

        self.def_opening_height = MeasurementDefinition.objects.create(
            name="Cargo Opening Height",
            category=MeasurementDefinition.Category.CARGO,
            description="Usable vertical height of rear cargo opening.",
        )
        self.def_behind_second_row = MeasurementDefinition.objects.create(
            name="Cargo Height Behind Second Row",
            category=MeasurementDefinition.Category.CARGO,
            description="Vertical interior height measured immediately behind second-row seating.",
        )

        self.sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        self.sunroof_present = ApplicabilityState.objects.create(feature=self.sunroof, name="Present")
        self.sunroof_absent = ApplicabilityState.objects.create(feature=self.sunroof, name="Absent")

    def test_15_generation_measurements_route_resolves(self):
        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        self.assertEqual(url, "/vehicles/toyota/4runner/fourth-generation/measurements/")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_16_page_renders_generation_identity(self):
        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4Runner — Fourth Generation Measurements")
        self.assertContains(response, "Toyota")

    def test_17_page_renders_definition_value_unit(self):
        MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )

        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cargo Opening Height")
        self.assertContains(response, "37.25")
        self.assertContains(response, "in")

    def test_18_page_identifies_generation_wide_results(self):
        MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )

        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generation-wide")

    def test_19_page_renders_feature_state_conditions(self):
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_behind_second_row,
            value=Decimal("33.00"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(result=result, state=self.sunroof_present)

        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sunroof: Present")

    def test_20_empty_generation_measurements_page(self):
        url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Physical Measurements Recorded")
        self.assertContains(response, "Absence of recorded measurements in RigArchive does not indicate")

    def test_21_generation_detail_links_to_measurements(self):
        url = reverse(
            "reference:generation-detail",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        measurements_url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.generation.slug,
            },
        )
        self.assertContains(response, measurements_url)

    def test_22_reference_browser_intact(self):
        response_mfr_list = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(response_mfr_list.status_code, 200)

        response_mfr_detail = self.client.get(self.manufacturer.get_absolute_url())
        self.assertEqual(response_mfr_detail.status_code, 200)

        response_gen_detail = self.client.get(self.generation.get_absolute_url())
        self.assertEqual(response_gen_detail.status_code, 200)
