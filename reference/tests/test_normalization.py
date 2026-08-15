"""
Automated Test Suite for Source Assertion Normalization (RA-014 / RA-015).

Tests shared contract dispatch, NHTSA and EPA Category C mappings, drivetrain evidence safety,
unmapped handling (Case A vs Case B), parsing failure handling, determinism, and integration
with offline RA-013 acquisition adapters.
"""

from pathlib import Path
from unittest import TestCase

from reference.ingestion import (
    EPAAdapter,
    NHTSAAdapter,
    NormalizedInterpretation,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
    TechnicalValue,
    UnsupportedSourceError,
    normalize_source_assertions,
)
from reference.ingestion.contracts import Envelope


class NormalizationTestCase(TestCase):
    """Test suite for source assertion normalization pipeline."""

    def setUp(self):
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "acquisition"

    def _create_mock_transport(self, status_code: int, payload_file: Path):
        with open(payload_file, "rb") as f:
            content = f.read()

        def mock_transport(url: str, headers: dict, timeout: int):
            return status_code, content, {"Content-Type": "application/json"}

        return mock_transport

    def _create_sample_envelope(self) -> Envelope:
        return Envelope(
            artifact_type="rigarchive.source_assertion_set.v1",
            schema_version="1.0.0",
            created_at="2026-08-15T12:00:00Z",
        )


    # --- 1. Shared Contract & Dispatch Tests ---

    def test_unsupported_source_error(self):
        env = self._create_sample_envelope()
        prov = SourceMetadata(
            source_id="unsupported_source_xyz",
            source_type="regulatory_api",
            source_locator="https://example.com/api",
            retrieved_at="2026-08-15T12:00:00Z",
        )
        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_01",
                    attribute_key="some_key",
                    raw_value="some_value",
                    extracted_at="2026-08-15T12:00:00Z",
                )
            ],
        )

        with self.assertRaises(UnsupportedSourceError) as ctx:
            normalize_source_assertions(sas)
        self.assertIn("unsupported_source_xyz", str(ctx.exception))

    # --- 2. NHTSA Normalization Tests ---

    def test_nhtsa_category_c_mappings(self):
        fixture_path = self.fixtures_dir / "nhtsa" / "get_models_toyota_2020.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = NHTSAAdapter(transport=mock_transport)
        assertion_sets = adapter.acquire_models_for_make_year("Toyota", 2020)
        self.assertGreaterEqual(len(assertion_sets), 1)

        # Focus on 4Runner record assertion set
        sas_4runner = next(
            s for s in assertion_sets
            if any(a.attribute_key == "model_name" and a.raw_value == "4Runner" for a in s.source_assertions)
        )

        interps = normalize_source_assertions(sas_4runner)
        self.assertEqual(len(interps), 4)

        interp_map = {i.target_attribute_key: i for i in interps}

        # 1. make_id -> nhtsa_make_id
        self.assertIn("nhtsa_make_id", interp_map)
        self.assertEqual(interp_map["nhtsa_make_id"].normalized_concept, 448)
        self.assertEqual(interp_map["nhtsa_make_id"].mapping_status, "mapped")

        # 2. make_name -> make
        self.assertIn("make", interp_map)
        self.assertEqual(interp_map["make"].normalized_concept, "Toyota")
        self.assertEqual(interp_map["make"].mapping_status, "mapped")

        # 3. model_id -> nhtsa_model_id
        self.assertIn("nhtsa_model_id", interp_map)
        self.assertEqual(interp_map["nhtsa_model_id"].normalized_concept, 11982)
        self.assertEqual(interp_map["nhtsa_model_id"].mapping_status, "mapped")

        # 4. model_name -> model
        self.assertIn("model", interp_map)
        self.assertEqual(interp_map["model"].normalized_concept, "4Runner")
        self.assertEqual(interp_map["model"].mapping_status, "mapped")

        # Verify provenance traceability
        for interp in interps:
            self.assertTrue(interp.source_assertion_ref.startswith("ast_nhtsa_"))

    # --- 3. EPA Normalization Tests ---

    def test_epa_category_c_mappings(self):
        fixture_path = self.fixtures_dir / "epa" / "vehicle_42101.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = EPAAdapter(transport=mock_transport)
        sas = adapter.acquire_vehicle_by_id("42101", make="Toyota", model="4Runner 4WD", model_year=2020)

        interps = normalize_source_assertions(sas)

        # Emitted assertions from EPA adapter:
        # 11 source assertions -> 12 normalized interpretations (since drive_descriptor emits 2)
        self.assertEqual(len(interps), 12)

        mapped_interps = [i for i in interps if i.mapping_status == "mapped"]
        unmapped_interps = [i for i in interps if i.mapping_status == "unmapped"]

        # 8 Category C mapped interpretations
        self.assertEqual(len(mapped_interps), 8)
        # 4 Category B unmapped interpretations (model, transmission_descriptor, vehicle_class, engine_description)
        self.assertEqual(len(unmapped_interps), 4)

        target_map = {}
        for i in mapped_interps:
            target_map[i.target_attribute_key] = i

        # model_year -> 2020 (integer)
        self.assertEqual(target_map["model_year"].normalized_concept, 2020)

        # make -> Toyota
        self.assertEqual(target_map["make"].normalized_concept, "Toyota")

        # drive_descriptor -> generic_drive_classification ("4WD") & drivetrain_architecture ("part_time_4wd")
        self.assertEqual(target_map["generic_drive_classification"].normalized_concept, "4WD")
        self.assertEqual(target_map["drivetrain_architecture"].normalized_concept, "part_time_4wd")

        # Verify 1 source assertion -> 2 interpretations provenance share
        drive_ast_id = next(a.assertion_id for a in sas.source_assertions if a.attribute_key == "drive_descriptor")
        self.assertEqual(target_map["generic_drive_classification"].source_assertion_ref, drive_ast_id)
        self.assertEqual(target_map["drivetrain_architecture"].source_assertion_ref, drive_ast_id)

        # engine_displacement_liters -> TechnicalValue(4.0, "L", "4.0")
        tech_val = target_map["engine_displacement_liters"].normalized_concept
        self.assertIsInstance(tech_val, TechnicalValue)
        self.assertEqual(tech_val.normalized_value, 4.0)
        self.assertEqual(tech_val.normalized_unit, "L")

        # engine_cylinders -> 6 (integer)
        self.assertEqual(target_map["engine_cylinders"].normalized_concept, 6)

        # city_mpg_epa_rating -> 16 (integer)
        self.assertEqual(target_map["city_mpg_epa_rating"].normalized_concept, 16)

        # highway_mpg_epa_rating -> 19 (integer)
        self.assertEqual(target_map["highway_mpg_epa_rating"].normalized_concept, 19)

    # --- 4. Drivetrain Evidence Safety Boundary Tests ---

    def test_drivetrain_evidence_safety_boundary(self):
        fixture_path = self.fixtures_dir / "epa" / "vehicle_42101.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = EPAAdapter(transport=mock_transport)
        sas = adapter.acquire_vehicle_by_id("42101")

        interps = normalize_source_assertions(sas)
        target_keys = {i.target_attribute_key for i in interps}

        # Assert ONLY generic_drive_classification and drivetrain_architecture are produced
        self.assertIn("generic_drive_classification", target_keys)
        self.assertIn("drivetrain_architecture", target_keys)

        # Explicitly verify forbidden drivetrain concepts are NOT produced
        forbidden_keys = {
            "2H", "4H", "4L", "low_range", "transfer_case", "transfer_case_ratio",
            "center_differential", "locking_differential", "shift_mechanism",
            "drivetrain_operating_modes", "drivetrain_capabilities", "drivetrain_mode_states"
        }
        self.assertTrue(forbidden_keys.isdisjoint(target_keys))

    # --- 5. Category B Assertion Handling Tests ---

    def test_category_b_assertions_remain_unmapped(self):
        fixture_path = self.fixtures_dir / "epa" / "vehicle_42101.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = EPAAdapter(transport=mock_transport)
        sas = adapter.acquire_vehicle_by_id("42101")

        interps = normalize_source_assertions(sas)
        unmapped_interps = {i.target_attribute_key: i for i in interps if i.mapping_status == "unmapped"}

        # Category B assertions must have mapping_status == "unmapped" and normalized_concept == None
        for key in ["model", "transmission_descriptor", "vehicle_class", "engine_description"]:
            self.assertIn(key, unmapped_interps)
            self.assertIsNone(unmapped_interps[key].normalized_concept)
            self.assertEqual(unmapped_interps[key].mapping_status, "unmapped")

    # --- 6. Unmapped Handling (Case A vs Case B) Tests ---

    def test_unmapped_case_a_known_concept_unmapped_value(self):
        env = self._create_sample_envelope()
        prov = SourceMetadata(
            source_id="epa_fueleconomy",
            source_type="regulatory_api",
            source_locator="https://example.com/api",
            retrieved_at="2026-08-15T12:00:00Z",
        )
        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_epa_drive_unknown_01",
                    attribute_key="drive_descriptor",
                    raw_value="Quad-Drive System",
                    extracted_at="2026-08-15T12:00:00Z",
                )
            ],
        )

        interps = normalize_source_assertions(sas)
        self.assertEqual(len(interps), 1)

        interp = interps[0]
        self.assertEqual(interp.target_attribute_key, "generic_drive_classification")
        self.assertEqual(interp.mapping_status, "unmapped")
        self.assertIsNone(interp.normalized_concept)
        self.assertEqual(interp.raw_source_value, "Quad-Drive System")
        self.assertIn("Unmapped value", interp.normalization_notes)

    def test_unmapped_case_b_unknown_source_attribute(self):
        env = self._create_sample_envelope()
        prov = SourceMetadata(
            source_id="epa_fueleconomy",
            source_type="regulatory_api",
            source_locator="https://example.com/api",
            retrieved_at="2026-08-15T12:00:00Z",
        )
        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_epa_custom_01",
                    attribute_key="custom_unrecognized_field",
                    raw_value="custom_value_123",
                    extracted_at="2026-08-15T12:00:00Z",
                )
            ],
        )

        interps = normalize_source_assertions(sas)
        # Case B: Unknown target concept emits NO NormalizedInterpretation
        self.assertEqual(len(interps), 0)

        # SourceAssertion remains present and unchanged in SourceAssertionSet
        self.assertEqual(len(sas.source_assertions), 1)
        self.assertEqual(sas.source_assertions[0].attribute_key, "custom_unrecognized_field")
        self.assertEqual(sas.source_assertions[0].raw_value, "custom_value_123")

        # Confirm no unclassified_source_attribute or raw source key is manufactured as a normalized target
        self.assertFalse(any(i.target_attribute_key == "unclassified_source_attribute" for i in interps))
        self.assertFalse(any(i.target_attribute_key == "custom_unrecognized_field" for i in interps))


    # --- 7. Parsing Failure Handling Tests ---

    def test_parsing_failure_handling(self):
        env = self._create_sample_envelope()
        prov = SourceMetadata(
            source_id="epa_fueleconomy",
            source_type="regulatory_api",
            source_locator="https://example.com/api",
            retrieved_at="2026-08-15T12:00:00Z",
        )
        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=[
                SourceAssertion(
                    assertion_id="ast_epa_year_invalid",
                    attribute_key="model_year",
                    raw_value="invalid_year_string",
                    extracted_at="2026-08-15T12:00:00Z",
                ),
                SourceAssertion(
                    assertion_id="ast_epa_displ_invalid",
                    attribute_key="engine_displacement_liters",
                    raw_value="four_point_oh",
                    extracted_at="2026-08-15T12:00:00Z",
                ),
                SourceAssertion(
                    assertion_id="ast_epa_cyl_invalid",
                    attribute_key="engine_cylinders",
                    raw_value="six",
                    extracted_at="2026-08-15T12:00:00Z",
                ),
            ],
        )

        interps = normalize_source_assertions(sas)
        self.assertEqual(len(interps), 3)

        for interp in interps:
            self.assertEqual(interp.mapping_status, "unmapped")
            self.assertIsNone(interp.normalized_concept)
            self.assertIn("Parsing failure", interp.normalization_notes)

    # --- 8. Determinism Tests ---

    def test_normalization_determinism(self):
        fixture_path = self.fixtures_dir / "epa" / "vehicle_42101.json"
        mock_transport = self._create_mock_transport(200, fixture_path)

        adapter = EPAAdapter(transport=mock_transport)
        sas = adapter.acquire_vehicle_by_id("42101")

        interps_run1 = normalize_source_assertions(sas)
        interps_run2 = normalize_source_assertions(sas)

        self.assertEqual(len(interps_run1), len(interps_run2))

        for i1, i2 in zip(interps_run1, interps_run2):
            self.assertEqual(i1.interpretation_id, i2.interpretation_id)
            self.assertEqual(i1.source_assertion_ref, i2.source_assertion_ref)
            self.assertEqual(i1.target_attribute_key, i2.target_attribute_key)
            self.assertEqual(i1.normalized_concept, i2.normalized_concept)
            self.assertEqual(i1.raw_source_value, i2.raw_source_value)
            self.assertEqual(i1.mapping_status, i2.mapping_status)
            self.assertEqual(i1.normalization_notes, i2.normalization_notes)
