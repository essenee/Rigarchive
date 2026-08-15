"""
Automated Test Suite for Candidate Configuration Construction & Aggregation (RA-016 / RA-017).

Validates pure Python candidate construction, multi-source attribute projection,
independent evidence lineage corroboration, conflict-safe scalar projection,
internal context verification, review workflow rules, and deterministic serialization.

Zero database writes or network calls are performed.
"""

import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from reference.ingestion import (
    CandidateConfigurationDocument,
    CandidateConstructionError,
    CandidateIdentity,
    EPAAdapter,
    NHTSAAdapter,
    NormalizedInterpretation,
    ReconciliationState,
    ReviewDisposition,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
    construct_candidate_configuration,
    deserialize_artifact,
    normalize_source_assertions,
    serialize_artifact,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "acquisition"


class CandidateConstructionTestCase(TestCase):
    """Test suite for construct_candidate_configuration and candidate builder logic."""

    def _create_mock_transport(self, status_code: int, file_path: Path):
        def mock_transport(url: str, headers: dict, timeout_seconds: int):
            with open(file_path, "rb") as f:
                body = f.read()
            return status_code, body, {"Content-Type": "application/json"}
        return mock_transport

    def setUp(self):
        nhtsa_path = FIXTURES_DIR / "nhtsa" / "get_models_toyota_2020.json"
        epa_path = FIXTURES_DIR / "epa" / "vehicle_42101.json"

        # Acquire NHTSA assertion sets via mock transport (returns List[SourceAssertionSet])
        nhtsa_adapter = NHTSAAdapter(transport=self._create_mock_transport(200, nhtsa_path))
        self.nhtsa_sas_list = nhtsa_adapter.acquire_models_for_make_year("Toyota", 2020)

        # Acquire EPA assertion set via mock transport (returns SourceAssertionSet)
        epa_adapter = EPAAdapter(transport=self._create_mock_transport(200, epa_path))
        self.epa_sas = epa_adapter.acquire_vehicle_by_id(42101)

        # Normalize both source assertion sets
        self.nhtsa_interps = []
        for sas in self.nhtsa_sas_list:
            self.nhtsa_interps.extend(normalize_source_assertions(sas))
        self.epa_interps = normalize_source_assertions(self.epa_sas)


        # Target candidate identity for controlled tests
        self.target_identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
        )


    # --- Scenario 1: Normal Controlled Aggregation (NHTSA + EPA 2020 4Runner) ---

    # --- Scenario 1: Normal Controlled Aggregation (NHTSA + EPA 2020 4Runner) ---

    def test_scenario_1_normal_controlled_aggregation(self):
        source_sets = self.nhtsa_sas_list + [self.epa_sas]
        all_interps = self.nhtsa_interps + self.epa_interps

        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=source_sets,
            normalized_assertions=all_interps,
            candidate_reference="cand_toyota_4runner_2020_controlled",
        )

        self.assertIsInstance(doc, CandidateConfigurationDocument)
        self.assertEqual(doc.candidate_reference, "cand_toyota_4runner_2020_controlled")
        self.assertEqual(doc.candidate_identity.manufacturer_name, "Toyota")
        self.assertEqual(doc.candidate_identity.vehicle_model_name, "4Runner")
        self.assertEqual(doc.candidate_identity.model_year, 2020)

        # 1. Source Native Configuration Identities
        native_ids = {i.native_identifier for i in doc.source_configuration_identities}
        self.assertIn("448", native_ids)    # NHTSA Make ID
        self.assertIn("11982", native_ids)  # NHTSA Model ID
        self.assertIn("42101", native_ids)  # EPA Vehicle ID

        # 2. Attribute Provenance & Evidence States
        self.assertIn("make", doc.attribute_provenance)
        self.assertEqual(len(doc.attribute_provenance["make"]), 2)  # Corroborated by NHTSA + EPA
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["make"].reconciliation_state,
            ReconciliationState.CORROBORATED.value,
        )

        self.assertIn("model", doc.attribute_provenance)
        self.assertEqual(len(doc.attribute_provenance["model"]), 1)  # NHTSA only ("4Runner")
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["model"].reconciliation_state,
            ReconciliationState.SINGLE_SOURCE.value,
        )

        # 3. Projected Technical Details
        tech = doc.normalized_technical_details
        self.assertIsNotNone(tech)
        self.assertIsNotNone(tech.drivetrain_details)
        self.assertEqual(tech.drivetrain_details.generic_classification, "4WD")
        self.assertEqual(tech.drivetrain_details.architecture, "part_time_4wd")

        self.assertIsNotNone(tech.engine)
        self.assertEqual(tech.engine.displacement.normalized_value, 4.0)
        self.assertEqual(tech.engine.displacement.normalized_unit, "L")
        self.assertEqual(tech.engine.cylinders, 6)

        self.assertIsNone(tech.transmission)  # Transmission remains unset (Category B in RA-015)

        # 4. Factory Technical Features
        self.assertEqual(len(doc.factory_technical_features), 0)

        # 5. Top-Level Review Disposition
        self.assertFalse(doc.reconciliation_and_review.requires_human_review)
        self.assertEqual(
            doc.reconciliation_and_review.review_workflow_disposition,
            ReviewDisposition.NOT_REQUIRED.value,
        )

    # --- Scenario 2: Candidate-Context Contradiction (Single Evidence Lineage) ---

    def test_scenario_2_context_contradiction_single_lineage(self):
        # Caller context says 2020, but single evidence lineage says 2019
        context_2020 = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
        )

        # EPA assertions naturally assert model_year = 2020; modify single interp to 2019 for contradiction
        single_interp = NormalizedInterpretation(
            interpretation_id="interp_epa_year_2019",
            source_assertion_ref=self.epa_sas.source_assertions[0].assertion_id,
            target_attribute_key="model_year",
            normalized_concept=2019,
            mapping_status="mapped",
        )

        doc = construct_candidate_configuration(
            candidate_identity=context_2020,
            source_assertion_sets=[self.epa_sas],
            normalized_assertions=[single_interp],
        )

        # Evidence state MUST remain single_source (for 2019), NOT conflicting
        self.assertIn("model_year", doc.attribute_provenance)
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["model_year"].reconciliation_state,
            ReconciliationState.SINGLE_SOURCE.value,
        )

        # Context contradiction triggers top-level human review
        self.assertTrue(doc.reconciliation_and_review.requires_human_review)
        self.assertEqual(
            doc.reconciliation_and_review.review_workflow_disposition,
            ReviewDisposition.PENDING_REVIEW.value,
        )
        self.assertIsNotNone(doc.reconciliation_and_review.reconciliation_notes)
        self.assertIn("Context contradiction detected", doc.reconciliation_and_review.reconciliation_notes)

    # --- Scenario 3: True Evidence Conflict + Context Contradiction ---

    def test_scenario_3_true_evidence_conflict_plus_context_contradiction(self):
        # Context = 2020. Source A = 2020. Source B = 2019.
        context_2020 = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
        )

        interp_nhtsa = NormalizedInterpretation(
            interpretation_id="interp_srcA_year_2020",
            source_assertion_ref=self.nhtsa_sas_list[0].source_assertions[0].assertion_id,
            target_attribute_key="model_year",
            normalized_concept=2020,
            mapping_status="mapped",
        )
        interp_epa = NormalizedInterpretation(
            interpretation_id="interp_srcB_year_2019",
            source_assertion_ref=self.epa_sas.source_assertions[0].assertion_id,
            target_attribute_key="model_year",
            normalized_concept=2019,
            mapping_status="mapped",
        )

        doc = construct_candidate_configuration(
            candidate_identity=context_2020,
            source_assertion_sets=self.nhtsa_sas_list + [self.epa_sas],
            normalized_assertions=[interp_nhtsa, interp_epa],
        )


        # Evidence reconciliation state MUST be conflicting
        self.assertIn("model_year", doc.attribute_provenance)
        self.assertEqual(len(doc.attribute_provenance["model_year"]), 2)
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["model_year"].reconciliation_state,
            ReconciliationState.CONFLICTING.value,
        )

        # Both interpretations retained in normalized_assertions
        self.assertEqual(len(doc.normalized_assertions), 2)

        # Human review required
        self.assertTrue(doc.reconciliation_and_review.requires_human_review)
        self.assertEqual(
            doc.reconciliation_and_review.review_workflow_disposition,
            ReviewDisposition.PENDING_REVIEW.value,
        )

    # --- Test 4: Repeated Acquisition / Same Lineage Test ---

    def test_repeated_acquisition_same_lineage_no_false_corroboration(self):
        # Same EPA record fetched twice (sharing same source_id and native_record_id)
        double_epa_interps = self.epa_interps + [
            NormalizedInterpretation(
                interpretation_id=f"{i.interpretation_id}_copy",
                source_assertion_ref=i.source_assertion_ref,
                target_attribute_key=i.target_attribute_key,
                normalized_concept=i.normalized_concept,
                mapping_status=i.mapping_status,
            )
            for i in self.epa_interps
        ]

        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=[self.epa_sas],
            normalized_assertions=double_epa_interps,
        )

        # Engine cylinders evidence state MUST be single_source, NOT corroborated
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["engine_cylinders"].reconciliation_state,
            ReconciliationState.SINGLE_SOURCE.value,
        )

    def test_same_source_different_records_same_value_not_corroborated(self):
        # Two different EPA vehicle records (42101 vs 42102) both asserting make = "Toyota"
        epa_sas_rec2 = SourceAssertionSet(
            envelope=self.epa_sas.envelope,
            provenance=SourceMetadata(
                source_id="epa_fueleconomy",
                source_type="public_api",
                source_locator="https://www.fueleconomy.gov/ws/rest/vehicle/42102",
                retrieved_at="2026-08-15T12:00:00Z",
                native_record_id="42102",
            ),
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_epa_make_rec2",
                    attribute_key="make",
                    raw_value="Toyota",
                )
            ],
        )

        interp_rec2 = NormalizedInterpretation(
            interpretation_id="interp_epa_make_rec2",
            source_assertion_ref="ast_epa_make_rec2",
            target_attribute_key="make",
            normalized_concept="Toyota",
            mapping_status="mapped",
        )

        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=[self.epa_sas, epa_sas_rec2],
            normalized_assertions=self.epa_interps + [interp_rec2],
        )

        # Same source_id with different native_record_id MUST NOT produce corroborated
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["make"].reconciliation_state,
            ReconciliationState.SINGLE_SOURCE.value,
        )

    def test_same_source_different_records_different_values_not_conflicting(self):
        # Two different EPA vehicle records (42101 with 6 cyl vs 42102 with 4 cyl)
        epa_sas_rec2 = SourceAssertionSet(
            envelope=self.epa_sas.envelope,
            provenance=SourceMetadata(
                source_id="epa_fueleconomy",
                source_type="public_api",
                source_locator="https://www.fueleconomy.gov/ws/rest/vehicle/42102",
                retrieved_at="2026-08-15T12:00:00Z",
                native_record_id="42102",
            ),
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_epa_cyl_rec2",
                    attribute_key="engine_cylinders",
                    raw_value="4",
                )
            ],
        )

        interp_rec2 = NormalizedInterpretation(
            interpretation_id="interp_epa_cyl_rec2",
            source_assertion_ref="ast_epa_cyl_rec2",
            target_attribute_key="engine_cylinders",
            normalized_concept=4,
            mapping_status="mapped",
        )

        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=[self.epa_sas, epa_sas_rec2],
            normalized_assertions=self.epa_interps + [interp_rec2],
        )

        # Same source_id with different values MUST NOT manufacture cross-source conflicting state
        self.assertEqual(
            doc.reconciliation_and_review.attribute_states["engine_cylinders"].reconciliation_state,
            ReconciliationState.SINGLE_SOURCE.value,
        )

        # Both interpretations and provenance links are preserved
        self.assertIn("interp_epa_cyl_rec2", doc.attribute_provenance["engine_cylinders"])
        cyl_interps = [i for i in doc.normalized_assertions if i.target_attribute_key == "engine_cylinders"]
        self.assertEqual(len(cyl_interps), 2)


    # --- Test 5: No Automatic Incomplete for Absent Optional Attributes ---

    def test_no_automatic_incomplete_for_absent_optional_attributes(self):
        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=self.nhtsa_sas_list + [self.epa_sas],
            normalized_assertions=self.nhtsa_interps + self.epa_interps,
        )

        # Absent optional attributes (e.g. horsepower) must NOT appear in attribute_states
        self.assertNotIn("horsepower", doc.reconciliation_and_review.attribute_states)
        self.assertNotIn("torque", doc.reconciliation_and_review.attribute_states)

    # --- Test 6: Preserved-but-Not-Projected Concepts Test ---

    def test_preserved_but_not_projected_concepts(self):
        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=[self.epa_sas],
            normalized_assertions=self.epa_interps,
        )

        # city_mpg_epa_rating and highway_mpg_epa_rating must be in normalized_assertions
        interp_keys = {i.target_attribute_key for i in doc.normalized_assertions}
        self.assertIn("city_mpg_epa_rating", interp_keys)
        self.assertIn("highway_mpg_epa_rating", interp_keys)

        # But must NOT populate attribute_provenance
        self.assertNotIn("city_mpg_epa_rating", doc.attribute_provenance)
        self.assertNotIn("highway_mpg_epa_rating", doc.attribute_provenance)

    # --- Test 7: Prohibit Tier 1 Normalization Bypass ---

    def test_prohibit_tier_1_normalization_bypass(self):
        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=self.nhtsa_sas_list + [self.epa_sas],
            normalized_assertions=self.nhtsa_interps + self.epa_interps,
        )

        # Tier 1 raw payloads contain descriptors, but factory_technical_features MUST remain []
        self.assertEqual(doc.factory_technical_features, [])

    # --- Test 8: Evidentiary Contradiction Preservation (Not Exception) ---

    def test_evidentiary_contradiction_preservation_not_exception(self):
        # Mapped assertion says make = "Lexus" against caller context Toyota
        lexus_interp = NormalizedInterpretation(
            interpretation_id="interp_lexus_make",
            source_assertion_ref=self.nhtsa_sas_list[0].source_assertions[0].assertion_id,
            target_attribute_key="make",
            normalized_concept="Lexus",
            mapping_status="mapped",
        )

        # MUST construct candidate successfully without raising CandidateConstructionError
        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=self.nhtsa_sas_list,
            normalized_assertions=[lexus_interp],
        )

        # Evidence is preserved and human review is flagged
        self.assertEqual(doc.normalized_assertions[0].normalized_concept, "Lexus")
        self.assertTrue(doc.reconciliation_and_review.requires_human_review)

    # --- Test 9: Broken Transitive Provenance Raises CandidateConstructionError ---

    def test_broken_transitive_provenance_raises_error(self):
        broken_interp = NormalizedInterpretation(
            interpretation_id="interp_broken_01",
            source_assertion_ref="nonexistent_assertion_id_12345",
            target_attribute_key="make",
            normalized_concept="Toyota",
            mapping_status="mapped",
        )

        with self.assertRaises(CandidateConstructionError):
            construct_candidate_configuration(
                candidate_identity=self.target_identity,
                source_assertion_sets=self.nhtsa_sas_list,
                normalized_assertions=[broken_interp],
            )

    # --- Test 10: Input Ordering Determinism Test ---

    def test_input_ordering_determinism(self):
        interps1 = self.nhtsa_interps + self.epa_interps
        interps2 = list(reversed(interps1))

        sources1 = self.nhtsa_sas_list + [self.epa_sas]
        sources2 = [self.epa_sas] + self.nhtsa_sas_list

        doc1 = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=sources1,
            normalized_assertions=interps1,
            candidate_reference="cand_fixed_ref",
        )

        doc2 = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=sources2,
            normalized_assertions=interps2,
            candidate_reference="cand_fixed_ref",
        )

        # Projected technical details and attribute provenance must be identical
        self.assertEqual(doc1.attribute_provenance, doc2.attribute_provenance)
        self.assertEqual(
            doc1.normalized_technical_details.engine.cylinders,
            doc2.normalized_technical_details.engine.cylinders,
        )

    # --- Test 11: Serialization & Validation Round-Trip ---

    def test_candidate_serialization_round_trip(self):
        doc = construct_candidate_configuration(
            candidate_identity=self.target_identity,
            source_assertion_sets=self.nhtsa_sas_list + [self.epa_sas],
            normalized_assertions=self.nhtsa_interps + self.epa_interps,
            candidate_reference="cand_roundtrip_test",
        )


        json_str = serialize_artifact(doc)
        deserialized_doc = deserialize_artifact(json_str)

        self.assertEqual(deserialized_doc.candidate_reference, doc.candidate_reference)
        self.assertEqual(
            deserialized_doc.candidate_identity.manufacturer_name,
            doc.candidate_identity.manufacturer_name,
        )
        self.assertEqual(deserialized_doc.attribute_provenance, doc.attribute_provenance)
