"""
Comprehensive Test Suite for General Canonical Record Correction Lifecycle (RA-029).

Verifies 12 governing requirements:
1. Correction creates a new canonical identity rather than mutating immutable slug identity.
2. Old UUID and slug remain historically present (with is_active=False).
3. Old execution receipt remains unchanged.
4. Correction audit linkage points old -> replacement with accurate snapshots.
5. Superseded row is excluded from active canonical matching.
6. Corrected row participates normally in exact-match planning.
7. Superseded row does not create stale namespace counts.
8. Correction is atomic (rollback on failure).
9. Duplicate/repeated correction is safely rejected or becomes an explicit no-op.
10. Unrelated canonical rows are untouched.
11. Public canonical browsing excludes superseded configurations.
12. Historical audit can retrieve superseded identity.
"""

from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse

from reference.ingestion.contracts import CandidateConfigurationDocument, CandidateIdentity
from reference.ingestion.importing import (
    CanonicalImportPlan,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportPlannedAction,
)
from reference.ingestion.importing.correction import execute_canonical_record_correction
from reference.ingestion.importing.planner import plan_candidate_import
from reference.models import (
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class CanonicalCorrectionLifecycleTests(TestCase):
    """RA-029 General Canonical Record Correction Lifecycle Test Suite."""

    def setUp(self):
        self.mfr = Manufacturer.objects.create(name="Toyota", country_code="JP")
        self.vm = VehicleModel.objects.create(manufacturer=self.mfr, name="4Runner")
        self.gen = Generation.objects.create(
            vehicle_model=self.vm,
            name="Fifth Generation",
            generation_number=5,
            start_year=2010,
        )

        # Create original (incorrect) canonical VehicleDefinition
        self.old_vd = VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="AWD",  # Misclassified
            market="US",
            is_active=True,
        )
        self.old_pk = self.old_vd.id
        self.old_uuid = str(self.old_vd.uuid)
        self.old_slug = self.old_vd.slug  # 2020-limited-40l-v6-awd-us

        # Create historical ImportExecutionReceipt for original promotion
        self.old_receipt = ImportExecutionReceipt.objects.create(
            operator_label="cli:test_operator",
            manifest_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
            candidate_reference="cand_old_8648",
            planned_action="create",
            create_basis="first_representation",
            source_id="toyota_usa",
            raw_artifact_hash="sha256:2222222222222222222222222222222222222222222222222222222222222222",
            raw_artifact_reference="storage/test_raw.json",
            native_identifier="8648",
            resolved_generation_id=self.gen.id,
            target_slug=self.old_slug,
            target_model_year=2020,
            target_trim_name="Limited",
            target_engine_name="4.0L V6",
            target_drivetrain="AWD",
            target_market="US",
            execution_outcome="created",
            created_vehicle_definition=self.old_vd,
            created_vehicle_definition_pk_snapshot=self.old_pk,
            created_vehicle_definition_uuid_snapshot=self.old_uuid,
            created_vehicle_definition_slug_snapshot=self.old_slug,
        )

        # Build replacement plan for 4WD identity
        self.replacement_plan = CanonicalImportPlan(
            candidate_reference="cand_new_8648",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.FIRST_REPRESENTATION,
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.vm.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={
                "model_year": 2020,
                "trim_name": "Limited",
                "engine_name": "4.0L V6",
                "drivetrain": "4WD",
                "market": "US",
            },
            target_slug="2020-limited-40l-v6-4wd-us",
            namespace_snapshot_count=0,
        )

    def test_1_correction_creates_new_canonical_identity_not_mutating_old_slug(self):
        """1. Correction creates a new canonical identity rather than mutating immutable slug identity."""
        res = execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
            correction_reason=CanonicalRecordCorrection.CorrectionReason.NORMALIZATION_RULE_CORRECTION,
            operator_label="cli:test_corrector",
        )

        self.assertEqual(res.outcome, "CORRECTED")
        self.assertNotEqual(res.replacement_vehicle_definition_id, self.old_pk)
        self.assertNotEqual(res.replacement_vehicle_definition_uuid, self.old_uuid)
        self.assertNotEqual(res.replacement_vehicle_definition_slug, self.old_slug)

        new_vd = VehicleDefinition.objects.get(id=res.replacement_vehicle_definition_id)
        self.assertEqual(new_vd.drivetrain, "4WD")
        self.assertEqual(new_vd.slug, "2020-limited-40l-v6-4wd-us")
        self.assertTrue(new_vd.is_active)

    def test_2_old_uuid_and_slug_remain_historically_present(self):
        """2. Old UUID/slug remain historically present in database (with is_active=False)."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        refetched_old = VehicleDefinition.objects.get(id=self.old_pk)
        self.assertEqual(str(refetched_old.uuid), self.old_uuid)
        self.assertEqual(refetched_old.slug, self.old_slug)
        self.assertFalse(refetched_old.is_active)

    def test_3_old_execution_receipt_remains_unchanged(self):
        """3. Old execution receipt remains unchanged."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        refetched_receipt = ImportExecutionReceipt.objects.get(id=self.old_receipt.id)
        self.assertEqual(refetched_receipt.target_slug, self.old_slug)
        self.assertEqual(refetched_receipt.target_drivetrain, "AWD")
        self.assertEqual(refetched_receipt.created_vehicle_definition_id, self.old_pk)

    def test_4_correction_audit_linkage_points_old_to_replacement(self):
        """4. Correction audit linkage points old -> replacement with accurate snapshots."""
        res = execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
            correction_reason=CanonicalRecordCorrection.CorrectionReason.NORMALIZATION_RULE_CORRECTION,
            operator_label="cli:test_corrector",
        )

        corr = CanonicalRecordCorrection.objects.get(uuid=res.correction_audit_uuid)
        self.assertEqual(corr.superseded_vehicle_definition_pk_snapshot, self.old_pk)
        self.assertEqual(corr.superseded_vehicle_definition_uuid_snapshot, self.old_uuid)
        self.assertEqual(corr.superseded_vehicle_definition_slug_snapshot, self.old_slug)
        self.assertEqual(corr.replacement_vehicle_definition_pk_snapshot, res.replacement_vehicle_definition_id)
        self.assertEqual(corr.replacement_vehicle_definition_slug_snapshot, res.replacement_vehicle_definition_slug)

    def test_5_superseded_row_is_excluded_from_active_canonical_matching(self):
        """5. Superseded row is excluded from active canonical matching."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        # Query active records for Limited
        active_lim = VehicleDefinition.objects.filter(
            generation=self.gen,
            trim_name="Limited",
            is_active=True,
        )
        self.assertEqual(active_lim.count(), 1)
        self.assertEqual(active_lim.first().drivetrain, "4WD")

    def test_6_corrected_row_participates_normally_in_exact_match_planning(self):
        """6. Corrected row participates normally in exact-match planning."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        from reference.ingestion.contracts import ArtifactType, Envelope, NormalizedInterpretation
        cand_doc = CandidateConfigurationDocument(
            envelope=Envelope(artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value, schema_version="1.0"),
            candidate_reference="cand_test_4wd",
            candidate_identity=CandidateIdentity(
                manufacturer_name="Toyota",
                vehicle_model_name="4Runner",
                model_year=2020,
                trim_name="Limited",
                market="US",
            ),
            normalized_assertions=[
                NormalizedInterpretation(interpretation_id="interp_1", source_assertion_ref="sa_1", target_attribute_key="make", normalized_concept="Toyota", mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_2", source_assertion_ref="sa_2", target_attribute_key="model", normalized_concept="4Runner", mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_3", source_assertion_ref="sa_3", target_attribute_key="model_year", normalized_concept=2020, mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_4", source_assertion_ref="sa_4", target_attribute_key="trim", normalized_concept="Limited", mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_5", source_assertion_ref="sa_5", target_attribute_key="generic_drive_classification", normalized_concept="4WD", mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_6", source_assertion_ref="sa_6", target_attribute_key="engine_displacement_liters", normalized_concept=4.0, mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_7", source_assertion_ref="sa_7", target_attribute_key="engine_cylinders", normalized_concept=6, mapping_status="mapped"),
                NormalizedInterpretation(interpretation_id="interp_8", source_assertion_ref="sa_8", target_attribute_key="market", normalized_concept="US", mapping_status="mapped"),
            ],
        )

        plan = plan_candidate_import(cand_doc)
        self.assertEqual(plan.planned_action, ImportPlannedAction.NO_OP_EXACT_MATCH)
        self.assertEqual(plan.target_slug, "2020-limited-40l-v6-4wd-us")

    def test_7_superseded_row_does_not_create_stale_namespace_counts(self):
        """7. Superseded row does not create stale namespace counts."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        active_count = VehicleDefinition.objects.filter(
            generation=self.gen,
            model_year=2020,
            market="US",
            is_active=True,
        ).count()
        total_count = VehicleDefinition.objects.filter(
            generation=self.gen,
            model_year=2020,
            market="US",
        ).count()

        self.assertEqual(active_count, 1)  # Only replacement 4WD is active
        self.assertEqual(total_count, 2)   # 1 superseded AWD + 1 active 4WD

    def test_8_correction_is_atomic(self):
        """8. Correction is atomic (rollback on replacement failure)."""
        failing_plan = CanonicalImportPlan(
            candidate_reference="cand_fail",
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
        )

        res = execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=failing_plan,
        )

        self.assertEqual(res.outcome, "FAILED_REPLACEMENT_EXECUTION")
        refetched_old = VehicleDefinition.objects.get(id=self.old_pk)
        self.assertTrue(refetched_old.is_active)  # Old record must remain active on failure!

    def test_9_duplicate_repeated_correction_safely_rejected_or_noop(self):
        """9. Duplicate/repeated correction is safely rejected or becomes an explicit no-op."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        # Attempt repeated correction on now-inactive record
        refetched_old = VehicleDefinition.objects.get(id=self.old_pk)
        res_repeat = execute_canonical_record_correction(
            superseded_vehicle_definition=refetched_old,
            replacement_plan=self.replacement_plan,
        )

        self.assertEqual(res_repeat.outcome, "NO_OP_ALREADY_CORRECTED")

    def test_10_unrelated_canonical_rows_are_untouched(self):
        """10. Unrelated canonical rows are untouched."""
        unrelated_vd = VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            is_active=True,
        )

        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        refetched_unrelated = VehicleDefinition.objects.get(id=unrelated_vd.id)
        self.assertTrue(refetched_unrelated.is_active)
        self.assertEqual(refetched_unrelated.slug, "2020-sr5-40l-v6-2wd-us")

    def test_11_public_canonical_browsing_excludes_superseded_configurations(self):
        """11. Public canonical browsing excludes superseded configurations."""
        execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        response = self.client.get(self.gen.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2020-limited-40l-v6-4wd-us")
        self.assertNotContains(response, "2020-limited-40l-v6-awd-us")

    def test_12_historical_audit_can_retrieve_superseded_identity(self):
        """12. Historical audit can retrieve superseded identity."""
        res = execute_canonical_record_correction(
            superseded_vehicle_definition=self.old_vd,
            replacement_plan=self.replacement_plan,
        )

        superseded_rows = VehicleDefinition.objects.filter(is_active=False)
        self.assertEqual(superseded_rows.count(), 1)
        self.assertEqual(superseded_rows.first().slug, self.old_slug)

        corr_records = CanonicalRecordCorrection.objects.filter(
            superseded_vehicle_definition_pk_snapshot=self.old_pk
        )
        self.assertEqual(corr_records.count(), 1)
        self.assertEqual(corr_records.first().replacement_vehicle_definition_slug_snapshot, res.replacement_vehicle_definition_slug)
