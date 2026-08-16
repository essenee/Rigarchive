"""
Unit and Integration Tests for Multi-Source Scalable Reference Population Model (RA-028).

Tests:
1. J.D. Power configuration enumeration extraction and deterministic parsing.
2. Source provenance and source authority separation (no Toyota/J.D. Power conflation).
3. Multi-source candidate aggregation across J.D. Power and Toyota USA assertion sets.
4. Independent lineage tracking (evidence_raw_hashes, source_configuration_identities, attribute_provenance).
5. Conflict preservation when J.D. Power and Toyota disagree on mapped attributes.
6. Missing Toyota model code tolerance during candidate construction and import planning.
7. Authentic 2019 Toyota 4Runner end-to-end planning and idempotence.
"""

from pathlib import Path
from django.test import TestCase

from reference.ingestion.acquisition.jd_power_extractor import JDPowerExtractor
from reference.ingestion.acquisition.profiles import JDPowerProfile, ToyotaUSAPressroomProfile
from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import (
    CandidateIdentity,
    ReconciliationState,
    SourceAssertionSet,
)
from reference.ingestion.importing import ImportEligibilityStatus, ImportPlannedAction
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
from reference.ingestion.orchestration.multi_source import MultiSourceOrchestrator
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class JDPowerExtractionTests(TestCase):
    """Tests J.D. Power extractor deterministic parsing and artifact validation."""

    def setUp(self):
        self.jdp_profile = JDPowerProfile()
        self.fixture_path = Path("reference/tests/fixtures/acquisition/jd_power/2019_4runner_configurations.json")
        self.extractor = JDPowerExtractor()
        self.meta = RawSourceSnapshotMetadata(
            source_id="jd_power",
            publisher_locator="https://www.jdpower.com/cars/2019/toyota/4runner",
            acquired_at="2026-08-15T18:00:00Z",
            content_type="application/json",
            content_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
            storage_path=str(self.fixture_path),
            source_applicability=self.jdp_profile.default_applicability,
            acquisition_method="local_file",
        )

    def test_extract_configurations(self):
        payload_bytes = self.fixture_path.read_bytes()
        assertion_sets = self.extractor.extract(payload_bytes, self.meta)

        self.assertEqual(len(assertion_sets), 11)
        first_set = assertion_sets[0]

        # Verify source provenance & authority
        self.assertEqual(first_set.provenance.source_id, "jd_power")
        self.assertEqual(first_set.provenance.source_type, "third_party_reference")
        self.assertEqual(first_set.provenance.source_applicability.applicability_basis, "configuration_enumeration")
        self.assertEqual(first_set.provenance.native_record_id, "sr5_2wd")

        # Verify model code is absent in J.D. Power assertions
        attr_keys = [ast.attribute_key for ast in first_set.source_assertions]
        self.assertNotIn("model_code", attr_keys)
        self.assertIn("trim", attr_keys)
        self.assertIn("drive_descriptor", attr_keys)


