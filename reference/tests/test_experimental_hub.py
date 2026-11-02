from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit
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


class ConfiguratorParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms, self.links, self.options, self.ids = [], [], [], set()
        self.link = self.option = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "form":
            self.forms.append(attrs)
        elif tag == "a":
            self.link = {"attrs": attrs, "text": ""}
            self.links.append(self.link)
        elif tag == "option":
            self.option = {"attrs": attrs, "text": ""}
            self.options.append(self.option)

    def handle_data(self, data):
        if self.link is not None:
            self.link["text"] += data
        if self.option is not None:
            self.option["text"] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self.link = None
        elif tag == "option":
            self.option = None


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
        self.assertEqual(response.context["generation"].notes, self.fourth_generation.notes)
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
        self.assertContains(response, 'data-year="2003"')
        self.assertIn(self.vd_2003_v6, response.context["displayed_configurations"])
        self.assertIn(self.vd_2003_v8, response.context["displayed_configurations"])
        self.assertNotIn(self.vd_2004_sr5, response.context["displayed_configurations"])
        # Generation-wide measurements remain preserved
        self.assertContains(response, "Maximum Cargo Interior Height")

    # 3. Valid exact-configuration filtering
    def test_valid_exact_configuration_filtering_marks_choice_and_preserves_specs_link(self) -> None:
        """Exact selection is marked and retains its canonical specification link."""
        response = self.client.get(
            self.fourth_generation.get_absolute_url() + f"?year=2003&configuration={self.vd_2003_v8.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertEqual(response.context["selected_config"], self.vd_2003_v8)
        self.assertTrue(response.context["filter_active"])
        self.assertContains(response, 'aria-current="true"')
        self.assertContains(response, self.vd_2003_v8.engine_name)
        self.assertContains(response, 'class="configuration-specs-link"')
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
    def test_forthcoming_sections_present_explicit_empty_states(self) -> None:
        """Adventure Builds and Service Maintenance are clearly framed as forthcoming without fake data."""
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertContains(response, "No Builds documented yet")
        self.assertContains(response, "No service guides added yet.")
        self.assertNotContains(response, "Click to add a build or mod")
        self.assertNotContains(response, "Click to add a service guide")

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
        """Homepage exposes populated platforms and available discovery forms."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vehicle Platforms")
        self.assertContains(response, "Explore the Archive")
        self.assertContains(response, "Find a Vehicle")
        self.assertContains(response, self.four_runner.get_absolute_url())
        self.assertContains(response, reverse("reference:manufacturer-list"))
        self.assertEqual(response.context["featured_platforms"][0]["generations_count"], 2)

    def test_homepage_graceful_handling_without_measurements(self) -> None:
        """Homepage handles missing measurements gracefully without crashing or broken layout."""
        MeasurementResult.objects.all().delete()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Measured Reality: Beyond Brochure Claims")
        self.assertContains(response, "Vehicle Platforms")
        self.assertContains(response, self.four_runner.get_absolute_url())
        self.assertNotContains(response, "38.60")


    def test_notes_remain_stored_and_accessible_without_standalone_panel(self):
        url = self.fourth_generation.get_absolute_url()
        for notes in ['<script>alert("notes")</script>\nRecorded second line.', ""]:
            with self.subTest(notes=notes):
                self.fourth_generation.notes = notes
                self.fourth_generation.save()
                response = self.client.get(url)
                self.fourth_generation.refresh_from_db()
                self.assertEqual(self.fourth_generation.notes, notes)
                self.assertEqual(response.context["generation"].notes, notes)
                self.assertNotContains(response, 'id="generation-notes-heading"')
                self.assertNotContains(response, "Generation Notes")
                self.assertNotContains(response, '<script>alert(')
                self.assertNotContains(response, "Recorded second line.")

    def test_initial_and_year_selected_choices_work_without_javascript(self):
        url = self.fourth_generation.get_absolute_url()
        response = self.client.get(url)
        page = ConfiguratorParser(response.content.decode())
        self.assertNotContains(response, 'class="configuration-choice"')
        self.assertContains(response, "Select a model year to view configurations.")
        year_link = next(link for link in page.links if link["attrs"].get("data-year") == "2003")
        response = self.client.get(url, parse_qs(urlsplit(year_link["attrs"]["href"]).query))
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertEqual(set(response.context["configuration_browser_choices"]), {self.vd_2003_v6, self.vd_2003_v8})
        self.assertIsNone(response.context["full_specs_url"])
        self.assertIsNone(response.context["selected_config"])


    def test_configuration_only_url_populates_inferred_year_choices(self):
        response = self.client.get(self.fourth_generation.get_absolute_url(),
                                   {"configuration": self.vd_2007_sr5.slug})
        self.assertEqual(response.context["available_trims"], ["SR5"])
        page = ConfiguratorParser(response.content.decode())
        year = next(link for link in page.links if link["attrs"].get("data-year") == "2007")
        self.assertIn("is-selected", year["attrs"]["class"])
        current = next(link for link in page.links if link["attrs"].get("aria-current") == "true")
        self.assertIn(self.vd_2007_sr5.slug, current["attrs"]["href"])
        self.assertEqual(list(response.context["displayed_configurations"]), [self.vd_2007_sr5])
        self.assertEqual(response.context["full_specs_url"], self.vd_2007_sr5.get_absolute_url())
        self.assertContains(response, self.vd_2007_sr5.get_absolute_url())


    def test_explicit_invalid_or_blank_year_is_never_replaced_by_configuration_year(self):
        for year in ["invalid", "1990", "", "999999999999999999999999999"]:
            with self.subTest(year=year):
                response = self.client.get(self.fourth_generation.get_absolute_url(),
                                           {"year": year, "configuration": self.vd_2007_sr5.slug})
                self.assertIsNone(response.context["selected_year"])
                self.assertIsNone(response.context["selected_config"])
                self.assertTrue(response.context["filter_errors"])
                self.assertIsNone(response.context["full_specs_url"])

    def test_unnamed_trim_remains_accessible_and_is_not_all_trims(self):
        unnamed = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="", engine_name="4.0L V6", drivetrain="4WD", market="US")
        url = self.fourth_generation.get_absolute_url()
        response = self.client.get(url, {"year": 2003, "trim": ""})
        self.assertEqual(response.context["selected_trim"], "")
        self.assertTrue(response.context["trim_filter_active"])
        self.assertEqual(list(response.context["displayed_configurations"]), [unnamed])
        self.assertContains(response, "Unnamed trim")
        self.assertContains(response, unnamed.get_absolute_url())
        self.assertContains(response, '?year=2003&amp;trim=#configurations')
        self.assertIsNone(response.context["selected_config"])
        response = self.client.get(url, {"configuration": unnamed.slug})
        self.assertEqual(response.context["selected_config"], unnamed)
        self.assertIn("", response.context["available_trims"])

    def test_trim_never_silently_selects_one_of_multiple_configurations(self):
        other = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="SR5", engine_name="4.0L V6", drivetrain="4WD", market="US")
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"year": 2003, "trim": "SR5"})
        self.assertEqual(set(response.context["displayed_configurations"]), {self.vd_2003_v6, other})
        self.assertIsNone(response.context["selected_config"])
        self.assertIsNone(response.context["full_specs_url"])
        self.assertContains(response, other.get_absolute_url())
        self.assertContains(response, self.vd_2003_v6.get_absolute_url())

    def test_mismatched_trim_and_unknown_or_inactive_configuration_are_rejected(self):
        url = self.fourth_generation.get_absolute_url()
        cases = [{"year": 2003, "trim": "SR5", "configuration": self.vd_2003_v8.slug},
                 {"year": 2003, "trim": "not-a-trim", "configuration": self.vd_2003_v8.slug},
                 {"year": 2003, "configuration": "not-a-config"},
                 {"year": 2003, "configuration": self.vd_fifth_gen.slug}]
        for params in cases:
            with self.subTest(params=params):
                response = self.client.get(url, params)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.context["selected_config"])
                self.assertTrue(response.context["filter_errors"])
                self.assertIsNone(response.context["full_specs_url"])

    def test_inactive_configuration_is_rejected(self):
        self.vd_2003_v8.is_active = False
        self.vd_2003_v8.save()
        response = self.client.get(self.fourth_generation.get_absolute_url(),
                                   {"year": 2003, "configuration": self.vd_2003_v8.slug})
        self.assertIsNone(response.context["selected_config"])
        self.assertTrue(response.context["filter_errors"])
        self.assertNotContains(response, self.vd_2003_v8.get_absolute_url())

    def test_years_and_configuration_options_have_deterministic_order(self):
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertEqual(response.context["active_model_years"], [2007, 2004, 2003])
        page = ConfiguratorParser(response.content.decode())
        self.assertEqual([link["attrs"]["data-year"] for link in page.links if "data-year" in link["attrs"]], ["2007", "2004", "2003"])
        context = get_generation_hub_context(self.fourth_generation, model_year="2003")
        self.assertEqual(list(context["configuration_choices"]), [self.vd_2003_v8, self.vd_2003_v6])

    def test_empty_generation_and_filter_reset(self):
        self.fourth_generation.vehicle_definitions.all().update(is_active=False)
        response = self.client.get(self.fourth_generation.get_absolute_url())
        self.assertContains(response, "No active configurations are available")
        self.assertEqual(list(response.context["configuration_choices"]), [])
        self.assertNotContains(response, 'class="configuration-choice"')
        response = self.client.get(self.fifth_generation.get_absolute_url(), {"configuration": self.vd_fifth_gen.slug})
        self.assertContains(response, "Clear Filters")
        reset = self.client.get(self.fifth_generation.get_absolute_url())
        self.assertIsNone(reset.context["selected_config"])
        self.assertIsNone(reset.context["selected_year"])
        self.assertFalse(reset.context["filter_active"])


    def test_single_year_or_trim_match_is_not_an_exact_selection(self):
        for params in [{"year": 2007}, {"year": 2007, "trim": "SR5"}]:
            with self.subTest(params=params):
                response = self.client.get(self.fourth_generation.get_absolute_url(), params)
                self.assertEqual(list(response.context["displayed_configurations"]), [self.vd_2007_sr5])
                self.assertIsNone(response.context["selected_config"])
                self.assertIsNone(response.context["full_specs_url"])
                self.assertNotContains(response, 'id="selected-configuration"')


    def test_configurator_get_links_and_reset_keep_stable_fragment(self):
        url = self.fourth_generation.get_absolute_url()
        page = ConfiguratorParser(self.client.get(url, {"year": 2003}).content.decode())
        self.assertNotIn("explore", page.ids)
        exact = next(link for link in page.links if link["attrs"].get("class") == "configuration-choice")
        target = urlsplit(exact["attrs"]["href"])
        self.assertEqual(target.fragment, "configurations")
        response = self.client.get(url, parse_qs(target.query, keep_blank_values=True))
        self.assertIsNotNone(response.context["selected_config"])
        reset = next(link for link in page.links if "clear-filters-link" in link["attrs"].get("class", "").split())
        self.assertEqual(reset["attrs"]["href"], url + "#configurations")
        cleared = self.client.get(urlsplit(reset["attrs"]["href"]).path)
        self.assertFalse(cleared.context["filter_active"])


    def test_compact_choices_keep_native_selection_and_canonical_specification_links(self):
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"year": 2003})
        page = ConfiguratorParser(response.content.decode())
        choices = [link for link in page.links if link["attrs"].get("class") == "configuration-choice"]
        self.assertEqual(len(choices), 2)
        self.assertEqual({urlsplit(c["attrs"]["href"]).fragment for c in choices}, {"configurations"})
        for configuration in [self.vd_2003_v6, self.vd_2003_v8]:
            self.assertTrue(any(configuration.slug in c["attrs"]["href"] for c in choices))
            specs = next(link for link in page.links if link["attrs"]["href"] == configuration.get_absolute_url())
            self.assertIn("Full specifications for", specs["attrs"]["aria-label"])
        self.assertContains(response, "Factory Configurations:")
        self.assertNotContains(response, "Matching Factory Configurations:")
        for option in page.options:
            self.assertNotIn("United States", option["text"])
            self.assertNotIn("US Market", option["text"])
        for choice in choices:
            self.assertNotIn("United States", choice["text"])
            self.assertNotIn("US Market", choice["text"])
        # This CSS contract protects wrapping chips from reverting to tall cards.
        from django.conf import settings
        css = (settings.BASE_DIR / "static/css/site.css").read_text()
        block = css.split(".matching-configs-list {", 1)[1].split("}", 1)[0]
        self.assertIn("flex-wrap: wrap", block)
        self.assertNotIn("max-height", block)
        self.assertIn("scroll-margin-top", css.split("#configurations {", 1)[1].split("}", 1)[0])

    def test_selected_compact_choice_keeps_siblings_and_current_marker(self):
        sibling = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="SR5", engine_name="4.0L V6", drivetrain="4WD", market="US")
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"configuration": sibling.slug})
        page = ConfiguratorParser(response.content.decode())
        choices = [link for link in page.links if link["attrs"].get("class") == "configuration-choice"]
        self.assertEqual(len(choices), 2)
        current = [c for c in choices if c["attrs"].get("aria-current") == "true"]
        self.assertEqual(len(current), 1)
        self.assertIn(sibling.slug, current[0]["attrs"]["href"])
        self.assertContains(response, self.vd_2003_v6.get_absolute_url())
        self.assertContains(response, sibling.get_absolute_url())
        # Only drivetrain varies within this trim; repeated engine/trim are omitted.
        self.assertEqual({c["text"] for c in choices}, {"2WD", "4WD"})
        self.assertEqual(response.context["selected_config"].market, "US")
        self.assertContains(self.client.get(sibling.get_absolute_url()), "United States")

    def test_market_is_only_added_when_needed_to_distinguish_choices(self):
        canadian = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="SR5", engine_name="4.0L V6", drivetrain="2WD", market="CA")
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"year": 2003, "trim": "SR5"})
        choices = response.context["configuration_browser_choices"]
        self.assertEqual({c.pk for c in choices}, {canadian.pk, self.vd_2003_v6.pk})
        self.assertEqual(len({c.choice_label for c in choices}), 2)
        self.assertTrue(any("Canada (CA)" in c.choice_label for c in choices))
        self.assertTrue(any("United States (US)" in c.choice_label for c in choices))

    def test_identical_attributes_use_real_canonical_identifiers(self):
        duplicate = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="SR5", engine_name="4.0L V6", drivetrain="2WD", market="US",
                    slug="alternate-canonical-record")
        context = get_generation_hub_context(self.fourth_generation, model_year="2003", trim_name="SR5")
        choices = context["configuration_browser_choices"]
        self.assertEqual(len(choices), 2)
        self.assertEqual(len({c.choice_label for c in choices}), 2)
        for choice in choices:
            self.assertIn(choice.slug, choice.choice_label)
        self.assertEqual({c.pk for c in choices}, {self.vd_2003_v6.pk, duplicate.pk})


    def test_native_trim_links_preserve_named_and_unnamed_selection(self):
        unnamed = VehicleDefinition.objects.create(generation=self.fourth_generation,
                    model_year=2003, trim_name="", engine_name="4.0L V6", drivetrain="4WD", market="US")
        url = self.fourth_generation.get_absolute_url()
        year_page = ConfiguratorParser(self.client.get(url, {"year": 2003}).content.decode())
        trim_links = [link for link in year_page.links if "trim-button" in link["attrs"].get("class", "").split()]
        for trim, configuration in [("SR5", self.vd_2003_v6), ("", unnamed)]:
            with self.subTest(trim=trim):
                link = next(link for link in trim_links if parse_qs(urlsplit(link["attrs"]["href"]).query, keep_blank_values=True).get("trim") == [trim])
                params = parse_qs(urlsplit(link["attrs"]["href"]).query, keep_blank_values=True)
                response = self.client.get(url, params)
                self.assertEqual(response.context["selected_trim"], trim)
                self.assertEqual(list(response.context["displayed_configurations"]), [configuration])
                page = ConfiguratorParser(response.content.decode())
                exact = next(link for link in page.links if link["attrs"].get("class") == "configuration-choice")
                selected = self.client.get(url, parse_qs(urlsplit(exact["attrs"]["href"]).query))
                self.assertEqual(selected.context["selected_config"], configuration)
                self.assertEqual(selected.context["selected_trim"], trim)


    def test_single_configurator_order_heading_and_removed_upper_panel(self):
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"configuration": self.vd_2003_v8.slug})
        html = response.content.decode()
        self.assertContains(response, 'id="configurations"', count=1)
        self.assertLess(html.index('class="generation-hero-container"'), html.index('id="configurations"'))
        self.assertLess(html.index('id="configurations"'), html.index('id="dimensions"'))
        self.assertContains(response, '<h2 class="section-title-serif">Configurations &amp; Specs</h2>', html=True)
        self.assertContains(response, "Explore available factory configurations by model year and trim. Select a configuration to view its detailed technical specifications.")
        for text in ["1. Model Year", "2. Trim", "3. Configuration"]:
            self.assertContains(response, text)
        for text in ['id="explore"', 'id="exploreFilterForm"', 'id="selected-configuration"', "Explore This Generation", "Apply Filters", "Explore Configurations", "View Full Specifications"]:
            self.assertNotContains(response, text)
        self.assertContains(response, self.vd_2003_v8.get_absolute_url())

    def test_builds_and_guides_have_matching_heading_structure_without_subtitle(self):
        response = self.client.get(self.fourth_generation.get_absolute_url())
        html = response.content.decode()
        for title in ["Builds and Mods", "Service Guides"]:
            self.assertIn(f'<div class="section-heading-row">\n                <h2 class="section-title-serif">{title}</h2>', html)
        self.assertNotContains(response, "Maintenance and repair information for the")
        self.assertContains(response, "No service guides added yet.")
        self.assertContains(response, "No Builds documented yet")

    def test_builds_and_guides_decorative_placeholders_for_two_generations(self):
        from django.contrib.staticfiles import finders
        from django.templatetags.static import static

        for generation in (self.fourth_generation, self.fifth_generation):
            with self.subTest(generation=generation.name):
                response = self.client.get(generation.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                for message in ("No Builds documented yet", "No service guides added yet."):
                    # The entire caption contains only the requested message:
                    # no generation identity, extra explanation or contribution CTA.
                    self.assertContains(
                        response,
                        '<div class="generation-domain-placeholder-body">'
                        f'<p class="generation-domain-placeholder-message">{message}</p></div>',
                        html=True, count=1,
                    )
                self.assertContains(response, 'class="empty-domain-card generation-domain-placeholder"', count=2)
                for asset, width, height in (
                    ("images/generation-builds-placeholder-baja.png", 1916, 821),
                    ("images/generation-service-guides-placeholder.png", 220, 150),
                ):
                    self.assertIsNotNone(finders.find(asset))
                    # Empty alt text keeps the generic photo out of the record's
                    # accessible description; no generation evidence is implied.
                    self.assertContains(
                        response,
                        f'<img class="generation-domain-placeholder-image" src="{static(asset)}" '
                        f'alt="" loading="lazy" width="{width}" height="{height}">',
                        html=True, count=1,
                    )
                for removed_text in (
                    "Future entries will document", "Future entries will cover",
                    "No builds are currently recorded for", "No service guides are currently available for",
                    "Click to add a build or mod", "Click to add a service guide",
                ):
                    self.assertNotContains(response, removed_text)
                page = ConfiguratorParser(response.content.decode())
                section_links = [
                    link for link in page.links
                    if link["attrs"].get("href") in ("#builds", "#service-guides")
                    and "section-action-link" in link["attrs"].get("class", "").split()
                ]
                self.assertEqual(len(section_links), 2)
                self.assertTrue(all(link["attrs"].get("aria-disabled") == "true" for link in section_links))


    def test_only_filter_links_opt_into_enhancement(self):
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"year": 2003})
        page = ConfiguratorParser(response.content.decode())
        for link in page.links:
            classes = link["attrs"].get("class", "").split()
            is_filter = bool(set(classes) & {"year-button", "trim-button", "configuration-choice", "clear-filters-link"})
            self.assertEqual("data-generation-filter" in link["attrs"], is_filter)
        self.assertContains(response, '/static/js/generation_configurator.js')
        self.assertNotContains(response, 'onchange=')


    def test_update_announcer_is_hidden_inside_configurator_outside_replaced_content(self):
        response = self.client.get(self.fourth_generation.get_absolute_url(), {"year": 2003})
        html = response.content.decode()
        self.assertContains(response, '<p id="generation-filter-status" class="visually-hidden" role="status" aria-live="polite" aria-atomic="true"></p>', html=True)
        self.assertContains(response, 'id="generation-filter-status"', count=1)
        self.assertLess(html.index('id="configurations"'), html.index('id="generation-filter-status"'))
        self.assertLess(html.index('id="generation-filter-status"'), html.index('id="configuration-content"'))
        self.assertLess(html.index('id="generation-filter-status"'), html.index('id="dimensions"'))
        self.assertNotContains(response, "Configurations updated.")
        self.assertNotContains(response, "Updating configurations")
        self.assertEqual(response.context["selected_year"], 2003)
        self.assertContains(response, self.vd_2003_v6.get_absolute_url())
        from django.conf import settings
        css = (settings.BASE_DIR / "static/css/site.css").read_text()
        rule = css.split(".visually-hidden {", 1)[1].split("}", 1)[0]
        self.assertIn("clip-path: inset(50%)", rule)
        self.assertNotIn("display: none", rule)
        self.assertNotIn("visibility: hidden", rule)
