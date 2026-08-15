"""
Automated Test Suite for Reference Ingestion Intermediate Serialization (RA-012).

Tests contract validation, deterministic JSON round-trip serialization, unknown-field preservation,
drivetrain multi-dimensionality, unresolved feature handling, separated reconciliation/review states,
semantic missing-value handling, and controlled test fixtures.
"""

import json
from pathlib import Path
from django.test import TestCase

from reference.ingestion import (
    ArtifactType,
    AttributeReconciliationState,
    CandidateConfigurationDocument,
    CandidateIdentity,
    DrivetrainComponent,
    DrivetrainDetails,
    DrivetrainMode,
    EngineDetails,
    Envelope,
    FactoryTechnicalFeature,
    IngestionValidationError,
    MissingValueStatus,
    NormalizedInterpretation,
    NormalizedTechnicalDetails,
    PackageOrOption,
    ReconciliationAndReview,
    ReconciliationState,
    ReviewDisposition,
    SemanticMissingValue,
    SourceAssertion,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    TechnicalValue,
    TransmissionDetails,
    deserialize_artifact,
    serialize_artifact,
    validate_artifact,
    validate_candidate_configuration,
    validate_envelope,
    validate_semantic_missing_value,
    validate_source_assertion_set,
)


class IngestionSerializationTestCase(TestCase):
    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "ingestion"

    # --- 1. Envelope & Validation Tests ---

    def test_envelope_validation_success(self):
        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.0.0",
        )
        validate_envelope(env, ArtifactType.SOURCE_ASSERTION_SET.value)

    def test_envelope_validation_missing_type(self):
        env = Envelope(artifact_type="", schema_version="1.0.0")
        with self.assertRaises(IngestionValidationError):
            validate_envelope(env, ArtifactType.SOURCE_ASSERTION_SET.value)

    def test_envelope_validation_unsupported_major_version(self):
        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="2.0.0",
        )
        with self.assertRaises(IngestionValidationError) as ctx:
            validate_envelope(env, ArtifactType.SOURCE_ASSERTION_SET.value)
        self.assertIn("Unsupported major schema_version '2'", str(ctx.exception))

    # --- 2. SourceAssertionSet Tests ---

    def test_source_assertion_set_round_trip(self):
        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.0.0",
            created_at="2026-08-15T09:00:00Z",
            generator="test-gen/1.0",
        )
        prov = SourceMetadata(
            source_id="nhtsa_vpic",
            source_type="regulatory_api",
            source_locator="https://vpic.nhtsa.dot.gov/api/",
            retrieved_at="2026-08-15T09:00:00Z",
            review_status="not_reviewed",
        )
        ast1 = SourceAssertion(
            assertion_id="ast_01",
            attribute_key="make",
            raw_value="Toyota",
        )
        ast2 = SourceAssertion(
            assertion_id="ast_02",
            attribute_key="model",
            raw_value="4Runner",
        )
        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=[ast2, ast1],  # Unsorted order
        )

        validate_artifact(sas)

        json_str = serialize_artifact(sas)
        deserialized = deserialize_artifact(json_str)

        self.assertIsInstance(deserialized, SourceAssertionSet)
        self.assertEqual(deserialized.provenance.source_id, "nhtsa_vpic")
        self.assertEqual(len(deserialized.source_assertions), 2)

        # Deterministic serialization sorts assertions by assertion_id
        reserialized_json = serialize_artifact(deserialized)
        self.assertEqual(json_str, reserialized_json)

    def test_duplicate_source_assertion_id_rejected(self):
        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.0.0",
        )
        prov = SourceMetadata(source_id="epa")
        ast1 = SourceAssertion(assertion_id="ast_dup", attribute_key="k1", raw_value="v1")
        ast2 = SourceAssertion(assertion_id="ast_dup", attribute_key="k2", raw_value="v2")
        sas = SourceAssertionSet(envelope=env, provenance=prov, source_assertions=[ast1, ast2])

        with self.assertRaises(IngestionValidationError) as ctx:
            validate_artifact(sas)
        self.assertIn("Duplicate assertion_id 'ast_dup'", str(ctx.exception))

    # --- 3. Normalized Interpretations & Reference Validation ---

    def test_broken_source_assertion_reference_rejection(self):
        sas_env = Envelope(artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value, schema_version="1.0.0")
        sas = SourceAssertionSet(
            envelope=sas_env,
            provenance=SourceMetadata(source_id="epa"),
            source_assertions=[SourceAssertion(assertion_id="ast_valid", attribute_key="drive", raw_value="4WD")],
        )

        cand_env = Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0.0")
        interp = NormalizedInterpretation(
            interpretation_id="interp_01",
            source_assertion_ref="ast_NONEXISTENT",  # Broken reference
            target_attribute_key="drivetrain.architecture",
            normalized_concept="part-time 4WD",
        )
        cand = CandidateConfigurationDocument(
            envelope=cand_env,
            candidate_reference="cand_ref_test",
            candidate_identity=CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner"),
            normalized_assertions=[interp],
        )

        with self.assertRaises(IngestionValidationError) as ctx:
            validate_candidate_configuration(cand, source_assertion_set=sas)
        self.assertIn("references unknown source_assertion_ref 'ast_NONEXISTENT'", str(ctx.exception))

    # --- 4. 7-Dimension Drivetrain Representation ---

    def test_seven_dimension_drivetrain_round_trip(self):
        dt = DrivetrainDetails(
            generic_classification="four-wheel drive",
            architecture="full-time 4WD",
            components=[
                DrivetrainComponent(component_type="transfer_case", name="Two-speed transfer case", low_range_ratio=2.566),
                DrivetrainComponent(component_type="center_differential", name="Torsen Type-3 LSD", has_locking_feature=True),
            ],
            operating_modes=[
                DrivetrainMode(mode_code="H4F", name="Full-Time 4WD High (Open)", center_differential_state="open"),
                DrivetrainMode(mode_code="H4L", name="Full-Time 4WD High (Locked)", center_differential_state="locked"),
            ],
            capabilities=["full_time_4wd_operation", "center_differential_lock", "low_range"],
            manufacturer_terminology="Full-time 4WD with Torsen limited-slip center differential with lock feature",
        )

        cand = CandidateConfigurationDocument(
            envelope=Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0.0"),
            candidate_reference="cand_ref_fulltime_4wd",
            candidate_identity=CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner"),
            normalized_technical_details=NormalizedTechnicalDetails(drivetrain_details=dt),
        )

        json_str = serialize_artifact(cand)
        deserialized = deserialize_artifact(json_str)

        dt_res = deserialized.normalized_technical_details.drivetrain_details
        self.assertEqual(dt_res.generic_classification, "four-wheel drive")
        self.assertEqual(dt_res.architecture, "full-time 4WD")
        self.assertEqual(len(dt_res.components), 2)
        self.assertEqual(dt_res.components[1].name, "Torsen Type-3 LSD")
        self.assertTrue(dt_res.components[1].has_locking_feature)
        self.assertEqual(len(dt_res.operating_modes), 2)
        self.assertIn("center_differential_lock", dt_res.capabilities)
        self.assertEqual(dt_res.manufacturer_terminology, dt.manufacturer_terminology)

    # --- 5. Factory Technical Features & Neutral KDSS Representation ---

    def test_unresolved_factory_technical_features(self):
        ftf_kdss = FactoryTechnicalFeature(
            feature_name="Kinetic Dynamic Suspension System (KDSS)",
            source_classification="option_package",
            normalized_classification_status="unresolved",
            source_assertion_ref="ast_kdss_01",
        )
        cand = CandidateConfigurationDocument(
            envelope=Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0.0"),
            candidate_reference="cand_ref_kdss_test",
            candidate_identity=CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner"),
            factory_technical_features=[ftf_kdss],
            packages_and_options=[],  # KDSS is NOT in packages_and_options
        )

        json_str = serialize_artifact(cand)
        deserialized = deserialize_artifact(json_str)

        self.assertEqual(len(deserialized.factory_technical_features), 1)
        feat = deserialized.factory_technical_features[0]
        self.assertEqual(feat.feature_name, "Kinetic Dynamic Suspension System (KDSS)")
        self.assertEqual(feat.source_classification, "option_package")
        self.assertEqual(feat.normalized_classification_status, "unresolved")
        self.assertEqual(len(deserialized.packages_and_options), 0)

    # --- 6. Separated Reconciliation & Review States ---

    def test_separated_reconciliation_and_review_states(self):
        rar = ReconciliationAndReview(
            requires_human_review=True,
            review_workflow_disposition=ReviewDisposition.PENDING_REVIEW.value,
            attribute_states={
                "trim_name": AttributeReconciliationState(
                    reconciliation_state=ReconciliationState.CONFLICTING.value,
                    review_disposition=ReviewDisposition.PENDING_REVIEW.value,
                    conflict_details="Source A asserts 'SR5', Source B asserts 'SR5 Premium'",
                )
            },
        )
        cand = CandidateConfigurationDocument(
            envelope=Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0.0"),
            candidate_reference="cand_ref_conflict",
            candidate_identity=CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner"),
            reconciliation_and_review=rar,
        )

        validate_artifact(cand)

        json_str = serialize_artifact(cand)
        deserialized = deserialize_artifact(json_str)

        rar_res = deserialized.reconciliation_and_review
        self.assertTrue(rar_res.requires_human_review)
        self.assertEqual(rar_res.review_workflow_disposition, "pending_review")
        self.assertIn("trim_name", rar_res.attribute_states)
        self.assertEqual(rar_res.attribute_states["trim_name"].reconciliation_state, "conflicting")

    # --- 7. Semantic Missing Values ---

    def test_semantic_missing_values(self):
        smv = SemanticMissingValue(
            status=MissingValueStatus.NOT_APPLICABLE.value,
            reason="Part-time 4WD system does not utilize a center differential",
        )
        validate_semantic_missing_value(smv)

        smv_bad = SemanticMissingValue(status="invalid_status")
        with self.assertRaises(IngestionValidationError):
            validate_semantic_missing_value(smv_bad)

    # --- 8. Technical Values & Units ---

    def test_technical_value_with_units(self):
        eng = EngineDetails(
            code="1GR-FE",
            cylinders=6,
            displacement=TechnicalValue(normalized_value=4.0, normalized_unit="L", raw_source_string="4.0 L"),
            horsepower=TechnicalValue(normalized_value=270, normalized_unit="hp", raw_source_string="270 hp @ 5600 rpm", rpm_normalized=5600),
        )
        cand = CandidateConfigurationDocument(
            envelope=Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0.0"),
            candidate_reference="cand_ref_eng_test",
            candidate_identity=CandidateIdentity(manufacturer_name="Toyota", vehicle_model_name="4Runner"),
            normalized_technical_details=NormalizedTechnicalDetails(engine=eng),
        )

        json_str = serialize_artifact(cand)
        deserialized = deserialize_artifact(json_str)

        eng_res = deserialized.normalized_technical_details.engine
        self.assertEqual(eng_res.displacement.normalized_value, 4.0)
        self.assertEqual(eng_res.displacement.normalized_unit, "L")
        self.assertEqual(eng_res.horsepower.rpm_normalized, 5600)

    # --- 9. Unknown Field Preservation & Forward Compatibility ---

    def test_unknown_fields_forward_compatibility(self):
        raw_json = {
            "envelope": {
                "artifact_type": "rigarchive.candidate_configuration.v1",
                "schema_version": "1.1.0",  # Minor additive version bump
                "future_envelope_field": "future_val",
            },
            "candidate_reference": "cand_ref_future",
            "candidate_identity": {
                "manufacturer_name": "Toyota",
                "vehicle_model_name": "4Runner",
                "unmodeled_identity_meta": "extra_val",
            },
            "future_root_array": [1, 2, 3],
        }

        json_input = json.dumps(raw_json)
        deserialized = deserialize_artifact(json_input)

        self.assertEqual(deserialized.envelope.unknown_fields["future_envelope_field"], "future_val")
        self.assertEqual(deserialized.candidate_identity.unknown_fields["unmodeled_identity_meta"], "extra_val")
        self.assertEqual(deserialized.unknown_fields["future_root_array"], [1, 2, 3])

        # Verify lossless round-trip serialization preserves future unknown fields
        reserialized_json = serialize_artifact(deserialized)
        reserialized_dict = json.loads(reserialized_json)

        self.assertEqual(reserialized_dict["envelope"]["future_envelope_field"], "future_val")
        self.assertEqual(reserialized_dict["candidate_identity"]["unmodeled_identity_meta"], "extra_val")
        self.assertEqual(reserialized_dict["future_root_array"], [1, 2, 3])

    # --- 10. Controlled Fixture Tests ---

    def test_fixture_source_assertion_set_2020_4runner(self):
        fixture_path = self.fixtures_dir / "source_assertion_set_4runner_2020.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            data_str = f.read()

        sas = deserialize_artifact(data_str)
        self.assertIsInstance(sas, SourceAssertionSet)
        validate_artifact(sas)

        self.assertEqual(sas.provenance.source_id, "epa_fueleconomy")
        self.assertEqual(len(sas.source_assertions), 4)

    def test_fixture_candidate_configuration_2020_trd_offroad(self):
        sas_fixture_path = self.fixtures_dir / "source_assertion_set_4runner_2020.json"
        with open(sas_fixture_path, "r", encoding="utf-8") as f:
            sas = deserialize_artifact(f.read())

        cand_fixture_path = self.fixtures_dir / "candidate_configuration_4runner_2020_trd_offroad.json"
        with open(cand_fixture_path, "r", encoding="utf-8") as f:
            cand_str = f.read()

        cand = deserialize_artifact(cand_str)
        self.assertIsInstance(cand, CandidateConfigurationDocument)

        # Validate candidate with source assertion set context
        validate_candidate_configuration(cand, source_assertion_set=sas)

        self.assertEqual(cand.candidate_identity.trim_name, "TRD Off-Road Premium")
        self.assertEqual(cand.candidate_identity.model_year, 2020)
        self.assertEqual(len(cand.factory_technical_features), 2)

    def test_fixture_candidate_configuration_2020_trim_conflict(self):
        fixture_path = self.fixtures_dir / "candidate_configuration_4runner_2020_trim_conflict.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            cand = deserialize_artifact(f.read())

        self.assertIsInstance(cand, CandidateConfigurationDocument)
        validate_artifact(cand)

        rar = cand.reconciliation_and_review
        self.assertTrue(rar.requires_human_review)
        self.assertEqual(rar.attribute_states["trim_name"].reconciliation_state, "conflicting")
        self.assertEqual(rar.attribute_states["trim_name"].review_disposition, "pending_review")

    def test_fixture_candidate_configuration_2010_i4_2wd(self):
        fixture_path = self.fixtures_dir / "candidate_configuration_4runner_2010_i4_2wd.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            cand = deserialize_artifact(f.read())

        self.assertIsInstance(cand, CandidateConfigurationDocument)
        validate_artifact(cand)

        self.assertEqual(cand.candidate_identity.model_year, 2010)
        self.assertEqual(cand.normalized_technical_details.engine.cylinders, 4)
        self.assertEqual(cand.normalized_technical_details.engine.displacement.normalized_value, 2.7)
        self.assertEqual(cand.normalized_technical_details.drivetrain_details.architecture, "rear-wheel drive")
