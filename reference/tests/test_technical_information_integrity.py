from decimal import Decimal
from html.parser import HTMLParser

from django.test import TestCase
from django.urls import reverse

from measurements.models import (
    ApplicabilityFeature, ApplicabilityState, MeasurementDefinition,
    MeasurementResult, MeasurementResultCondition,
)
from reference.models import Generation, ImportExecutionReceipt, Manufacturer, VehicleDefinition, VehicleModel


class DiagramTextParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.depth = 0
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "svg":
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "svg":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text.append(data)


class TechnicalInformationIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Toyota")
        model = VehicleModel.objects.create(manufacturer=manufacturer, name="4Runner")
        cls.generation = Generation.objects.create(
            vehicle_model=model, name="Fourth Generation", start_year=2003, end_year=2009,
        )
        cls.other_generation = Generation.objects.create(
            vehicle_model=model, name="Fifth Generation", start_year=2010, end_year=2024,
        )
        cls.configuration = VehicleDefinition.objects.create(
            generation=cls.generation, model_year=2003, trim_name="SR5",
            engine_name="4.0L V6", drivetrain="4WD", market="US",
        )
        cls.definition = MeasurementDefinition.objects.create(
            name="Cargo Opening Height", description="Height of the rear cargo opening.",
        )
        sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        floor = ApplicabilityFeature.objects.create(name="Cargo Floor Position")
        cls.sunroof_present = ApplicabilityState.objects.create(feature=sunroof, name="Present")
        cls.upper_floor = ApplicabilityState.objects.create(feature=floor, name="Upper")
        cls.measurements_url = reverse("measurements:generation-measurements", kwargs={
            "manufacturer_slug": manufacturer.slug, "vehicle_model_slug": model.slug,
            "generation_slug": cls.generation.slug,
        })

    def result(self, **kwargs):
        return MeasurementResult.objects.create(**{
            "generation": self.generation, "definition": self.definition,
            "value": Decimal("37.25"), "unit": "in", **kwargs,
        })

    def conditional_result(self, **kwargs):
        result = self.result(**kwargs)
        for state in [self.sunroof_present, self.upper_floor]:
            MeasurementResultCondition.objects.create(result=result, state=state)
        return result

    def page_urls(self):
        return [self.generation.get_absolute_url(), self.configuration.get_absolute_url(), self.measurements_url]

    def test_generic_diagrams_have_no_unsupported_dimension_labels(self):
        for generation in [self.generation, self.other_generation]:
            with self.subTest(generation=generation):
                response = self.client.get(generation.get_absolute_url())
                for value in ["109.8", "189.6", "72.2", "66.0", "42.5", "46.0", "30.5"]:
                    self.assertNotContains(response, value + "″")
                self.assertNotContains(response, "(BETWEEN WHEEL WELLS)")
                # SVG path/viewBox coordinates are drawing instructions, not labels.
                text = " ".join(DiagramTextParser(response.content.decode()).text)
                self.assertFalse(any(character.isdigit() for character in text))
                self.assertContains(response, "Illustrative · not to scale.")
                self.assertNotContains(response, "Illustrative measurement locations only")
                self.assertContains(response, 'aria-label="Generic measurement-location illustration, not to scale"', count=3)

    def test_real_values_remain_separate_from_illustrative_drawings(self):
        result = self.result(value=Decimal("951.50"), unit="mm")
        response = self.client.get(self.generation.get_absolute_url())
        html = response.content.decode()
        self.assertContains(response, "951.50 mm")
        self.assertNotContains(response, str(result.uuid))
        diagram_area = html.split('<div class="dimensions-schematic-grid">', 1)[1].split('class="recorded-measurements-container"', 1)[0]
        self.assertNotIn("951.50", diagram_area)
        self.assertNotContains(response, "Verified Measurements")

    def test_empty_states_do_not_imply_verification_or_ongoing_collection(self):
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "No verified")
                self.assertNotContains(response, "Under Field Compilation")
                self.assertNotContains(response, "currently being recorded")
        self.assertContains(self.client.get(self.generation.get_absolute_url()), "No physical measurements are recorded for this generation.")
        self.assertContains(self.client.get(self.configuration.get_absolute_url()), "No Physical Measurements Recorded")

    def test_generation_wide_record_is_not_automatically_verified(self):
        self.result(notes="Reported value; no review status recorded.")
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Generation-wide")
                self.assertContains(response, "Reported value; no review status recorded.")
                self.assertNotContains(response, "Each row is a separate reported result")
                self.assertNotContains(response, "Each card is an independent reported result")
                self.assertNotContains(response, "Verified Measurements")
                self.assertNotContains(response, "verified physical dimensions")

    def test_conditional_results_expose_all_conditions_with_and_semantics(self):
        result = self.conditional_result()
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Sunroof: Present")
                self.assertContains(response, "Cargo Floor Position: Upper")
                self.assertContains(response, ">AND</span>")
                self.assertContains(response, "All listed conditions must be satisfied.")
                self.assertContains(response, "Applicability to a specific factory configuration has not been established.")
                self.assertNotContains(response, str(result.uuid))
        response = self.client.get(self.configuration.get_absolute_url())
        self.assertEqual(response.context["applicable_measurements"], [])
        self.assertEqual(response.context["conditional_measurements"], [result])
        self.assertContains(response, "No generation-wide results are recorded")
        self.assertNotContains(response, "No Physical Measurements Recorded")

    def test_year_trim_and_exact_selection_do_not_establish_feature_states(self):
        self.conditional_result()
        for params in [{}, {"year": 2003}, {"year": 2003, "trim": "SR5"}, {"configuration": self.configuration.slug}]:
            with self.subTest(params=params):
                response = self.client.get(self.generation.get_absolute_url(), params)
                self.assertContains(response, "Applicability to a specific factory configuration has not been established.")
                self.assertContains(response, "Sunroof: Present")
                self.assertContains(response, "37.25 in")
                if "configuration" in params:
                    self.assertEqual(response.context["selected_config"], self.configuration)
                    self.assertContains(response, 'aria-current="true"')
                    self.assertContains(response, self.configuration.get_absolute_url())

    def test_independent_duplicate_results_units_and_notes_are_not_collapsed(self):
        first = self.result(notes="First report")
        second = self.result(notes="Second report")
        third = self.result(value=Decimal("946.00"), unit="mm", notes="Third report")
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                for result in [first, second, third]:
                    self.assertNotContains(response, str(result.uuid))
                    self.assertContains(response, result.notes)
                self.assertContains(response, 'measurement-result"', count=3)
                self.assertContains(response, "37.25", count=2)
                self.assertContains(response, "946.00")
                self.assertContains(response, "mm")
        self.assertEqual(MeasurementResult.objects.filter(definition=self.definition).count(), 3)
        for result in [first, second, third]:
            original_uuid = result.uuid
            result.refresh_from_db()
            self.assertEqual(result.uuid, original_uuid)

    def test_inactive_and_other_generation_results_are_not_presented(self):
        hidden = self.result(is_active=False, notes="Inactive result")
        other = self.result(generation=self.other_generation, notes="Other generation result")
        for url in self.page_urls():
            response = self.client.get(url)
            self.assertNotContains(response, str(hidden.uuid))
            self.assertNotContains(response, str(other.uuid))
            self.assertNotContains(response, "Inactive result")
            self.assertNotContains(response, "Other generation result")

    def test_receipt_preserves_attribution_and_outcome_without_verification_claim(self):
        receipt = ImportExecutionReceipt.objects.create(
            existing_vehicle_definition=self.configuration,
            source_id="recorded-source-id", native_identifier="source-record-123",
            manifest_hash="sha256:" + "a" * 64, raw_artifact_hash="sha256:" + "b" * 64,
            adjudication_hash="sha256:" + "c" * 64,
            planned_action="NO_OP_EXACT_MATCH", execution_outcome="no_op_exact_match",
        )
        for outcome in ["no_op_exact_match", "failed"]:
            receipt.execution_outcome = outcome
            receipt.save()
            response = self.client.get(self.configuration.get_absolute_url())
            for value in [receipt.source_id, receipt.native_identifier, receipt.manifest_hash,
                          receipt.raw_artifact_hash, receipt.adjudication_hash, outcome]:
                self.assertContains(response, value)
            self.assertContains(response, "Import execution receipt")
            self.assertContains(response, "do not establish independent verification of every specification")
            self.assertNotContains(response, "Audited &amp; Verified")
            self.assertNotContains(response, "Durable verification receipt")
            self.assertNotContains(response, "Source Authority")

    def test_absent_receipt_does_not_fabricate_provenance(self):
        response = self.client.get(self.configuration.get_absolute_url())
        self.assertIsNone(response.context["receipt"])
        self.assertContains(response, "No associated import execution receipt is available")
        self.assertNotContains(response, "Audited &amp; Verified")

    def test_recorded_text_remains_escaped_and_layout_order_is_preserved(self):
        result = self.conditional_result(notes='<script>alert("untrusted note")</script>')
        response = self.client.get(self.generation.get_absolute_url())
        html = response.content.decode()
        for before, after in [('class="generation-hero-container"', 'id="configurations"'),
                              ('id="configurations"', 'id="dimensions"'), ('id="dimensions"', 'id="builds"')]:
            self.assertLess(html.index(before), html.index(after))
        for url in self.page_urls():
            response = self.client.get(url)
            self.assertContains(response, "&lt;script&gt;")
            self.assertNotContains(response, result.notes)


    def test_additional_measurements_are_compact_and_preserve_publication_notes(self):
        first = self.result(notes="Toyota mechanical publication: source note A.")
        second = self.result(value=Decimal("38.50"), notes="Toyota mechanical publication: source note B.")
        before = list(MeasurementResult.objects.order_by("pk").values("uuid", "value", "unit", "notes"))
        for url in self.page_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, first.notes)
                self.assertContains(response, second.notes)
                self.assertContains(response, "37.25")
                self.assertContains(response, "38.50")
                self.assertContains(response, "in")
                self.assertContains(response, 'measurement-result"', count=2)
                for result in [first, second]:
                    self.assertNotContains(response, str(result.uuid))
                self.assertNotContains(response, "Each row is a separate reported result")
                self.assertNotContains(response, "Each card is an independent reported result")
                self.assertNotContains(response, "Verified Measurements")
                self.assertNotContains(response, "Manufacturer verified")
        response = self.client.get(self.generation.get_absolute_url())
        self.assertContains(response, ">Additional Measurements</h3>")
        self.assertNotContains(response, "Recorded Measurements from Archive")
        self.assertNotContains(response, "Illustrative measurement locations only")
        self.assertEqual(list(MeasurementResult.objects.order_by("pk").values("uuid", "value", "unit", "notes")), before)
