"""Offline Stage 2 checks. Early-year rows below are synthetic protocol inputs."""
import json
from dataclasses import replace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from reference.ingestion.acquisition.jeep import JK_UNLIMITED_SPORT_HASH, extract_jk_unlimited_sport
from reference.ingestion.acquisition.snapshots import snapshot_metadata_from_dict
from reference.ingestion.contracts import Envelope, SourceAssertion, SourceAssertionSet, SourceMetadata
from reference.ingestion.normalization.generation import generation_evidence_from_sets
from reference.ingestion.normalization.jeep import _normalize_reviewed_jk_row, normalize_jeep
from reference.ingestion.serialization import normalized_interpretation_to_dict, serialize_artifact


def concepts(interpretations):
    return {i.target_attribute_key: i for i in interpretations}


def synthetic_row(**changes):
    values = {
        "make_name": "Jeep", "model_name": "Wrangler", "model_year": "2011",
        "market": "US", "generation_designation": "JK", "body_designation": "Wrangler Unlimited",
        "manufacturer_grade": "Sport Unlimited", "engine_descriptor": "3.8L V6 SMPI",
        "drive_descriptor": "4WD",
    }
    values.update(changes)
    return [SourceAssertion(key, key, value, "Synthetic protocol row") for key, value in values.items()]