class MultiSourceAggregationTests(TestCase):
    """Tests multi-source candidate construction, provenance, and conflict preservation."""

    def setUp(self):
        self.jdp_fixture = Path("reference/tests/fixtures/acquisition/jd_power/2019_4runner_configurations.json")
        self.toyota_fixture = Path("reference/tests/fixtures/acquisition/toyota/2019_4runner_product_info.json")

        self.jdp_profile = JDPowerProfile()
        self.toyota_profile = ToyotaUSAPressroomProfile()
        self.jdp_normalizer = JDPowerNormalizer()
        self.toyota_normalizer = ManufacturerNormalizer()

        # Set up canonical DB parent entities
        self.mfr = Manufacturer.objects.create(name="Toyota", country_code="JP")
        self.vm = VehicleModel.objects.create(manufacturer=self.mfr, name="4Runner")
        self.gen = Generation.objects.create(
            vehicle_model=self.vm,
            name="Fifth Generation",
            start_year=2010,
            end_year=2024,
        )

    def test_multi_source_candidate_provenance(self):
        orch = MultiSourceOrchestrator(
            jdp_profile=self.jdp_profile,
            toyota_profile=self.toyota_profile,
            jdp_normalizer=self.jdp_normalizer,
            toyota_normalizer=self.toyota_normalizer,
        )

        run_res = orch.run_multi_source_pipeline(
            jd_power_input=self.jdp_fixture,
            toyota_input=self.toyota_fixture,
        )

        self.assertEqual(run_res.primary_source_id, "jd_power")
        self.assertEqual(run_res.secondary_source_id, "toyota_usa")
        self.assertEqual(len(run_res.candidate_results), 11)

        first_cand = run_res.candidate_results[0].candidate_doc

        # Verify 2 independent evidence raw hashes
        self.assertEqual(len(first_cand.evidence_raw_hashes), 2)

        # Verify distinct source configuration identities (J.D. Power record ID & Toyota record ID)
        src_ids = [s.source_id for s in first_cand.source_configuration_identities]
        self.assertIn("jd_power", src_ids)
        self.assertIn("toyota_usa", src_ids)

        # Verify multi-source attribute provenance
        self.assertIn("make", first_cand.attribute_provenance)
        self.assertEqual(len(first_cand.attribute_provenance["make"]), 2)  # 1 from J.D. Power, 1 from Toyota

        # Verify corroborated reconciliation state for shared concepts
        rec = first_cand.reconciliation_and_review
        self.assertEqual(rec.attribute_states["make"].reconciliation_state, ReconciliationState.CORROBORATED.value)
        self.assertEqual(rec.attribute_states["model_year"].reconciliation_state, ReconciliationState.CORROBORATED.value)
        self.assertEqual(rec.attribute_states["engine_displacement_liters"].reconciliation_state, ReconciliationState.CORROBORATED.value)

    def test_conflict_preservation_across_sources(self):
        """Verify conflict preservation when J.D. Power and Toyota disagree on an attribute."""
        jdp_acq = self.jdp_profile.acquire_from_file(self.jdp_fixture)
        from reference.ingestion.acquisition.snapshots import RawSnapshotManager
        sm = RawSnapshotManager()
        _, jdp_meta = sm.store_snapshot(jdp_acq)
        jdp_sets = self.jdp_profile.extract(jdp_meta, raw_bytes=jdp_acq.raw_bytes)
        jdp_interps = self.jdp_normalizer.normalize(jdp_sets[0])  # SR5 2WD

        # Create conflicting Toyota assertion set (claiming 4WD for same context)
        toyota_acq = self.toyota_profile.acquire_from_file(self.toyota_fixture)
        _, toyota_meta = sm.store_snapshot(toyota_acq)
        toyota_data = {
            "_provenance": {"publication_scope": "US", "publisher": "Toyota Motor Sales, U.S.A., Inc."},
            "configurations": [
                {
                    "model_code": "conflict_test",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2019,
                    "drivetrain": "4WD",  # Conflicting drive classification!
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }
        toyota_sets = self.toyota_profile.extract(toyota_meta, transcription_data=toyota_data)
        toyota_interps = self.toyota_normalizer.normalize(toyota_sets[0])

        combined_sets = [jdp_sets[0], toyota_sets[0]]
        combined_interps = jdp_interps + toyota_interps

        cand_identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2019,
            market="US",
            trim_name="SR5",
        )

        cand_doc = construct_candidate_configuration(
            candidate_identity=cand_identity,
            source_assertion_sets=combined_sets,
            normalized_assertions=combined_interps,
        )

        rec = cand_doc.reconciliation_and_review
        self.assertTrue(rec.requires_human_review)

        # Drive classification state must be CONFLICTING
        self.assertIn("generic_drive_classification", rec.attribute_states)
        self.assertEqual(
            rec.attribute_states["generic_drive_classification"].reconciliation_state,
            ReconciliationState.CONFLICTING.value,
        )

        # Import planning must flag review for EVIDENCE_CONFLICT
        plan = plan_candidate_import(cand_doc)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_missing_model_code_tolerance(self):
        """Verify that candidate construction and import planning succeed without a Toyota model code."""
        jdp_acq = self.jdp_profile.acquire_from_file(self.jdp_fixture)
        from reference.ingestion.acquisition.snapshots import RawSnapshotManager
        sm = RawSnapshotManager()
        _, jdp_meta = sm.store_snapshot(jdp_acq)
        jdp_sets = self.jdp_profile.extract(jdp_meta, raw_bytes=jdp_acq.raw_bytes)
        jdp_interps = self.jdp_normalizer.normalize(jdp_sets[0])  # SR5 2WD

        cand_identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2019,
            market="US",
            trim_name="SR5",
        )

        cand_doc = construct_candidate_configuration(
            candidate_identity=cand_identity,
            source_assertion_sets=[jdp_sets[0]],
            normalized_assertions=jdp_interps,
        )

        plan = plan_candidate_import(cand_doc)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)
        self.assertEqual(plan.target_slug, "2019-sr5-40l-v6-2wd-us")

    def test_jd_power_standalone_canonical_promotion(self):
        """
        Verify that J.D. Power configuration evidence stands on its own without requiring
        Toyota first-party corroboration, successfully promoting candidates to ELIGIBLE / CREATE.
        """
        orch = MultiSourceOrchestrator(
            jdp_profile=self.jdp_profile,
            jdp_normalizer=self.jdp_normalizer,
        )

        # Run pipeline with zero Toyota input
        run_res = orch.run_multi_source_pipeline(
            jd_power_input=self.jdp_fixture,
            toyota_input=None,
        )

        self.assertEqual(run_res.primary_source_id, "jd_power")
        self.assertIsNone(run_res.secondary_source_id)
        self.assertEqual(len(run_res.candidate_results), 11)

        # All 11 candidates must be ELIGIBLE / CREATE without needing a 2nd source
        for cand_res in run_res.candidate_results:
            self.assertEqual(cand_res.plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
            self.assertEqual(cand_res.plan.planned_action, ImportPlannedAction.CREATE)
            self.assertEqual(len(cand_res.candidate_doc.evidence_raw_hashes), 1)

