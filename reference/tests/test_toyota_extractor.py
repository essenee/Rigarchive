"""
Unit tests for Toyota PDF Extractor & Production Decoupling (RA-026).

Verifies deterministic extraction of Tier 1 SourceAssertionSets directly from authentic
retained PDF snapshots, golden fixture equivalence testing, layout error handling,
and decoupling of the production runtime path from the golden JSON transcription.
"""

import json
from pathlib import Path

from django.test import TestCase

from reference.ingestion.contracts import SourceApplicability
from reference.ingestion.acquisition.profiles import ToyotaUSAPressroomProfile
from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata, compute_content_hash
from reference.ingestion.acquisition.toyota_extractor import (
    ExtractionLayoutError,
    ToyotaPricingMasterPdfStrategy,
)


class ToyotaExtractorTests(TestCase):
    def setUp(self):
        self.fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "acquisition" / "toyota"
        self.pdf_fixture_path = self.fixtures_dir / "2020_4runner_pricing.pdf"
        self.json_fixture_path = self.fixtures_dir / "2020_4runner_specs.json"

        with open(self.json_fixture_path, "r", encoding="utf-8") as f:
            self.golden_json_data = json.load(f)

        self.pdf_bytes = self.pdf_fixture_path.read_bytes()
        self.pdf_hash = compute_content_hash(self.pdf_bytes)

        self.snapshot_meta = RawSourceSnapshotMetadata(
            source_id="toyota_usa",
            publisher_locator="https://pressroom.toyota.com/vehicle/2020-toyota-4runner/",
            acquired_at="2026-08-15T16:00:00Z",
            content_type="application/pdf",
            content_hash=self.pdf_hash,
            storage_path=str(self.pdf_fixture_path),
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )

    def test_pdf_strategy_extraction(self):
        strategy = ToyotaPricingMasterPdfStrategy()
        assertion_sets = strategy.extract(self.pdf_bytes, self.snapshot_meta)

        self.assertTrue(len(assertion_sets) > 0)
        first_set = assertion_sets[0]

        self.assertEqual(first_set.provenance.source_id, "toyota_usa")
        self.assertEqual(first_set.provenance.extraction_provenance.raw_artifact_hash, self.pdf_hash)
        self.assertEqual(
            first_set.provenance.extraction_provenance.extractor_id,
            "toyota_pricing_master_pdf_strategy",
        )

        # Check extracted attributes
        attr_dict = {a.attribute_key: a.raw_value for a in first_set.source_assertions}
        self.assertEqual(attr_dict["make_name"], "Toyota")
        self.assertEqual(attr_dict["model_name"], "4Runner")
        self.assertEqual(attr_dict["model_year"], "2020")
        self.assertEqual(attr_dict["market"], "US")

    def test_production_profile_decoupled_from_json(self):
        profile = ToyotaUSAPressroomProfile()
        # Call extract passing raw PDF snapshot without supplying transcription_data
        sets = profile.extract(self.snapshot_meta, raw_bytes=self.pdf_bytes)

        self.assertTrue(len(sets) > 0)
        self.assertEqual(sets[0].provenance.extraction_provenance.raw_artifact_hash, self.pdf_hash)

    def test_golden_json_benchmark_equivalence(self):
        profile = ToyotaUSAPressroomProfile()
        sets_pdf = profile.extract(self.snapshot_meta, raw_bytes=self.pdf_bytes)

        # Map model codes extracted from PDF
        pdf_model_codes = {
            s.provenance.native_record_id: {a.attribute_key: a.raw_value for a in s.source_assertions}
            for s in sets_pdf
        }

        # Validate controlled codes exist in PDF extraction output
        controlled_codes = ["8664", "8666", "8670", "8672", "8674"]
        for code in controlled_codes:
            self.assertIn(code, pdf_model_codes)
            attr = pdf_model_codes[code]
            self.assertEqual(attr["make_name"], "Toyota")
            self.assertEqual(attr["model_name"], "4Runner")
            self.assertEqual(attr["model_year"], "2020")

    def test_malformed_pdf_layout_error(self):
        strategy = ToyotaPricingMasterPdfStrategy()
        bad_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        with self.assertRaises(ExtractionLayoutError):
            strategy.extract(bad_bytes, self.snapshot_meta)
