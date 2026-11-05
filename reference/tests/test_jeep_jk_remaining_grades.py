"""Offline tests for the four reviewed MY2018 US JK grade/body rows."""
from dataclasses import replace
import hashlib
import io
import json

from django.conf import settings
from django.test import SimpleTestCase
from pypdf import PdfReader

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.jeep import JK_UNLIMITED_SPORT_HASH, extract_jk_remaining_grade
from reference.ingestion.acquisition.snapshots import snapshot_metadata_from_dict
from reference.ingestion.contracts import SourceAssertion
from reference.ingestion.normalization.generation import generation_evidence_from_sets
from reference.ingestion.normalization.jeep import normalize_jeep
from reference.ingestion.serialization import (
    deserialize_artifact, normalized_interpretation_to_dict, serialize_artifact,
)
from reference.ingestion.validation import validate_source_assertion_set


EXPECTED = {
    "sahara": ("SAHARA®", "Wrangler", "Sahara", "Command-Trac® 4x4 system"),
    "unlimited-sahara": ("Sahara Unlimited", "Wrangler Unlimited", "Unlimited Sahara", "Command-Trac® 4x4 system"),
    "rubicon": ("RUBICON®", "Wrangler", "Rubicon", "Rock-Trac® 4x4 system"),
    "unlimited-rubicon": ("Rubicon® Unlimited", "Wrangler Unlimited", "Unlimited Rubicon", "Rock-Trac® 4x4 system"),
}