class JKReviewedRowProtocolTests(SimpleTestCase):
    def test_synthetic_2007_unlimited_x_2wd(self):
        rows = synthetic_row(model_year="2007", manufacturer_grade="Unlimited X", drive_descriptor="2WD")
        result = concepts(_normalize_reviewed_jk_row(rows))
        self.assertEqual(result["trim"].normalized_concept, "Unlimited X")
        self.assertEqual(result["model_year"].normalized_concept, 2007)
        self.assertEqual(result["engine_displacement_liters"].normalized_concept.normalized_value, 3.8)
        self.assertEqual(result["engine_displacement_liters"].normalized_concept.normalized_unit, "L")
        self.assertEqual(result["engine_cylinders"].normalized_concept, 6)
        self.assertEqual(result["generic_drive_classification"].normalized_concept, "2WD")

    def test_synthetic_aliases_preserve_terms(self):
        for grade in ("Sport", "Sahara", "Rubicon", "X"):
            year = "2007" if grade == "X" else "2011"
            for alias in (f"Unlimited {grade}", f"{grade} Unlimited", f"Wrangler Unlimited {grade}"):
                with self.subTest(alias=alias):
                    row = synthetic_row(model_year=year, manufacturer_grade=alias)
                    trim = concepts(_normalize_reviewed_jk_row(row))["trim"]
                    self.assertEqual(trim.normalized_concept, f"Unlimited {grade}")
                    self.assertEqual((trim.raw_source_value, trim.manufacturer_term), (alias, alias))

    def test_named_systems_remain_distinct_in_source_values(self):
        for grade, drive in (
            ("Sport", "Command-Trac® 4x4 system"), ("Rubicon", "Rock-Trac® 4x4 system"),
        ):
            result = concepts(_normalize_reviewed_jk_row(synthetic_row(
                manufacturer_grade=grade, drive_descriptor=drive,
            )))
            self.assertEqual(result["generic_drive_classification"].normalized_concept, "4WD")
            self.assertEqual(result["generic_drive_classification"].manufacturer_term, drive)

    def test_unsupported_scope_and_combinations_rejected(self):
        for changes in (
            {"manufacturer_grade": "Rubicon", "drive_descriptor": "2WD", "model_year": "2007"},
            {"drive_descriptor": "2WD"}, {"drive_descriptor": "Selectable 2WD mode"},
            {"manufacturer_grade": "Sport S"}, {"manufacturer_grade": "Willys Wheeler"},
            {"manufacturer_grade": "Freedom"}, {"manufacturer_grade": "Rubicon Hard Rock"},
            {"engine_descriptor": "3.6L Pentastar® V6"},
            {"manufacturer_grade": "Unlimited X"}, {"model_year": "2007"},
            {"body_designation": "Wrangler"}, {"body_designation": "Unknown"},
            {"generation_designation": "JL"}, {"market": "CA"},
            {"drive_descriptor": "Rock-Trac® 4x4 system"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                _normalize_reviewed_jk_row(synthetic_row(**changes))

    def test_incomplete_or_conflicting_row_rejected(self):
        rows = synthetic_row(manufacturer_grade="Sport")
        with self.assertRaises(ValueError):
            _normalize_reviewed_jk_row([a for a in rows if a.attribute_key != "body_designation"])
        for key, value in (
            ("manufacturer_grade", "Rubicon"), ("engine_descriptor", "3.6L Pentastar® V6"),
            ("drive_descriptor", "2WD"), ("generation_designation", "JL"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                _normalize_reviewed_jk_row(rows + [SourceAssertion("other", key, value)])

    def test_synthetic_row_has_no_production_admission(self):
        for year, grade, drive in (("2007", "Unlimited X", "2WD"), ("2011", "Sport Unlimited", "4WD")):
            assertions = SourceAssertionSet(
                Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
                SourceMetadata("jeep_usa", target_context={"market": "US"}),
                synthetic_row(model_year=year, manufacturer_grade=grade, drive_descriptor=drive),
            )
            with self.subTest(year=year), self.assertRaisesRegex(ValueError, "No reviewed JK"):
                normalize_jeep(assertions)


class JKStage1NormalizationTests(SimpleTestCase):
    def setUp(self):
        stem = JK_UNLIMITED_SPORT_HASH.removeprefix("sha256:")
        root = settings.BASE_DIR / "storage/raw_source_artifacts/jeep_usa"
        pdf, metadata = root / f"{stem}.pdf", root / f"{stem}.meta.json"
        if not pdf.is_file() or not metadata.is_file():
            self.skipTest("Authentic retained JK brochure or metadata unavailable.")
        self.source = extract_jk_unlimited_sport(
            pdf.read_bytes(), snapshot_metadata_from_dict(json.loads(metadata.read_text())),
        )

    def test_authentic_row_normalizes_deterministically_with_original_evidence(self):
        before = serialize_artifact(self.source)
        with patch("reference.ingestion.generation_correspondence.resolve_generation",
                   side_effect=AssertionError("Normalization must not resolve a Generation")):
            interpretations = normalize_jeep(self.source)
        serialized = [normalized_interpretation_to_dict(i) for i in interpretations]
        shuffled = replace(self.source, source_assertions=list(reversed(self.source.source_assertions)))
        self.assertEqual(serialized, [normalized_interpretation_to_dict(i) for i in normalize_jeep(shuffled)])
        self.assertEqual(before, serialize_artifact(self.source))
        output = concepts(interpretations)
        self.assertEqual(set(output), {
            "make", "model", "model_year", "market", "trim", "engine_displacement_liters",
            "engine_cylinders", "generic_drive_classification",
        })
        self.assertEqual(output["trim"].normalized_concept, "Unlimited Sport")
        self.assertEqual(output["engine_displacement_liters"].normalized_concept.normalized_value, 3.6)
        self.assertEqual(output["engine_cylinders"].normalized_concept, 6)
        self.assertEqual(output["generic_drive_classification"].normalized_concept, "4WD")
        self.assertEqual(output["market"].normalized_concept, "US")
        for interpretation in interpretations:
            original = next(a for a in self.source.source_assertions if a.assertion_id == interpretation.source_assertion_ref)
            self.assertEqual(interpretation.raw_source_value, original.raw_value)
            self.assertEqual(interpretation.manufacturer_term, original.raw_value)
        generation, _ = generation_evidence_from_sets([self.source])
        self.assertEqual(len(generation), 1)
        self.assertEqual(generation[0]["native_identifier"], "JK")
        self.assertEqual(generation[0]["document_hash"], JK_UNLIMITED_SPORT_HASH)
        self.assertEqual(generation[0]["assertion_set_id"], "pdf-page-10-sport-unlimited")

    def test_stage1_marker_cannot_admit_unrelated_or_modified_evidence(self):
        for key, value in (
            ("generation_designation", "JL"), ("manufacturer_grade", "Sport S"),
            ("drive_descriptor", "2WD"), ("engine_descriptor", "3.8L V6"),
        ):
            rows = [replace(a, raw_value=value) if a.attribute_key == key else a for a in self.source.source_assertions]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "Exact reviewed"):
                normalize_jeep(replace(self.source, source_assertions=rows))
        for rows in (
            [a for a in self.source.source_assertions if a.attribute_key != "body_designation"],
            self.source.source_assertions + [SourceAssertion("foreign", "generation_section", "ALL-NEW 2018 WRANGLER")],
            [replace(a, source_context="Unrelated grade column") if a.attribute_key == "engine_descriptor" else a
             for a in self.source.source_assertions],
        ):
            with self.assertRaisesRegex(ValueError, "Exact reviewed"):
                normalize_jeep(replace(self.source, source_assertions=rows))

    def test_incorrect_publication_and_market_rejected(self):
        p = self.source.provenance
        for provenance in (
            replace(p, source_locator="https://example.invalid/wrangler.pdf"),
            replace(p, unknown_fields=p.unknown_fields | {"publication_revision": "other"}),
            replace(p, source_applicability=None, target_context={"market": "US"}),
        ):
            with self.subTest(provenance=provenance), self.assertRaisesRegex(ValueError, "Exact reviewed"):
                normalize_jeep(replace(self.source, provenance=provenance))
