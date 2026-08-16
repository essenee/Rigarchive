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

        cls.unpopulated_mfr, _ = Manufacturer.objects.get_or_create(
            name="UnpopulatedMfr",
            defaults={"country_code": "DE"},
        )

        cls.four_runner, _ = VehicleModel.objects.get_or_create(
            manufacturer=cls.toyota,
            name="4Runner",
        )

        cls.unpopulated_model, _ = VehicleModel.objects.get_or_create(
            manufacturer=cls.unpopulated_mfr,
            name="UnpopulatedModel",
        )

        cls.bronco, _ = VehicleModel.objects.get_or_create(
            manufacturer=cls.ford,
            name="Bronco",
        )

        cls.fourth_generation, _ = Generation.objects.get_or_create(
            vehicle_model=cls.four_runner,
            name="Fourth Generation",
            slug="fourth-generation",
            defaults={
                "generation_number": 4,
                "start_year": 2003,
                "end_year": 2009,
                "notes": "Fourth generation built on Land Cruiser Prado platform.",
            },
        )

        cls.fifth_generation, _ = Generation.objects.get_or_create(
            vehicle_model=cls.four_runner,
            name="Fifth Generation",
            slug="fifth-generation",
            defaults={
                "generation_number": 5,
                "start_year": 2010,
            },
        )

        cls.bronco_gen1, _ = Generation.objects.get_or_create(
            vehicle_model=cls.bronco,
            name="First Generation",
            slug="first-generation",
            defaults={
                "generation_number": 1,
                "start_year": 1966,
                "end_year": 1977,
            },
        )

        cls.vd_2003_v6, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fourth_generation,
            model_year=2003,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.vd_2003_v8, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fourth_generation,
            model_year=2003,
            trim_name="SR5",
            engine_name="4.7L V8",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.vd_2004_sr5, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.fourth_generation,
            model_year=2004,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        cls.vd_2007_sr5, _ = VehicleDefinition.objects.get_or_create(
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

        cls.vd_bronco, _ = VehicleDefinition.objects.get_or_create(
            generation=cls.bronco_gen1,
            model_year=1970,
            trim_name="Base",
            engine_name="4.9L V8",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

    def test_1_vehicles_index_lists_active_manufacturers_and_their_models(self) -> None:
        """1. /vehicles/ lists active Manufacturers and includes their populated model links directly."""
        response = self.client.get(reverse("reference:manufacturer-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota")
        self.assertContains(response, "4Runner")
        self.assertContains(response, "Ford")
        self.assertContains(response, "Bronco")
        self.assertContains(response, self.four_runner.get_absolute_url())

    def test_2_generation_archive_cards_render_thumbnail_and_fallback(self) -> None:
        """RA-032.1 & .2. Generation archive cards render bounded thumbnail container and fallback."""
        response = self.client.get(self.toyota.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "card-thumbnail-wrap")
        self.assertContains(response, "card-thumbnail-img")
        self.assertContains(response, "fourth-generation.jpg")

        res_ford = self.client.get(self.ford.get_absolute_url())
        self.assertEqual(res_ford.status_code, 200)
        self.assertContains(res_ford, "card-thumbnail-placeholder")

    def test_3_no_implicit_domain_requirement_on_generation_model(self) -> None:
        """RA-032.3. Confirm zero domain model attribute additions to Generation in reference/models.py."""
        self.assertFalse(hasattr(Generation, "hero_image_url"))

    def test_4_generation_landing_page_wikipedia_overview_infobox(self) -> None:
        """RA-032.4, .5, .6, .7, .8, .9, .10. Overview infobox contains image, production, sequence, manufacturer, notes."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "generation-infobox")
        self.assertContains(response, "infobox-img")
        self.assertContains(response, "2003–2009")
        self.assertContains(response, "Generation 4")
        self.assertContains(response, "Toyota")
        self.assertContains(response, "Fourth generation built on Land Cruiser Prado platform.")
        self.assertNotContains(response, "Market Scope")
        self.assertNotContains(response, '<dt>Production years</dt>')

    def test_5_unpopulated_measurements_and_camping_builds_headings_absent(self) -> None:
        """RA-032.12 & .13. Measurements and Camping Builds headings do not render without integrated domain data."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="detailed-specs"')
        self.assertNotContains(response, '<section class="archive-section" id="measurements">')
        self.assertNotContains(response, '<section class="archive-section" id="camping-builds">')

    def test_6_year_only_selection_resolves_to_year_overview(self) -> None:
        """RA-032.7. Year-only selection redirects to model-year overview route."""
        response = self.client.get(self.fourth_generation.get_absolute_url() + "?year=2003")
        expected_url = reverse(
            "reference:model-year-overview",
            kwargs={
                "manufacturer_slug": "toyota",
                "vehicle_model_slug": "4runner",
                "generation_slug": "fourth-generation",
                "model_year": 2003,
            },
        )
        self.assertRedirects(response, expected_url)

    def test_7_matching_year_plus_configuration_redirects_to_exact_vehicle_definition(self) -> None:
        """RA-032.8. Matching year + configuration selection redirects directly to exact VehicleDefinition detail page."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2003_v8.slug}"
        )
        self.assertRedirects(response, self.vd_2003_v8.get_absolute_url())

    def test_8_mismatched_year_plus_configuration_is_rejected(self) -> None:
        """RA-032.9. Mismatched year + configuration (e.g. year=2003 & 2004 config) rejects cross-year navigation."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2004_sr5.slug}"
        )
        expected_2003_overview = reverse(
            "reference:model-year-overview",
            kwargs={
                "manufacturer_slug": "toyota",
                "vehicle_model_slug": "4runner",
                "generation_slug": "fourth-generation",
                "model_year": 2003,
            },
        )
        # Must NOT redirect to 2004 configuration detail page!
        self.assertNotEqual(response.headers.get("Location"), self.vd_2004_sr5.get_absolute_url())
        self.assertRedirects(response, expected_2003_overview)

    def test_9_inactive_configuration_selection_is_rejected(self) -> None:
        """RA-032.10. Inactive/superseded configuration selection is rejected."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2007&configuration={self.superseded_definition.slug}"
        )
        self.assertNotEqual(response.headers.get("Location"), self.superseded_definition.get_absolute_url())

    def test_10_cross_generation_configuration_selection_is_rejected(self) -> None:
        """RA-032.11. Configuration slug from a different generation is rejected."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2020&configuration={self.fifth_gen_definition.slug}"
        )
        self.assertNotEqual(response.headers.get("Location"), self.fifth_gen_definition.get_absolute_url())

    def test_11_year_overview_contains_only_real_active_canonical_combinations(self) -> None:
        """RA-032.14. Model-year overview contains only real active canonical combinations."""
        url = reverse(
            "reference:model-year-overview",
            kwargs={
                "manufacturer_slug": "toyota",
                "vehicle_model_slug": "4runner",
                "generation_slug": "fourth-generation",
                "model_year": 2003,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2003 Toyota 4Runner")
        self.assertContains(response, "SR5")
        self.assertContains(response, "2WD")
        self.assertContains(response, "4.0L V6")
        self.assertContains(response, "4.7L V8")
        self.assertNotContains(response, "Limited")
        self.assertContains(response, self.vd_2003_v6.get_absolute_url())
        self.assertContains(response, self.vd_2003_v8.get_absolute_url())

    def test_12_initial_configuration_selector_is_disabled_with_placeholder(self) -> None:
        """RA-032 Disabled State. Initial configuration selector is rendered disabled with placeholder text."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="config-select" class="specs-selector-select" disabled>')
        self.assertContains(response, 'Select model year first')

    def test_13_unpopulated_manufacturers_and_models_are_excluded_from_index(self) -> None:
        """RA-033 Public Visibility. Unpopulated taxonomy remains in database but is excluded publicly until populated."""
        # 1. Verify unpopulated entities exist validly in the database
        self.assertTrue(Manufacturer.objects.filter(name="UnpopulatedMfr").exists())
        self.assertTrue(VehicleModel.objects.filter(name="UnpopulatedModel").exists())

        # 2. Verify they do NOT render on public /vehicles/ archive index
        response = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Toyota")
        self.assertContains(response, "4Runner")
        self.assertNotContains(response, "UnpopulatedMfr")
        self.assertNotContains(response, "UnpopulatedModel")

        # 3. Populate an active VehicleDefinition under UnpopulatedMfr / UnpopulatedModel
        gen, _ = Generation.objects.get_or_create(
            vehicle_model=self.unpopulated_model,
            name="First Generation",
            slug="first-gen-unpop",
            defaults={"start_year": 2020},
        )
        VehicleDefinition.objects.create(
            generation=gen,
            model_year=2020,
            trim_name="Base",
            engine_name="2.0L I4",
            drivetrain=VehicleDefinition.Drivetrain.TWO_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
            is_active=True,
        )

        # 4. Verify they now render on public /vehicles/ archive index
        pop_response = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(pop_response.status_code, 200)
        self.assertContains(pop_response, "UnpopulatedMfr")
        self.assertContains(pop_response, "UnpopulatedModel")