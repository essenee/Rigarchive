"""Offline checks for the reviewed 2018 JK Unlimited Sport transcription."""
import hashlib
import json
import io
from dataclasses import replace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from pypdf import PdfReader

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.jeep import (
    JK_UNLIMITED_SPORT_HASH, PUBLICATIONS, extract_jk_unlimited_sport,
)
from reference.ingestion.acquisition.snapshots import (
    RawSourceSnapshotMetadata, snapshot_metadata_from_dict,
)
from reference.ingestion.contracts import SourceApplicability
from reference.ingestion.serialization import deserialize_artifact, serialize_artifact
from reference.ingestion.validation import validate_source_assertion_set


def digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class UnlimitedSportProtocolTests(SimpleTestCase):
    # Synthetic bytes exercise the provenance gate, not manufacturer evidence.
    raw = b"%PDF-synthetic-reviewed-snapshot"

    def setUp(self):
        self.metadata = RawSourceSnapshotMetadata(
            source_id="jeep_usa", publisher_locator=PUBLICATIONS["jk"]["url"],
            acquired_at="2026-11-04T16:33:12.140190+00:00",
            content_type="application/pdf", content_hash=digest(self.raw),
            storage_path="storage/raw_source_artifacts/jeep_usa/synthetic.pdf",
            source_applicability=SourceApplicability(
                market="US", applicability_basis="official_jeep_en_us_publication",
                publisher_jurisdiction="FCA US LLC", applicability_scope="model_year",
            ),
            acquisition_method="local_file",
        )

    def test_deterministic_validated_assertions_and_provenance(self):
        with patch("reference.ingestion.acquisition.jeep.JK_UNLIMITED_SPORT_HASH", digest(self.raw)):
            result = extract_jk_unlimited_sport(self.raw, self.metadata)
            serialized = serialize_artifact(result)
            self.assertEqual(serialized, serialize_artifact(extract_jk_unlimited_sport(self.raw, self.metadata)))
        recovered = deserialize_artifact(serialized)
        validate_source_assertion_set(recovered)
        self.assertEqual(serialize_artifact(recovered), serialized)
        self.assertEqual(result.provenance.native_record_id, "pdf-page-10-sport-unlimited")
        self.assertEqual(result.provenance.source_locator, self.metadata.publisher_locator)
        self.assertEqual(result.provenance.retrieved_at, self.metadata.acquired_at)
        self.assertEqual(result.provenance.extraction_provenance.raw_artifact_hash, self.metadata.content_hash)
        self.assertEqual(result.provenance.extraction_provenance.raw_artifact_reference, self.metadata.storage_path)
        self.assertEqual(result.provenance.unknown_fields["publication_revision"], "74-383-3802 (9/17 143M)")
        assertions = {a.attribute_key: a for a in result.source_assertions}
        self.assertEqual(len(assertions), 9)
        self.assertEqual(assertions["manufacturer_grade"].raw_value, "SPORT")
        self.assertEqual(assertions["body_designation"].raw_value, "Wrangler Unlimited")
        self.assertEqual(assertions["body_designation"].assertion_id, "sport_unlimited_body_designation")
        self.assertIn("air conditioning standard", assertions["body_designation"].source_context)
        self.assertEqual(assertions["engine_descriptor"].raw_value, "3.6L Pentastar® V6")
        self.assertEqual(assertions["drive_descriptor"].raw_value, "Command-Trac® 4x4 system")
        self.assertEqual(assertions["generation_designation"].raw_value, "JK")
        self.assertIn("cover artwork", assertions["generation_designation"].source_context)

    def test_unreviewed_bytes_rejected_even_with_matching_snapshot_metadata(self):
        for alteration in (
            b"form 74-383-3871", b"revision 10/17", b"Sport S only",
            b"missing Unlimited qualifier", b"two-door only", b"Unlimited Sport 2WD",
        ):
            raw = self.raw + alteration
            with self.subTest(alteration=alteration), self.assertRaisesRegex(AcquisitionError, "bytes/revision"):
                extract_jk_unlimited_sport(raw, replace(self.metadata, content_hash=digest(raw)))

    def test_wrong_locator_market_or_hash_rejected(self):
        cases = (
            replace(self.metadata, publisher_locator=PUBLICATIONS["jl"]["url"]),
            replace(self.metadata, source_applicability=replace(self.metadata.source_applicability, market="CA")),
            replace(self.metadata, content_hash="sha256:" + "0" * 64),
        )
        with patch("reference.ingestion.acquisition.jeep.JK_UNLIMITED_SPORT_HASH", digest(self.raw)):
            for metadata in cases:
                with self.subTest(metadata=metadata), self.assertRaises(AcquisitionError):
                    extract_jk_unlimited_sport(self.raw, metadata)


class UnlimitedSportAuthenticSourceTests(SimpleTestCase):
    def test_retained_brochure_and_snapshot_metadata(self):
        stem = JK_UNLIMITED_SPORT_HASH.removeprefix("sha256:")
        folder = settings.BASE_DIR / "storage/raw_source_artifacts/jeep_usa"
        pdf, sidecar = folder / f"{stem}.pdf", folder / f"{stem}.meta.json"
        if not pdf.is_file() or not sidecar.is_file():
            self.skipTest("Authentic retained JK brochure or metadata unavailable.")
        raw = pdf.read_bytes()
        pages = PdfReader(io.BytesIO(raw)).pages
        self.assertIn("74-383-3802 (9/17 143M)", pages[12].extract_text())
        sport, heading, _ = pages[9].extract_text().partition("\nSPORT\n")
        self.assertEqual(heading, "\nSPORT\n")
        standard, available = sport.split("\nSTANDARD", 1)[1].split("\nAVAILABLE", 1)
        self.assertIn("3.6L Pentastar ® V6 engine", " ".join(standard.split()))
        self.assertIn("Command-Trac ® 4x4 system", " ".join(standard.split()))
        self.assertIn("Air conditioning (standard on Wrangler Unlimited)", " ".join(available.split()))
        self.assertIn("ratio (4-door only)", " ".join(pages[9].extract_text().split()))
        metadata = snapshot_metadata_from_dict(json.loads(sidecar.read_text()))
        result = extract_jk_unlimited_sport(raw, metadata)
        self.assertEqual(result.provenance.extraction_provenance.raw_artifact_hash, JK_UNLIMITED_SPORT_HASH)
        self.assertEqual(
            {a.attribute_key: a.raw_value for a in result.source_assertions},
            {
                "make_name": "Jeep", "model_name": "Wrangler", "model_year": "2018",
                "generation_designation": "JK", "market": "US", "manufacturer_grade": "SPORT",
                "body_designation": "Wrangler Unlimited", "engine_descriptor": "3.6L Pentastar® V6",
                "drive_descriptor": "Command-Trac® 4x4 system",
            },
        )
