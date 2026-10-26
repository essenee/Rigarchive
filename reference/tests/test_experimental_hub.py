from decimal import Decimal
from django.test import TestCase
from django.urls import reverse

from measurements.models import MeasurementDefinition, MeasurementResult
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)
from reference.services import (
    get_generation_hub_context,
    get_homepage_context,
    get_full_specifications_context,
)


class ExperimentalVehicleHubAndHomepageTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.toyota = Manufacturer.objects.create(name="Toyota", country_code="JP")
        cls.four_runner = VehicleModel.objects.create(
            manufacturer=cls.toyota,
            name="4Runner",
            slug="4runner",
        )
        cls.fourth_generation = Generation.objects.create(
            vehicle_model=cls.four_runner,
            name="Fourth Generation",
            slug="fourth-generation",
            generation_number=4,
            start_year=2003,
            end_year=2009,
            notes="Fourth generation built on Land Cruiser Prado 120 platform.",
        )
        cls.fifth_generation = Generation.objects.create(
            vehicle_model=cls.four_runner,
            name="Fifth Generation",
            slug="fifth-generation",
            generation_number=5,
            start_year=2010,
            end_year=2024,
        )

        cls.vd_2003_v6 = VehicleDefinition.objects.create(
            generation=cls.fourth_generation,
            model_year=2003,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )
        cls.vd_2003_v8 = VehicleDefinition.objects.create(
            generation=cls.fourth_generation,
            model_year=2003,
            trim_name="Limited",
            engine_name="4.7L V8",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )
        cls.vd_2004_sr5 = VehicleDefinition.objects.create(
            generation=cls.fourth_generation,
            model_year=2004,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )
        cls.vd_2007_sr5 = VehicleDefinition.objects.create(
            generation=cls.fourth_generation,
            model_year=2007,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )
        cls.vd_fifth_gen = VehicleDefinition.objects.create(
            generation=cls.fifth_generation,
            model_year=2020,
            trim_name="TRD Pro",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        # Physical measurements for Fourth Generation
        cls.meas_def = MeasurementDefinition.objects.create(
            name="Maximum Cargo Interior Height",
            slug="maximum-cargo-interior-height",
            category=MeasurementDefinition.Category.CARGO,
            description="Vertical clearance from floor to headliner.",
        )
        cls.meas_result = MeasurementResult.objects.create(
            generation=cls.fourth_generation,
            definition=cls.meas_def,
            value=Decimal("38.60"),
            unit=MeasurementResult.Unit.INCHES,
            notes="Measured along centerline.",
        )

    # 1. Default unfiltered Generation page
    def test_default_unfiltered_generation_page(self) -> None:
        """Generation page defaults to generation-wide hub without requiring year or trim selection."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fourth Generation")
        self.assertContains(response, "Toyota 4Runner")
        self.assertContains(response, "2003–2009")
        self.assertContains(response, "Fourth generation built on Land Cruiser Prado 120 platform.")
        self.assertIsNone(response.context["selected_year"])
        self.assertIsNone(response.context["selected_config"])
        self.assertFalse(response.context["filter_active"])
        self.assertEqual(response.context["total_generation_configs"], 4)
        # Physical measurements are present on generation hub
        self.assertTrue(response.context["has_measurements"])
        self.assertContains(response, "Maximum Cargo Interior Height")
        self.assertContains(response, "38.60")

    # 2. Valid model-year filtering
    def test_valid_model_year_filtering_refines_in_place(self) -> None:
        """Selecting model year refines configurations on the Generation page in-place (HTTP 200)."""
        response = self.client.get(self.fourth_generation.get_absolute_url() + "?year=2003")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertIsNone(response.context["selected_config"])
        self.assertTrue(response.context["filter_active"])
        self.assertContains(response, "Model Year 2003")
        self.assertIn(self.vd_2003_v6, response.context["displayed_configurations"])
        self.assertIn(self.vd_2003_v8, response.context["displayed_configurations"])
        self.assertNotIn(self.vd_2004_sr5, response.context["displayed_configurations"])
        # Generation-wide measurements remain preserved
        self.assertContains(response, "Maximum Cargo Interior Height")

    # 3. Valid exact-configuration filtering
    def test_valid_exact_configuration_filtering_shows_banner_and_specs_action(self) -> None:
        """Selecting exact configuration displays context banner and Full Specifications action."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2003_v8.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertEqual(response.context["selected_config"], self.vd_2003_v8)
        self.assertTrue(response.context["filter_active"])
        self.assertContains(response, "Selected Configuration Filter")
        self.assertContains(response, "2003 4Runner Limited")
        self.assertContains(response, "View Full Specifications →")
        self.assertContains(response, self.vd_2003_v8.get_absolute_url())

    # 4. Configuration without explicit year auto-syncs year
    def test_configuration_without_explicit_year_auto_syncs(self) -> None:
        """Providing configuration slug alone automatically resolves and syncs the model year."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?configuration={self.vd_2007_sr5.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2007)
        self.assertEqual(response.context["selected_config"], self.vd_2007_sr5)

    # 5. Invalid and mismatched filter parameters
    def test_invalid_year_parameter_falls_back_cleanly(self) -> None:
        """Invalid year parameter (out of bounds or string) gracefully falls back to unfiltered view."""
        response = self.client.get(self.fourth_generation.get_absolute_url() + "?year=1990")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["selected_year"])
        self.assertFalse(response.context["filter_active"])

        response_str = self.client.get(self.fourth_generation.get_absolute_url() + "?year=invalid")
        self.assertEqual(response_str.status_code, 200)
        self.assertIsNone(response_str.context["selected_year"])

    def test_mismatched_year_and_configuration_rejects_config(self) -> None:
        """Mismatched year and configuration (e.g. year=2003 & 2004 config) does not select wrong config."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2004_sr5.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertIsNone(response.context["selected_config"])
        self.assertNotIn(self.vd_2004_sr5, response.context["displayed_configurations"])

    def test_cross_generation_configuration_cannot_be_selected(self) -> None:
        """Configuration slug from a different generation is strictly rejected from selection."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?configuration={self.vd_fifth_gen.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["selected_config"])

    # 6. Preservation of generation-wide measurements
    def test_preservation_of_generation_wide_measurements(self) -> None:
        """Generation-wide measurements remain visible and applicable across all filter states."""
        # Unfiltered
        r1 = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertContains(r1, "38.60")
        # Year filtered
        r2 = self.client.get(self.fourth_generation.get_absolute_url() + "?year=2003")
        self.assertContains(r2, "38.60")
        # Config filtered
        r3 = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2003_v8.slug}"
        )
        self.assertContains(r3, "38.60")

    # 7. Prevention of unsupported applicability claims (epistemic notices)
    def test_epistemic_forthcoming_sections_present_clear_disclaimers(self) -> None:
        """Adventure Builds and Service Maintenance are clearly framed as forthcoming without fake data."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertContains(response, "Under Active Archival")
        self.assertContains(response, "strict separation from factory baseline specifications")

    # 8. Full Specifications Page
    def test_full_specifications_page_content_and_navigation(self) -> None:
        """Full Specifications page displays comprehensive factory attributes, applicable measurements, and sibling trims."""
        response = self.client.get(self.vd_2003_v8.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Full Specifications")
        self.assertContains(response, "2003 Toyota 4Runner Limited 4.7L V8 4WD")
        self.assertContains(response, "Return to Fourth Generation Hub")
        self.assertContains(response, "Factory Technical Specifications")
        self.assertContains(response, "4.7L V8")
        self.assertContains(response, "4WD")
        # Applicable measurements surfaced on full specs page
        self.assertContains(response, "Maximum Cargo Interior Height")
        self.assertContains(response, "38.60")
        # Sibling trims from same model year (2003 SR5)
        self.assertContains(response, "Other 2003 4Runner Trims")
        self.assertContains(response, self.vd_2003_v6.get_absolute_url())
        # Epistemic notice
        self.assertContains(response, "Canonical Factory Baseline Reference")

    # 9. Existing URL compatibility
    def test_existing_canonical_urls_remain_compatible(self) -> None:
        """All existing canonical routes (/vehicles/, model detail, model-year overview, measurements) remain 100% functional."""
        # 1. Manufacturer list
        r_mfr_list = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(r_mfr_list.status_code, 200)

        # 2. Manufacturer detail
        r_mfr = self.client.get(self.toyota.get_absolute_url())
        self.assertEqual(r_mfr.status_code, 200)

        # 3. Model detail
        r_model = self.client.get(self.four_runner.get_absolute_url())
        self.assertEqual(r_model.status_code, 200)

        # 4. Generation detail (unfiltered)
        r_gen = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(r_gen.status_code, 200)

        # 5. Model-year overview direct route
        my_url = reverse(
            "reference:model-year-overview",
            kwargs={
                "manufacturer_slug": "toyota",
                "vehicle_model_slug": "4runner",
                "generation_slug": "fourth-generation",
                "model_year": 2003,
            },
        )
        r_year = self.client.get(my_url)
        self.assertEqual(r_year.status_code, 200)
        self.assertContains(r_year, "2003 Toyota 4Runner")

        # 6. Full Specifications canonical route
        r_specs = self.client.get(self.vd_2003_v8.get_absolute_url())
        self.assertEqual(r_specs.status_code, 200)

        # 7. Measurements view canonical route
        meas_url = reverse(
            "measurements:generation-measurements",
            kwargs={
                "manufacturer_slug": "toyota",
                "vehicle_model_slug": "4runner",
                "generation_slug": "fourth-generation",
            },
        )
        r_meas = self.client.get(meas_url)
        self.assertEqual(r_meas.status_code, 200)

    # 10. Homepage behavior with populated and missing optional content
    def test_homepage_renders_content_led_design(self) -> None:
        """Homepage renders compelling headline, statistics, platform cards, and measurement teaser."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Know your vehicle.")
        self.assertContains(response, "Build with confidence.")
        self.assertContains(response, "Featured Expedition Platforms")
        self.assertContains(response, "4Runner")
        self.assertContains(response, "The Four Pillars of RigArchive")
        self.assertContains(response, "Measured Reality: Beyond Brochure Claims")
        self.assertContains(response, "38.60")

    def test_homepage_graceful_handling_without_measurements(self) -> None:
        """Homepage handles missing measurements gracefully without crashing or broken layout."""
        MeasurementResult.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Measured Reality: Beyond Brochure Claims")
        self.assertContains(response, "Know your vehicle.")
