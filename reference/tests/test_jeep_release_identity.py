"""Bounded identity extraction and equipment-policy tests, without persistence."""
import copy
from pathlib import Path
from unittest import SkipTest
from django.conf import settings
from django.test import SimpleTestCase
from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.jeep_release import (
    SOURCE_ID, SOURCE_URL, _parse, extract_release_identity,
)
from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata, compute_content_hash
from reference.ingestion.contracts import SourceApplicability


class JeepReleaseIdentityTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = settings.BASE_DIR / "storage/acquisition_inputs/jeep_2018/2017_mopar_2018_wrangler_release.html"
        if not path.exists():
            raise SkipTest("Original local manufacturer release not installed.")
        cls.raw = path.read_bytes()
        assert compute_content_hash(cls.raw) == "sha256:1378745a03e10f2a60e8080ee09f06b24116b078667057f513a6deecd1f3a4b7"
        cls.meta = RawSourceSnapshotMetadata(SOURCE_ID, SOURCE_URL, "2026-11-04T00:00:00+00:00",
            "text/html", compute_content_hash(cls.raw), "synthetic-test-storage.html",
            SourceApplicability(market=None), "local_file")

    def test_original_statement_preserves_customization_qualifier(self):
        sas = extract_release_identity(self.raw, self.meta)
        statement = next(a for a in sas.source_assertions if a.attribute_key == "vehicle_body_grade_statement")
        self.assertIn("two-door 2018 Jeep Wrangler Sport uniquely customized", statement.raw_value)
        self.assertIn("FCA US display", statement.raw_value)
        self.assertIn("p[", statement.source_context)

    def test_no_accessories_mechanics_or_commercial_market_assertions(self):
        sas = extract_release_identity(self.raw, self.meta)
        self.assertEqual({a.attribute_key for a in sas.source_assertions},
                         {"generation_section", "vehicle_body_grade_statement", "publication_date"})
        self.assertIsNone(sas.provenance.source_applicability.market)

    def test_no_literal_jl_code_invented(self):
        sas = extract_release_identity(self.raw, self.meta)
        section = next(a for a in sas.source_assertions if a.attribute_key == "generation_section")
        self.assertIn("All-new 2018", section.raw_value)
        self.assertNotEqual(section.raw_value, "JL")

    def test_raw_hash_tampering_rejected(self):
        with self.assertRaises(AcquisitionError):
            extract_release_identity(self.raw + b"changed", self.meta)

    def test_wrong_publisher_locator_rejected(self):
        meta = copy.deepcopy(self.meta)
        meta.publisher_locator = "https://example.invalid/release"
        with self.assertRaises(AcquisitionError):
            extract_release_identity(self.raw, meta)

    def test_missing_body_statement_rejected(self):
        with self.assertRaises(AcquisitionError):
            _parse(self.raw.replace(b"two-door 2018 Jeep Wrangler Sport", b"unspecified vehicle"))

    def test_script_text_is_not_identity_evidence(self):
        _, (_, paragraph) = _parse(self.raw)
        missing = self.raw.replace(b"two-door 2018 Jeep Wrangler Sport", b"unspecified vehicle")
        forged = b"<script><p>" + paragraph.encode("utf-8") + b"</p></script>"
        with self.assertRaises(AcquisitionError):
            _parse(missing.replace(b"</body>", forged + b"</body>"))
