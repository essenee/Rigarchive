"""W1 golden checks against supplied originals; no canonical writes or network."""
import copy
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError

from reference.ingestion.acquisition.jeep import PUBLICATIONS, acquire_local, extract_brochure
from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.snapshots import RawSnapshotManager
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import (
    CandidateIdentity, Envelope, SourceApplicability, SourceAssertion,
    SourceAssertionSet, SourceMetadata,
)
from reference.ingestion.normalization.jeep import normalize_jeep
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.importing.planner import plan_candidate_import


class JeepRuleSafetyTests(SimpleTestCase):
    def source(self):
        return SourceAssertionSet(
            Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
            SourceMetadata("jeep_usa", source_applicability=SourceApplicability(
                market="US", applicability_basis="official_jeep_en_us_publication")),
            [SourceAssertion("make", "make_name", "Jeep", "synthetic test"),
             SourceAssertion("grade", "manufacturer_grade", "Sport", "synthetic test"),
             SourceAssertion("engine", "engine_descriptor", "3.6L Pentastar ® V6", "synthetic test"),
             SourceAssertion("drive", "drive_descriptor", "Command-Trac", "synthetic test")],
        )

    def test_explicit_rules_preserve_raw_terms(self):
        interps = normalize_jeep(self.source())
        self.assertEqual(next(i.normalized_concept for i in interps if i.target_attribute_key == "engine_cylinders"), 6)
        self.assertEqual(next(i.raw_source_value for i in interps if i.target_attribute_key == "engine_cylinders"), "3.6L Pentastar ® V6")
        self.assertEqual(next(i.mapping_status for i in interps if i.target_attribute_key == "trim"), "unmapped")

    def test_direct_planner_blocks_before_database_queries(self):
        candidate = construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler"), [self.source()], normalize_jeep(self.source()))
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")

    def test_jdp_jeep_does_not_reach_toyota_fallback(self):
        sas = self.source()
        sas.provenance.source_id = "jd_power"
        with self.assertRaisesMessage(ValueError, "Toyota/VW fallback is forbidden"):
            JDPowerNormalizer().normalize(sas)

    def test_local_non_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.pdf"
            path.write_bytes(b"not an official PDF")
            with self.assertRaises(AcquisitionError):
                acquire_local(path, "jk")