class JKRemainingGradeTests(SimpleTestCase):
    def setUp(self):
        stem = JK_UNLIMITED_SPORT_HASH.removeprefix("sha256:")
        folder = settings.BASE_DIR / "storage/raw_source_artifacts/jeep_usa"
        pdf, sidecar = folder / f"{stem}.pdf", folder / f"{stem}.meta.json"
        if not pdf.is_file() or not sidecar.is_file():
            self.skipTest("Authentic retained JK brochure or snapshot metadata unavailable.")
        self.raw = pdf.read_bytes()
        self.metadata = snapshot_metadata_from_dict(json.loads(sidecar.read_text()))

    def extract(self, configuration):
        return extract_jk_remaining_grade(self.raw, self.metadata, configuration)

    def test_actual_brochure_anchors_establish_both_bodies_and_standard_mechanics(self):
        pages = PdfReader(io.BytesIO(self.raw)).pages
        sahara, rubicon = pages[8].extract_text().split("\nSAHARA\n", 1)
        for section, system, body_evidence in (
            (sahara, "Command-Trac", "ratio (4-door only)"),
            (rubicon, "Rock-Trac", "alarm (4-door models only)"),
        ):
            standard = section.split("STANDARD", 1)[1].split("AVAILABLE", 1)[0]
            compact = " ".join(standard.split())
            self.assertIn("3.6L Pentastar ® V6 engine", compact)
            self.assertIn(f"{system} ® 4x4 system", compact)
            self.assertIn("(2-door only)", compact)
            self.assertIn(body_evidence, " ".join(section.split()))
        self.assertIn("Sahara Unlimited in Firecracker Red", pages[5].extract_text())
        self.assertIn("Rubicon® Unlimited in Black", pages[2].extract_text())
        self.assertIn("Unlimited Rubicon 484 / 644", pages[10].extract_text())
        self.assertIn("74-383-3802 (9/17 143M)", pages[12].extract_text())

    def test_four_authentic_assertion_sets_and_normalized_identities(self):
        ids = set()
        for key, (grade, body, trim, drive) in EXPECTED.items():
            with self.subTest(configuration=key):
                source = self.extract(key)
                validate_source_assertion_set(source)
                serialized = serialize_artifact(source)
                self.assertEqual(serialized, serialize_artifact(self.extract(key)))
                source = deserialize_artifact(serialized)
                self.assertEqual(source.provenance.native_record_id, f"pdf-page-9-{key}")
                self.assertEqual(source.provenance.extraction_provenance.raw_artifact_hash, JK_UNLIMITED_SPORT_HASH)
                self.assertEqual(source.provenance.source_locator, self.metadata.publisher_locator)
                rows = {a.attribute_key: a for a in source.source_assertions}
                self.assertEqual(len(rows), 9)
                for attribute, expected in (
                    ("manufacturer_grade", grade), ("body_designation", body),
                    ("engine_descriptor", "3.6L Pentastar® V6"), ("drive_descriptor", drive),
                    ("generation_designation", "JK"),
                ):
                    self.assertEqual(rows[attribute].raw_value, expected)
                    self.assertTrue(rows[attribute].source_context.startswith("PDF page"))
                self.assertIn("PDF page 9", rows["body_designation"].source_context)
                qualifier = "4-door" if body == "Wrangler Unlimited" else "2-door only"
                self.assertIn(qualifier, rows["body_designation"].source_context)
                self.assertIn("STANDARD column", rows["drive_descriptor"].source_context)
                self.assertFalse(ids.intersection(a.assertion_id for a in rows.values()))
                ids.update(a.assertion_id for a in rows.values())

                interpretations = normalize_jeep(source)
                output = {i.target_attribute_key: i.normalized_concept for i in interpretations}
                self.assertEqual(len(interpretations), 8)
                engine = output.pop("engine_displacement_liters")
                self.assertEqual((engine.normalized_value, engine.normalized_unit), (3.6, "L"))
                self.assertEqual(output, dict(make="Jeep", model="Wrangler", model_year=2018, market="US",
                                              trim=trim, engine_cylinders=6, generic_drive_classification="4WD"))
                ordered = replace(source, source_assertions=list(reversed(source.source_assertions)))
                self.assertEqual([normalized_interpretation_to_dict(i) for i in interpretations],
                                 [normalized_interpretation_to_dict(i) for i in normalize_jeep(ordered)])
                for interpretation in interpretations:
                    original = next(a for a in rows.values() if a.assertion_id == interpretation.source_assertion_ref)
                    self.assertEqual(interpretation.manufacturer_term, original.raw_value)
                    self.assertEqual(interpretation.raw_source_value, original.raw_value)
                # Verify the existing document-qualified identity projection
                # without assembling a Candidate v2 or resolving a Generation.
                generation, documents = generation_evidence_from_sets([source])
                self.assertEqual(len(generation), 1)
                self.assertEqual(generation[0]["native_identifier"], "JK")
                self.assertEqual(generation[0]["assertion_id"], rows["generation_designation"].assertion_id)
                self.assertEqual(generation[0]["document_hash"], JK_UNLIMITED_SPORT_HASH)
                self.assertEqual(generation[0]["assertion_set_id"], source.provenance.native_record_id)
                self.assertEqual({a["assertion_id"] for a in documents[0]["assertions"]},
                                 {a.assertion_id for a in rows.values()})

    def test_extraction_rejects_wrong_publication_scope_and_unsupported_selection(self):
        changed = self.raw + b"\n% unreviewed revision"
        matching_changed = replace(self.metadata, content_hash="sha256:" + hashlib.sha256(changed).hexdigest())
        for raw, metadata in (
            (changed, matching_changed),
            (self.raw, replace(self.metadata, content_hash="sha256:" + "0" * 64)),
            (self.raw, replace(self.metadata, unknown_fields={"publication_revision": "74-383-3871"})),
            (self.raw, replace(self.metadata, publisher_locator="https://example.invalid/wrangler.pdf")),
            (self.raw, replace(self.metadata, source_applicability=replace(self.metadata.source_applicability, market="CA"))),
        ):
            with self.assertRaises(AcquisitionError):
                extract_jk_remaining_grade(raw, metadata, "sahara")
        with self.assertRaises(AcquisitionError):
            self.extract("rubicon-recon")

    def test_normalization_rejects_mixed_body_grade_mechanics_and_altered_provenance(self):
        sahara = self.extract("sahara")
        unlimited = self.extract("unlimited-sahara")
        rubicon = self.extract("rubicon")
        for source, key, changes in (
            (sahara, "drive_descriptor", {"raw_value": EXPECTED["rubicon"][3]}),
            (rubicon, "drive_descriptor", {"raw_value": EXPECTED["sahara"][3]}),
            (sahara, "drive_descriptor", {"raw_value": "2WD"}),
            (sahara, "body_designation", {"raw_value": "Wrangler Unlimited", "source_context": "PDF page 9 (4-door only)"}),
            (unlimited, "body_designation", {"raw_value": "Wrangler", "source_context": "PDF page 9 (2-door only)"}),
            (sahara, "manufacturer_grade", {"raw_value": "Altitude"}),
            (rubicon, "manufacturer_grade", {"raw_value": "Rubicon Recon"}),
            (rubicon, "generation_designation", {"raw_value": "JL"}),
            (rubicon, "model_year", {"raw_value": "2017"}),
            (rubicon, "engine_descriptor", {"assertion_id": "different_id"}),
            (rubicon, "engine_descriptor", {"source_context": "Unrelated section"}),
        ):
            with self.subTest(key=key, changes=changes), self.assertRaises(ValueError):
                normalize_jeep(replace(source, source_assertions=[
                    replace(a, **changes) if a.attribute_key == key else a for a in source.source_assertions
                ]))
        p = sahara.provenance
        for mutated in (
            replace(sahara, provenance=replace(p, native_record_id=unlimited.provenance.native_record_id)),
            replace(sahara, provenance=replace(p, unknown_fields=p.unknown_fields | {"publication_revision": "changed"})),
            replace(sahara, provenance=replace(p, extraction_provenance=replace(
                p.extraction_provenance, raw_artifact_hash="sha256:" + "0" * 64))),
            replace(sahara, source_assertions=[a for a in sahara.source_assertions if a.attribute_key != "body_designation"]),
            replace(sahara, source_assertions=[*sahara.source_assertions, SourceAssertion("other", "manufacturer_grade", "Rubicon")]),
        ):
            with self.assertRaises(ValueError):
                normalize_jeep(mutated)
