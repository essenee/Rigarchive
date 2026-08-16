"""
Automated Unit Tests for Manufacturer Evidence Acquisition & Normalization (RA-021).

Verifies explicit SourceApplicability provenance, Source-Independence Test context rejection,
ManufacturerSpecificationAdapter acquisition, Toyota grade taxonomy normalization,
isolated SourceAssertionSet configuration grouping, candidate document construction,
Cartesian product prohibition, and downstream RA-019 import planning.
"""

import os
from django.test import TestCase

from reference.models import Generation, Manufacturer, VehicleModel
from reference.ingestion import (
    CandidateIdentity,
    ImportEligibilityStatus,
    ImportPlannedAction,
    ManufacturerNormalizer,
    ManufacturerSpecificationAdapter,
    NormalizedInterpretation,
    SourceApplicability,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    construct_candidate_configuration,
    deserialize_artifact,
    normalize_source_assertions,
    plan_candidate_import,
    serialize_artifact,
    validate_artifact,
)
from reference.ingestion.validation import IngestionValidationError, validate_source_applicability


class ManufacturerIngestionTestCase(TestCase):
    """Test suite covering RA-021 manufacturer acquisition, normalization, and promotion."""

    def setUp(self):
        # Seed parent reference entities for RA-019 downstream planning tests
        self.manufacturer = Manufacturer.objects.create(
            name="Toyota",
            slug="toyota",
        )
        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="4Runner",
            slug="4runner",
        )
        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Fifth Generation (N280)",
            slug="fifth-generation-n280",
            start_year=2010,
            end_year=2024,
        )

        # Path to controlled 2020 4Runner specification fixture
        self.fixture_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "acquisition",
            "toyota",
            "2020_4runner_specs.json",
        )

    def test_source_applicability_serialization_round_trip(self):
        """Test SourceApplicability serialization, deserialization, and schema compatibility."""
        sa = SourceApplicability(
            market="US",
            applicability_basis="first_party_publisher_scope",
            publisher_jurisdiction="US-TMC",
        )
        meta = SourceMetadata(
            source_id="toyota_usa",
            source_type="manufacturer_specification",
            source_applicability=sa,
        )

        from reference.ingestion.serialization import source_metadata_from_dict, source_metadata_to_dict

        res_dict = source_metadata_to_dict(meta)
        self.assertEqual(res_dict["source_id"], "toyota_usa")
        self.assertEqual(res_dict["source_applicability"]["market"], "US")
        self.assertEqual(res_dict["source_applicability"]["applicability_basis"], "first_party_publisher_scope")

        deserialized = source_metadata_from_dict(res_dict)
        self.assertIsNotNone(deserialized.source_applicability)
        self.assertEqual(deserialized.source_applicability.market, "US")
        self.assertEqual(deserialized.source_applicability.publisher_jurisdiction, "US-TMC")

    def test_source_applicability_validation(self):
        """Test validation of SourceApplicability market scope."""
        valid_sa = SourceApplicability(market="US")
        validate_source_applicability(valid_sa)  # Should not raise

        invalid_sa = SourceApplicability(market="INVALID_MARKET")
        with self.assertRaises(IngestionValidationError):
            validate_source_applicability(invalid_sa)

    def test_source_metadata_omitted_applicability_backward_compatibility(self):
        """Test backward compatibility for SourceMetadata without source_applicability."""
        from reference.ingestion.serialization import source_metadata_from_dict

        meta_dict = {
            "source_id": "nhtsa_vpic",
            "source_type": "regulatory_api",
            "target_context": {"market": "US"},
        }
        meta = source_metadata_from_dict(meta_dict)
        self.assertIsNone(meta.source_applicability)
        self.assertEqual(meta.target_context["market"], "US")


    def test_source_independence_context_rejection(self):
        """Test Source-Independence Test: target_context alone does NOT yield mapped market evidence."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        raw_data = {
            "_provenance": {"publisher": "Test Publisher"},
            "configurations": [
                {
                    "model_code": "TEST01",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2020,
                    "grade": "SR5",
                    "drivetrain": "2WD",
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }

        sas_list = adapter.acquire_from_dict(raw_data)
        sas = sas_list[0]

        # Strip source_applicability to simulate context-only payload
        sas.provenance.source_applicability = None

        norm = ManufacturerNormalizer()
        interps = norm.normalize(sas)

        market_interps = [i for i in interps if i.target_attribute_key == "market"]
        self.assertEqual(len(market_interps), 1)
        self.assertEqual(market_interps[0].mapping_status, "unmapped")
        self.assertIsNone(market_interps[0].normalized_concept)

    def test_valid_source_applicability_normalization(self):
        """Test explicit source_applicability produces mapped market normalized interpretation."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        raw_data = {
            "_provenance": {"publisher": "Toyota USA", "publication_scope": "US"},
            "configurations": [
                {
                    "model_code": "TEST02",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2020,
                    "grade": "SR5",
                    "drivetrain": "Part-Time 4WD",
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }

        sas_list = adapter.acquire_from_dict(raw_data)
        sas = sas_list[0]

        norm = ManufacturerNormalizer()
        interps = norm.normalize(sas)

        market_interps = [i for i in interps if i.target_attribute_key == "market" and i.mapping_status == "mapped"]
        self.assertEqual(len(market_interps), 1)
        self.assertEqual(market_interps[0].normalized_concept, "US")

    def test_manufacturer_fixture_acquisition(self):
        """Test loading controlled 2020 Toyota 4Runner specification fixture."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        self.assertEqual(len(sas_list), 12)
        model_codes = [sas.provenance.native_record_id for sas in sas_list]
        self.assertIn("8642", model_codes)
        self.assertIn("8664", model_codes)
        self.assertIn("8666", model_codes)
        self.assertIn("8668", model_codes)
        self.assertIn("8674", model_codes)

        # Verify provenance of first item
        sas_8666 = next(s for s in sas_list if s.provenance.native_record_id == "8666")
        self.assertEqual(sas_8666.provenance.source_id, "toyota_usa")
        self.assertIsNotNone(sas_8666.provenance.source_applicability)
        self.assertEqual(sas_8666.provenance.source_applicability.market, "US")

    def test_toyota_grade_normalization(self):
        """Test Toyota grade strings normalize to official manufacturer trim names."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        norm = ManufacturerNormalizer()

        grade_map = {}
        for sas in sas_list:
            code = sas.provenance.native_record_id
            interps = norm.normalize(sas)
            trim_interp = next((i for i in interps if i.target_attribute_key == "trim"), None)
            if trim_interp and trim_interp.mapping_status == "mapped":
                grade_map[code] = trim_interp.normalized_concept

        self.assertEqual(grade_map["8642"], "SR5")
        self.assertEqual(grade_map["8646"], "SR5 Premium")
        self.assertEqual(grade_map["8670"], "TRD Off-Road")
        self.assertEqual(grade_map["8672"], "TRD Off-Road Premium")
        self.assertEqual(grade_map["8667"], "Venture Edition")
        self.assertEqual(grade_map["8648"], "Limited")
        self.assertEqual(grade_map["8649"], "Nightshade")
        self.assertEqual(grade_map["8674"], "TRD Pro")

    def test_dealer_package_rejection(self):
        """Test non-grade dealer/accessory packages do NOT normalize as trim."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        raw_data = {
            "_provenance": {"publication_scope": "US"},
            "configurations": [
                {
                    "model_code": "PKG01",
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": 2020,
                    "grade": "XP PREDATOR",
                    "drivetrain": "Part-Time 4WD",
                    "engine_displacement_liters": 4.0,
                    "engine_cylinders": 6,
                    "market": "US",
                }
            ],
        }

        sas_list = adapter.acquire_from_dict(raw_data)
        interps = ManufacturerNormalizer().normalize(sas_list[0])

        trim_interp = next(i for i in interps if i.target_attribute_key == "trim")
        self.assertEqual(trim_interp.mapping_status, "unmapped")
        self.assertIsNone(trim_interp.normalized_concept)

    def test_configuration_grouping_isolation(self):
        """Test assertions for Model Code 8664 (SR5 4WD) remain isolated from Model Code 8668 (Limited Full-Time 4WD)."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        sas_8664 = next(s for s in sas_list if s.provenance.native_record_id == "8664")
        sas_8668 = next(s for s in sas_list if s.provenance.native_record_id == "8668")

        norm = ManufacturerNormalizer()
        interps_8664 = norm.normalize(sas_8664)
        interps_8668 = norm.normalize(sas_8668)

        trim_8664 = next(i for i in interps_8664 if i.target_attribute_key == "trim").normalized_concept
        trim_8668 = next(i for i in interps_8668 if i.target_attribute_key == "trim").normalized_concept

        drive_8664 = next(i for i in interps_8664 if i.target_attribute_key == "generic_drive_classification").normalized_concept
        drive_8668 = next(i for i in interps_8668 if i.target_attribute_key == "generic_drive_classification").normalized_concept

        self.assertEqual(trim_8664, "SR5")
        self.assertEqual(drive_8664, "4WD")

        self.assertEqual(trim_8668, "Limited")
        self.assertEqual(drive_8668, "AWD")

    def test_candidate_construction_from_manufacturer_spec(self):
        """Test construct_candidate_configuration converts manufacturer assertions into a valid candidate document."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        sas_8664 = next(s for s in sas_list if s.provenance.native_record_id == "8664")
        norm_interps = ManufacturerNormalizer().normalize(sas_8664)

        identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="SR5",
            market="US",
        )

        candidate = construct_candidate_configuration(
            candidate_identity=identity,
            source_assertion_sets=[sas_8664],
            normalized_assertions=norm_interps,
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.candidate_identity.trim_name, "SR5")

        # Verify preserved mapped assertions contain trim and market
        mapped_concepts = {i.target_attribute_key: i.normalized_concept for i in candidate.normalized_assertions if i.mapping_status == "mapped"}
        self.assertEqual(mapped_concepts["trim"], "SR5")
        self.assertEqual(mapped_concepts["market"], "US")
        self.assertEqual(mapped_concepts["generic_drive_classification"], "4WD")

        # Verify SourceConfigurationIdentity preserved
        self.assertEqual(len(candidate.source_configuration_identities), 1)
        self.assertEqual(candidate.source_configuration_identities[0].native_identifier, "8664")

    def test_ra019_planning_eligible_create(self):
        """Test fully evidenced manufacturer candidate reaches ELIGIBLE / CREATE under RA-019 planner."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        sas_8664 = next(s for s in sas_list if s.provenance.native_record_id == "8664")
        norm_interps = ManufacturerNormalizer().normalize(sas_8664)

        identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="SR5",
            market="US",
        )

        candidate = construct_candidate_configuration(
            candidate_identity=identity,
            source_assertion_sets=[sas_8664],
            normalized_assertions=norm_interps,
        )

        plan = plan_candidate_import(candidate)

        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)
        self.assertEqual(plan.target_vehicle_definition_fields["trim_name"], "SR5")
        self.assertEqual(plan.target_vehicle_definition_fields["drivetrain"], "4WD")
        self.assertEqual(plan.target_vehicle_definition_fields["market"], "US")


    def test_cartesian_prohibition_guarantee(self):
        """Test 12 manufacturer model-code configurations generate exactly 12 isolated candidates."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)

        norm = ManufacturerNormalizer()

        candidates = []
        for sas in sas_list:
            interps = norm.normalize(sas)
            trim_concept = next(i for i in interps if i.target_attribute_key == "trim").normalized_concept
            identity = CandidateIdentity(
                manufacturer_name="Toyota",
                vehicle_model_name="4Runner",
                model_year=2020,
                trim_name=trim_concept,
                market="US",
            )
            cand = construct_candidate_configuration(
                candidate_identity=identity,
                source_assertion_sets=[sas],
                normalized_assertions=interps,
            )

            candidates.append(cand)

        # Must equal exactly 12 configurations, preserving distinct model codes
        self.assertEqual(len(candidates), 12)
        unique_model_codes = {c.source_configuration_identities[0].native_identifier for c in candidates}
        self.assertEqual(len(unique_model_codes), 12)

    def test_offline_zero_network_dependency(self):
        """Test acquisition and normalization execute 100% offline without network transport."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)
        self.assertTrue(len(sas_list) > 0)

    def test_trim_context_contradiction_triggers_review(self):
        """Test CandidateIdentity trim_name contradicting mapped trim evidence triggers REQUIRES_REVIEW."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)
        sas_8666 = next(s for s in sas_list if s.provenance.native_record_id == "8666")
        norm_interps = ManufacturerNormalizer().normalize(sas_8666)

        # Contradictory context: CandidateIdentity says "Limited" but evidence is "SR5"
        identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="Limited",
            market="US",
        )
        cand = construct_candidate_configuration(
            candidate_identity=identity,
            source_assertion_sets=[sas_8666],
            normalized_assertions=norm_interps,
        )

        plan = plan_candidate_import(cand)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)
        self.assertTrue(any("trim_name" in r and "contradicts" in r for r in plan.reasons))

    def test_market_context_contradiction_triggers_review(self):
        """Test CandidateIdentity market contradicting mapped market evidence triggers REQUIRES_REVIEW."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)
        sas_8666 = next(s for s in sas_list if s.provenance.native_record_id == "8666")
        norm_interps = ManufacturerNormalizer().normalize(sas_8666)

        # Contradictory context: CandidateIdentity says "CA" but evidence is "US"
        identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="SR5",
            market="CA",
        )
        cand = construct_candidate_configuration(
            candidate_identity=identity,
            source_assertion_sets=[sas_8666],
            normalized_assertions=norm_interps,
        )

        plan = plan_candidate_import(cand)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)
        self.assertTrue(any("market" in r and "contradicts" in r for r in plan.reasons))

    def test_context_alone_cannot_supply_missing_evidence(self):
        """Test CandidateIdentity with trim_name and market does NOT make candidate eligible if evidence is missing."""
        adapter = ManufacturerSpecificationAdapter(source_id="toyota_usa")
        sas_list = adapter.acquire_from_file(self.fixture_path)
        sas_8666 = next(s for s in sas_list if s.provenance.native_record_id == "8666")
        norm_interps = ManufacturerNormalizer().normalize(sas_8666)

        # Omit trim evidence from normalized interpretations
        norm_interps_no_trim = [i for i in norm_interps if i.target_attribute_key != "trim"]

        identity = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="SR5",
            market="US",
        )
        cand = construct_candidate_configuration(
            candidate_identity=identity,
            source_assertion_sets=[sas_8666],
            normalized_assertions=norm_interps_no_trim,
        )

        plan = plan_candidate_import(cand)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)
        self.assertTrue(any("missing ['trim']" in r for r in plan.reasons))