class JeepW1Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = tempfile.TemporaryDirectory(prefix="jeep-w1-tests-")
        cls.sets = {}
        cls.acquired = {}
        cls.metadata = {}
        hashes = {
            "jk": "800f8ecd964e4df584cf6c382216f8401c5b273b85befa686faf93f92841a158",
            "jl": "711e265443dcf830ee789bdfd8cedd51699ab19a176ccd2718040c11dee20433",
        }
        try:
            for key, spec in PUBLICATIONS.items():
                path = settings.BASE_DIR / "storage/acquisition_inputs/jeep_2018" / spec["filename"]
                if not path.exists():
                    import unittest
                    raise unittest.SkipTest("Local authentic Jeep golden PDFs are not installed.")
                acq = acquire_local(path, key)
                assert hashlib.sha256(acq.raw_bytes).hexdigest() == hashes[key], "Golden source revision changed"
                _, meta = RawSnapshotManager(Path(cls.folder.name)).store_snapshot(acq)
                cls.acquired[key], cls.metadata[key] = acq, meta
                cls.sets[key] = extract_brochure(acq.raw_bytes, meta, key)
        except BaseException:
            cls.folder.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()
        super().tearDownClass()

    def candidate(self, key):
        sas = self.sets[key]
        return construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler", model_year=2018, trim_name="Sport", market="US"),
            [sas], normalize_jeep(sas), candidate_reference=f"synthetic-test-{key}", schema_version="2.0.0",
        )

    def test_all_pages_accounted_without_claiming_table_semantics(self):
        for key, sas in self.sets.items():
            pages = [a for a in sas.source_assertions if a.attribute_key == "published_page_content"]
            self.assertEqual(len(pages), PUBLICATIONS[key]["pages"])
            self.assertEqual([a.unknown_fields["pdf_page"] for a in pages], list(range(1, len(pages) + 1)))
            self.assertTrue(all(a.unknown_fields["accounting"] == "retained_pending_representation" for a in pages))
            self.assertTrue(all(set(a.raw_value) == {"plain_text", "layout_text"} for a in pages))

    def test_powertrain_raw_term_and_rule_preserved(self):
        for sas in self.sets.values():
            raw = next(a.raw_value for a in sas.source_assertions if a.attribute_key == "engine_descriptor")
            self.assertIn("®", raw)
            interps = normalize_jeep(sas)
            self.assertEqual(next(i.normalized_concept for i in interps if i.target_attribute_key == "engine_cylinders"), 6)
            self.assertEqual(next(i.normalized_concept for i in interps if i.target_attribute_key == "generic_drive_classification"), "4WD")

    def test_body_ambiguous_grade_cannot_be_promoted(self):
        for key in PUBLICATIONS:
            candidate = self.candidate(key)
            trim = next(i for i in candidate.normalized_assertions if i.target_attribute_key == "trim")
            self.assertEqual(trim.mapping_status, "unmapped")
            with patch("reference.ingestion.importing.planner.Manufacturer.objects.get", side_effect=AssertionError("Must block before parent query")):
                plan = plan_candidate_import(candidate)
            self.assertEqual(plan.planned_action.value, "flag_review")
            self.assertIn("trim", str(plan.reasons))

    def test_no_canonical_generation_code_fabricated(self):
        self.assertEqual(self.candidate("jk").generation_evidence, [])
        evidence = self.candidate("jl").generation_evidence
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["native_identifier"], "ALL-NEW 2018 WRANGLER")

    def test_candidate_round_trip_and_qualified_lineage(self):
        for key in PUBLICATIONS:
            candidate = self.candidate(key)
            result = deserialize_artifact(serialize_artifact(candidate))
            validate_candidate_configuration(result)
            self.assertEqual(result.evidence_raw_hashes, candidate.evidence_raw_hashes)
            self.assertTrue(all(i.source_assertion_ref.startswith("jeep_usa|sha256:") for i in result.normalized_assertions))

    def test_generation_projection_omission_rejected(self):
        candidate = self.candidate("jl")
        candidate.generation_evidence = []
        with self.assertRaises(ValidationError):
            validate_candidate_configuration(candidate)

    def test_snapshot_hash_and_publication_mismatch_rejected(self):
        for key in PUBLICATIONS:
            with self.assertRaises(AcquisitionError):
                extract_brochure(self.acquired[key].raw_bytes + b"changed", self.metadata[key], key)
            with self.assertRaises(AcquisitionError):
                extract_brochure(self.acquired[key].raw_bytes, self.metadata[key], "jl" if key == "jk" else "jk")

    def test_unknown_market_not_normalized(self):
        sas = copy.deepcopy(self.sets["jk"])
        sas.provenance.source_applicability = None
        self.assertFalse(any(i.target_attribute_key == "market" for i in normalize_jeep(sas)))

    def test_jeep_cannot_enter_toyota_jdp_fallback(self):
        sas = copy.deepcopy(self.sets["jk"])
        sas.provenance.source_id = "jd_power"
        with self.assertRaisesMessage(ValueError, "Toyota/VW fallback is forbidden"):
            JDPowerNormalizer().normalize(sas)

    def test_unsupported_grade_stays_unmapped(self):
        sas = copy.deepcopy(self.sets["jk"])
        next(a for a in sas.source_assertions if a.attribute_key == "manufacturer_grade").raw_value = "Unreviewed Edition"
        self.assertFalse(any(i.target_attribute_key == "trim" and i.mapping_status == "mapped" for i in normalize_jeep(sas)))
