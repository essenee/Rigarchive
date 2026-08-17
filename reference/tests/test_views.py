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


class RA037GenerationImageTests(TestCase):
    def test_01_get_presentation_hero_image_url_resolution(self) -> None:
        """RA-037. Resolution helper distinguishes models and prevents cross-model fallback."""
        from reference.views import get_presentation_hero_image_url

        # 4Runner 4th Gen
        url_4runner_4 = get_presentation_hero_image_url("toyota", "4runner", "fourth-generation")
        self.assertEqual(url_4runner_4, "/static/images/generations/toyota-4runner-fourth-generation.jpg")

        # Tacoma 4th Gen (must NOT use 4Runner image)
        url_tacoma_4 = get_presentation_hero_image_url("toyota", "tacoma", "fourth-generation")
        self.assertEqual(url_tacoma_4, "/static/images/generations/toyota-tacoma-fourth-generation.jpg")
        self.assertNotEqual(url_tacoma_4, url_4runner_4)

        # Tacoma 1st Gen
        self.assertEqual(get_presentation_hero_image_url("toyota", "tacoma", "first-generation"), "/static/images/generations/toyota-tacoma-first-generation.jpg")

        # Tacoma 2nd Gen
        self.assertEqual(get_presentation_hero_image_url("toyota", "tacoma", "second-generation"), "/static/images/generations/toyota-tacoma-second-generation.jpg")

        # Tacoma 3rd Gen
        self.assertEqual(get_presentation_hero_image_url("toyota", "tacoma", "third-generation"), "/static/images/generations/toyota-tacoma-third-generation.jpg")

        # Touareg 1st Gen
        self.assertEqual(get_presentation_hero_image_url("volkswagen", "touareg", "first-generation"), "/static/images/generations/volkswagen-touareg-first-generation.jpg")

        # Touareg 2nd Gen
        self.assertEqual(get_presentation_hero_image_url("volkswagen", "touareg", "second-generation"), "/static/images/generations/volkswagen-touareg-second-generation.jpg")

        # Missing image falls back to generic placeholder (empty string)
        self.assertEqual(get_presentation_hero_image_url("unknown_mfr", "unknown_model", "fourth-generation"), "")

    def test_02_generation_model_purity(self) -> None:
        """RA-037. Confirms no image fields or DB properties were added to Generation model."""
        fields = [f.name for f in Generation._meta.get_fields()]
        self.assertNotIn("hero_image", fields)
        self.assertNotIn("hero_image_url", fields)
        self.assertNotIn("image", fields)

    def test_03_live_page_hero_image_rendering(self) -> None:
        """RA-037. Generation thumbnails and overview infoboxes render model-specific imagery on live pages."""
        # Toyota Tacoma model page
        mfr_toyota, _ = Manufacturer.objects.get_or_create(name="Toyota")
        model_tacoma, _ = VehicleModel.objects.get_or_create(manufacturer=mfr_toyota, name="Tacoma")
        gen_tacoma_4, _ = Generation.objects.get_or_create(
            vehicle_model=model_tacoma,
            name="Fourth Generation",
            slug="fourth-generation",
            defaults={"start_year": 2024},
        )
        VehicleDefinition.objects.get_or_create(
            generation=gen_tacoma_4,
            model_year=2024,
            trim_name="SR5",
            engine_name="2.4L I4",
            drivetrain="4WD",
            is_active=True,
        )

        resp_model = self.client.get(model_tacoma.get_absolute_url())
        self.assertEqual(resp_model.status_code, 200)
        self.assertContains(resp_model, "/static/images/generations/toyota-tacoma-fourth-generation.jpg")
        self.assertNotContains(resp_model, "/static/images/generations/fourth-generation.jpg")

        resp_gen = self.client.get(gen_tacoma_4.get_absolute_url())
        self.assertEqual(resp_gen.status_code, 200)
        self.assertContains(resp_gen, "/static/images/generations/toyota-tacoma-fourth-generation.jpg")

    def test_04_shared_hero_image_css_contract(self) -> None:
        """RA-037. Confirms infobox-img and card-thumbnail-img CSS maintain generic shared object-position center contract."""
        import os
        from django.conf import settings
        css_path = os.path.join(settings.BASE_DIR, "static", "css", "site.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        self.assertIn("object-position: center;", css_content)

    def test_05_ra038_runner_all_generations_ui_and_images(self) -> None:
        """RA-038 & RA-039. Confirms /vehicles/toyota/4runner/ renders all 6 generations with distinct image paths."""
        mfr, _ = Manufacturer.objects.get_or_create(name="Toyota", defaults={"is_active": True})
        model, _ = VehicleModel.objects.get_or_create(manufacturer=mfr, name="4Runner", defaults={"is_active": True})
        gen_data = [
            ("First Generation", 1984, 1989),
            ("Second Generation", 1990, 1995),
            ("Third Generation", 1996, 2002),
            ("Fourth Generation", 2003, 2009),
            ("Fifth Generation", 2010, 2024),
            ("Sixth Generation", 2025, None),
        ]
        for name, start, end in gen_data:
            g, _ = Generation.objects.get_or_create(vehicle_model=model, start_year=start, defaults={"name": name, "end_year": end, "is_active": True})
            VehicleDefinition.objects.get_or_create(generation=g, model_year=start, trim_name="SR5", engine_name="2.4L I4", drivetrain="4WD", market="US", defaults={"is_active": True})

        resp = self.client.get(model.get_absolute_url())
        self.assertEqual(resp.status_code, 200)

        # Confirm all 6 generations are present in page output
        self.assertContains(resp, "First Generation")
        self.assertContains(resp, "Second Generation")
        self.assertContains(resp, "Third Generation")
        self.assertContains(resp, "Fourth Generation")
        self.assertContains(resp, "Fifth Generation")
        self.assertContains(resp, "Sixth Generation")

        # Confirm distinct generation image URLs for all 6 generations
        for gen_slug in ["first-generation", "second-generation", "third-generation", "fourth-generation", "fifth-generation", "sixth-generation"]:
            self.assertContains(resp, f"/static/images/generations/toyota-4runner-{gen_slug}.jpg")

    def test_06_ra041_compact_multi_column_card_contracts(self) -> None:
        """RA-041. Confirms multi-column grid containers and compact cards are present in CSS and template markup."""
        import os
        from django.conf import settings
        css_path = os.path.join(settings.BASE_DIR, "static", "css", "site.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # CSS multi-column grid & mobile image responsiveness verification
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", css_content)
        self.assertIn(".generation-card-grid, .archive-nav-grid", css_content)
        self.assertIn(".generation-nav-card, .archive-nav-card", css_content)
        self.assertIn("aspect-ratio: 16 / 9;", css_content)
        self.assertIn("object-fit: cover;", css_content)

        # Create active test generation & vehicle definition for mfr detail rendering
        toyota, _ = Manufacturer.objects.get_or_create(name="Toyota", defaults={"is_active": True})
        model, _ = VehicleModel.objects.get_or_create(manufacturer=toyota, name="4RunnerTestModel", defaults={"is_active": True})
        gen = Generation.objects.create(vehicle_model=model, name="First Generation", slug="gen1-test-card", start_year=1984, end_year=1989, is_active=True)
        VehicleDefinition.objects.create(generation=gen, model_year=1984, trim_name="SR5", engine_name="2.4L I4", drivetrain="4WD", market="US", is_active=True)

        resp_mfr = self.client.get(toyota.get_absolute_url())
        self.assertEqual(resp_mfr.status_code, 200)
        self.assertContains(resp_mfr, "generation-card-grid")
        self.assertContains(resp_mfr, "generation-nav-card")

        resp_model = self.client.get(model.get_absolute_url())
        self.assertEqual(resp_model.status_code, 200)
        self.assertContains(resp_model, "archive-nav-grid")
        self.assertContains(resp_model, "archive-nav-card")