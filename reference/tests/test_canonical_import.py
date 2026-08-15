"""
Unit tests for Canonical Reference Matching & Import Engine (RA-018 / RA-019).

Verifies plan-first eligibility analysis, parent resolution, create-only execution policy,
idempotent no-op logic, stale plan revalidation, transaction integrity safeguards,
and protection of canonical Reference domain records.
"""

from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase

from reference.ingestion.contracts import (
    ArtifactType,
    CandidateConfigurationDocument,
    CandidateIdentity,
    Envelope,
    NormalizedInterpretation,
    ReconciliationAndReview,
    ReconciliationState,
    ReviewDisposition,
    TechnicalValue,
)
from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportEligibilityStatus,
    ImportExecutionOutcome,
    ImportPlannedAction,
    execute_candidate_import,
    plan_candidate_import,
)
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class CanonicalImportTestCase(TestCase):
    """Test suite for RA-019 Canonical Reference Matching and Import Engine."""

    def setUp(self) -> None:
        """Seed clean canonical parent entities for deterministic import testing."""
        self.manufacturer = Manufacturer.objects.create(
            name="Toyota",
            country_code="JP",
            is_active=True,
        )
        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="4Runner",
            is_active=True,
        )
        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Fifth Generation",
            start_year=2010,
            end_year=None,
            generation_number=5,
            is_active=True,
        )

    def _build_candidate_doc(
        self,
        normalized_assertions: Optional[List[NormalizedInterpretation]] = None,
        candidate_identity: Optional[CandidateIdentity] = None,
        requires_human_review: bool = False,
        attribute_states: Optional[Dict[str, Any]] = None,
        schema_version: str = "1.0.0",
        candidate_reference: str = "cand_ref_test_001",
    ) -> CandidateConfigurationDocument:
        """Helper to construct a valid CandidateConfigurationDocument for test scenarios."""
        cid = candidate_identity or CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
        )
        rec_review = ReconciliationAndReview(
            requires_human_review=requires_human_review,
            review_workflow_disposition=ReviewDisposition.PENDING_REVIEW.value if requires_human_review else ReviewDisposition.NOT_REQUIRED.value,
            attribute_states=attribute_states or {},
            reconciliation_notes="",
        )
        return CandidateConfigurationDocument(
            envelope=Envelope(
                artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value,
                schema_version=schema_version,
                created_at="2026-08-15T12:00:00Z",
                generator="TestGenerator/1.0.0",
            ),
            candidate_reference=candidate_reference,
            candidate_identity=cid,
            source_configuration_identities=[],
            normalized_assertions=normalized_assertions or [],
            factory_technical_features=[],
            packages_and_options=[],
            attribute_provenance={},
            reconciliation_and_review=rec_review,
        )

    def _build_full_synthetic_assertions(
        self,
        make: str = "Toyota",
        model: str = "4Runner",
        year: int = 2020,
        drive: str = "4WD",
        displ: float = 4.0,
        cyls: int = 6,
        trim: str = "SR5",
        market: str = "US",
    ) -> Tuple[List[NormalizedInterpretation], CandidateIdentity]:
        """Construct complete evidence-backed mapped assertions and matching CandidateIdentity."""
        assertions = [
            NormalizedInterpretation(
                interpretation_id="interp_make",
                source_assertion_ref="ast_make",
                target_attribute_key="make",
                normalized_concept=make,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_model",
                source_assertion_ref="ast_model",
                target_attribute_key="model",
                normalized_concept=model,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_year",
                source_assertion_ref="ast_year",
                target_attribute_key="model_year",
                normalized_concept=year,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_drive",
                source_assertion_ref="ast_drive",
                target_attribute_key="generic_drive_classification",
                normalized_concept=drive,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_displ",
                source_assertion_ref="ast_displ",
                target_attribute_key="engine_displacement_liters",
                normalized_concept=TechnicalValue(displ, "L", str(displ)),
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_cyls",
                source_assertion_ref="ast_cyls",
                target_attribute_key="engine_cylinders",
                normalized_concept=cyls,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_trim",
                source_assertion_ref="ast_trim",
                target_attribute_key="trim",
                normalized_concept=trim,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_market",
                source_assertion_ref="ast_market",
                target_attribute_key="market",
                normalized_concept=market,
                mapping_status="mapped",
            ),
        ]
        cid = CandidateIdentity(
            manufacturer_name=make,
            vehicle_model_name=model,
            model_year=year,
            market=market,
        )
        return assertions, cid

    # --- Test Scenarios ---

    def test_production_2020_4runner_missing_trim_and_market_flags_review(self) -> None:
        """Production 2020 4Runner candidate (missing normalized trim & market) plans to REQUIRES_REVIEW (0 writes)."""
        assertions = [
            NormalizedInterpretation(
                interpretation_id="interp_make",
                source_assertion_ref="ast_make",
                target_attribute_key="make",
                normalized_concept="Toyota",
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_model",
                source_assertion_ref="ast_model",
                target_attribute_key="model",
                normalized_concept="4Runner",
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_year",
                source_assertion_ref="ast_year",
                target_attribute_key="model_year",
                normalized_concept=2020,
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_drive",
                source_assertion_ref="ast_drive",
                target_attribute_key="generic_drive_classification",
                normalized_concept="4WD",
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_displ",
                source_assertion_ref="ast_displ",
                target_attribute_key="engine_displacement_liters",
                normalized_concept=TechnicalValue(4.0, "L", "4.0"),
                mapping_status="mapped",
            ),
            NormalizedInterpretation(
                interpretation_id="interp_cyls",
                source_assertion_ref="ast_cyls",
                target_attribute_key="engine_cylinders",
                normalized_concept=6,
                mapping_status="mapped",
            ),
        ]
        candidate = self._build_candidate_doc(normalized_assertions=assertions)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.FLAGGED_REVIEW)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_context_only_trim_and_market_flags_review(self) -> None:
        """Candidate identity context alone (CandidateIdentity.trim_name = 'SR5') does NOT satisfy evidence."""
        assertions, _ = self._build_full_synthetic_assertions()
        # Remove trim interpretation from assertions
        assertions = [a for a in assertions if a.target_attribute_key != "trim"]

        cid = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            trim_name="SR5",
            market="US",
        )
        candidate = self._build_candidate_doc(
            normalized_assertions=assertions,
            candidate_identity=cid,
        )

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.FLAGGED_REVIEW)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_synthetic_valid_candidate_plans_create(self) -> None:
        """Synthetic candidate with all 8 evidence-backed attributes plans to ELIGIBLE / CREATE."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)
        self.assertEqual(plan.resolved_generation_id, self.generation.id)
        self.assertEqual(plan.target_vehicle_definition_fields["model_year"], 2020)
        self.assertEqual(plan.target_vehicle_definition_fields["trim_name"], "SR5")
        self.assertEqual(plan.target_vehicle_definition_fields["engine_name"], "4.0L V6")
        self.assertEqual(plan.target_vehicle_definition_fields["drivetrain"], "4WD")
        self.assertEqual(plan.target_vehicle_definition_fields["market"], "US")
        self.assertEqual(plan.target_slug, "2020-sr5-40l-v6-4wd-us")

    def test_first_representation_create_executes_successfully(self) -> None:
        """First-representation CREATE creates exactly one VehicleDefinition record."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        result = execute_candidate_import(plan)

        self.assertEqual(result.outcome, ImportExecutionOutcome.CREATED)
        self.assertIsNotNone(result.vehicle_definition_id)
        self.assertEqual(result.vehicle_definition_slug, "2020-sr5-40l-v6-4wd-us")

        self.assertEqual(VehicleDefinition.objects.count(), 1)
        vd = VehicleDefinition.objects.get(id=result.vehicle_definition_id)
        self.assertEqual(vd.generation, self.generation)
        self.assertEqual(vd.model_year, 2020)
        self.assertEqual(vd.trim_name, "SR5")
        self.assertEqual(vd.engine_name, "4.0L V6")
        self.assertEqual(vd.drivetrain, "4WD")
        self.assertEqual(vd.market, "US")

    def test_proven_dimensional_drivetrain_difference_creates_new_row(self) -> None:
        """Candidate sharing trim ('SR5') but differing in drivetrain ('2WD' vs '4WD') creates separate row."""
        # Existing 2WD row in DB
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
        )

        # Candidate is 4WD
        assertions, cid = self._build_full_synthetic_assertions(drive="4WD")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.CREATED)
        self.assertEqual(VehicleDefinition.objects.count(), 2)

    def test_trim_string_inequality_alone_flags_review(self) -> None:
        """Candidate differing only in trim string ('SR5 Premium' vs existing 'SR5') flags REQUIRES_REVIEW."""
        # Existing SR5 row in DB
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        # Candidate asserts SR5 Premium
        assertions, cid = self._build_full_synthetic_assertions(trim="SR5 Premium")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.FLAGGED_REVIEW)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_first_representation_plan_becomes_stale_when_namespace_changes(self) -> None:
        """First-representation CREATE plan returns ABORTED_STALE_PLAN if a new row appears in namespace before execution."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        # Insert a DIFFERENT row in the same namespace before execution
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)
        # Verify candidate row was NOT created (only the manually created Limited row exists)
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.assertEqual(VehicleDefinition.objects.first().trim_name, "Limited")

    def test_first_representation_concurrent_exact_target_yields_no_op(self) -> None:
        """First-representation CREATE plan returns NO_OP_EXACT_MATCH if exact target row appears before execution."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        # Insert EXACT target row before execution
        vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)
        self.assertEqual(result.vehicle_definition_id, vd.id)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_engine_display_text_difference_does_not_prove_distinctness(self) -> None:
        """Differing engine display string alone against existing same-trim row flags REQUIRES_REVIEW (no CREATE)."""
        # Existing row in DB
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        # Candidate has same trim ('SR5') and drivetrain ('4WD'), but different engine displacement (2.7L I4)
        assertions, cid = self._build_full_synthetic_assertions(displ=2.7, cyls=4)
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.FLAGGED_REVIEW)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_mechanical_create_plan_namespace_staleness(self) -> None:
        """Mechanical-dimension CREATE plan returns ABORTED_STALE_PLAN if namespace count changes before execution."""
        # Existing 2WD row in DB
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
        )

        # Candidate is 4WD -> MECHANICAL_DIMENSION CREATE plan
        assertions, cid = self._build_full_synthetic_assertions(drive="4WD")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        # Insert another row in namespace before execution
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)
        self.assertEqual(VehicleDefinition.objects.count(), 2)

    def test_mechanical_create_same_count_different_composition_staleness(self) -> None:
        """Mechanical CREATE plan returns ABORTED_STALE_PLAN if basis row is replaced and count remains unchanged."""
        basis = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
        )

        assertions, cid = self._build_full_synthetic_assertions(drive="4WD")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        # Remove basis row and insert Limited row so count remains 1
        basis.delete()
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)
        # Verify candidate was NOT created (only Limited exists)
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.assertEqual(VehicleDefinition.objects.first().trim_name, "Limited")

    def test_mechanical_create_basis_row_modified_staleness(self) -> None:
        """Mechanical CREATE plan returns ABORTED_STALE_PLAN if basis row fields are modified before execution."""
        basis = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
        )

        assertions, cid = self._build_full_synthetic_assertions(drive="4WD")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.CREATE)

        # Mutate basis row drivetrain in DB before execution
        basis.drivetrain = "4WD"
        basis.save()

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)



    def test_exact_existing_match_executes_no_op(self) -> None:
        """Re-importing exact matching candidate yields NO_OP_EXACT_MATCH (0 DB writes)."""
        vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.NO_OP_EXACT_MATCH)
        self.assertEqual(plan.existing_vehicle_definition_id, vd.id)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)
        self.assertEqual(result.vehicle_definition_id, vd.id)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_no_op_revalidation_detects_stale_deleted_row(self) -> None:
        """NO_OP plan row deleted before execution returns ABORTED_STALE_PLAN."""
        vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action, ImportPlannedAction.NO_OP_EXACT_MATCH)

        # Delete existing row before execution
        vd.delete()

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)

    def test_concurrent_insert_integrity_error_verifies_field_equality(self) -> None:
        """Concurrent insert IntegrityError with identical fields yields NO_OP_EXACT_MATCH."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)
        plan = plan_candidate_import(candidate)

        # Create row concurrently and simulate IntegrityError on save
        existing_vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        with patch.object(VehicleDefinition, "save", side_effect=IntegrityError("UNIQUE constraint failed")):
            result = execute_candidate_import(plan)

        self.assertEqual(result.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)
        self.assertEqual(result.vehicle_definition_id, existing_vd.id)

    def test_concurrent_insert_integrity_error_non_identical_row_rejects(self) -> None:
        """IntegrityError resulting in non-identical target fields returns REJECTED."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)
        plan = plan_candidate_import(candidate)

        # Force a slug collision in database with conflicting fields
        existing_vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",  # Conflicting drivetrain
            market="US",
        )
        existing_vd.slug = plan.target_slug
        existing_vd.save(update_fields=["slug"])

        # Patch pre-check filter to return None so save() is attempted and raises IntegrityError, then re-query returns existing_vd
        original_filter = VehicleDefinition.objects.filter
        call_count = 0

        def selective_filter(*args, **kwargs):
            nonlocal call_count
            if kwargs.get("slug") == plan.target_slug or "generation_id" in kwargs:
                call_count += 1
                if call_count <= 2:
                    return VehicleDefinition.objects.none()
                return original_filter(*args, **kwargs)
            return original_filter(*args, **kwargs)

        with patch("reference.models.VehicleDefinition.objects.filter", side_effect=selective_filter):
            with patch.object(VehicleDefinition, "save", side_effect=IntegrityError("UNIQUE constraint failed")):
                result = execute_candidate_import(plan)

        self.assertEqual(result.outcome, ImportExecutionOutcome.REJECTED)



    def test_planning_executes_zero_db_writes(self) -> None:
        """plan_candidate_import performs zero database mutations."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        initial_vd_count = VehicleDefinition.objects.count()
        initial_gen_count = Generation.objects.count()

        plan = plan_candidate_import(candidate)
        self.assertIsNotNone(plan)

        self.assertEqual(VehicleDefinition.objects.count(), initial_vd_count)
        self.assertEqual(Generation.objects.count(), initial_gen_count)

    def test_zero_parent_auto_creation_guarantee(self) -> None:
        """Automated importer NEVER creates missing Manufacturer, VehicleModel, or Generation records."""
        # Candidate asserts unknown Manufacturer "Ford"
        assertions, cid = self._build_full_synthetic_assertions(make="Ford", model="Bronco")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.INELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.REJECT)

        result = execute_candidate_import(plan)
        self.assertEqual(result.outcome, ImportExecutionOutcome.REJECTED)

        self.assertFalse(Manufacturer.objects.filter(name="Ford").exists())
        self.assertFalse(VehicleModel.objects.filter(name="Bronco").exists())

    def test_create_only_policy_never_updates_existing_rows(self) -> None:
        """Automated importer NEVER updates or overwrites existing VehicleDefinition records."""
        vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
            notes="Manually curated note",
        )

        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        result = execute_candidate_import(plan)

        self.assertEqual(result.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)

        # Refresh from DB and verify notes and fields are completely unchanged
        vd.refresh_from_db()
        self.assertEqual(vd.notes, "Manually curated note")

    # --- Edge Cases ---

    def test_missing_generation_rejects_import(self) -> None:
        """Model year outside any active Generation range rejects import."""
        assertions, cid = self._build_full_synthetic_assertions(year=1990)
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.INELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.REJECT)

    def test_overlapping_generations_flags_review(self) -> None:
        """Multiple overlapping active Generations flag review."""
        Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Overlapping Gen",
            start_year=2015,
            end_year=2022,
            generation_number=99,
            is_active=True,
        )

        assertions, cid = self._build_full_synthetic_assertions(year=2020)
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_unsupported_drivetrain_rejects_import(self) -> None:
        """Unsupported drivetrain string rejects import."""
        assertions, cid = self._build_full_synthetic_assertions(drive="HOVER")
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_schema_version_mismatch_rejects_import(self) -> None:
        """Unsupported major schema version rejects import."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(
            normalized_assertions=assertions,
            candidate_identity=cid,
            schema_version="2.0.0",
        )

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.INELIGIBLE)
        self.assertEqual(plan.planned_action, ImportPlannedAction.REJECT)

    def test_candidate_review_flag_preserves_review_status(self) -> None:
        """Top-level requires_human_review flag on candidate forces FLAG_REVIEW plan."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(
            normalized_assertions=assertions,
            candidate_identity=cid,
            requires_human_review=True,
        )

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_conflicting_attribute_state_flags_review(self) -> None:
        """Attribute with conflicting reconciliation_state forces FLAG_REVIEW plan."""
        assertions, cid = self._build_full_synthetic_assertions()
        from reference.ingestion.contracts import AttributeReconciliationState
        rar_states = {
            "engine": AttributeReconciliationState(
                reconciliation_state=ReconciliationState.CONFLICTING.value,
                review_disposition=ReviewDisposition.PENDING_REVIEW.value,
            )
        }
        candidate = self._build_candidate_doc(
            normalized_assertions=assertions,
            candidate_identity=cid,
            attribute_states=rar_states,
        )

        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status, ImportEligibilityStatus.REQUIRES_REVIEW)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_repeated_execution_is_idempotent(self) -> None:
        """Executing import twice for same candidate results in 1 CREATED and 1 NO_OP_EXACT_MATCH."""
        assertions, cid = self._build_full_synthetic_assertions()
        candidate = self._build_candidate_doc(normalized_assertions=assertions, candidate_identity=cid)

        plan1 = plan_candidate_import(candidate)
        res1 = execute_candidate_import(plan1)
        self.assertEqual(res1.outcome, ImportExecutionOutcome.CREATED)

        plan2 = plan_candidate_import(candidate)
        res2 = execute_candidate_import(plan2)
        self.assertEqual(res2.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)
        self.assertEqual(res2.vehicle_definition_id, res1.vehicle_definition_id)

        self.assertEqual(VehicleDefinition.objects.count(), 1)
