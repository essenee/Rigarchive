"""
Unit and integration tests for Canonical Reference Import Execution & Execution Provenance Workflow (RA-024).

Covers review manifest serialization/hashing/validation, exact plan reconstruction,
single-plan workflow execution, ImportExecutionReceipt audit persistence, CREATED atomicity rollback,
and management CLI commands.
"""

from io import StringIO
import json
import os
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import TestCase

from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportExecutionOutcome,
    ImportPlannedAction,
)
from reference.ingestion.importing.workflow import (
    CanonicalExecutionWorkflowError,
    execute_canonical_import_workflow,
)
from reference.ingestion.manifest import (
    CanonicalImportReviewManifest,
    CanonicalImportReviewPlan,
    ManifestValidationError,
    build_review_manifest,
    compute_manifest_hash,
    dict_to_manifest,
    manifest_to_dict,
    reconstruct_plan_from_manifest,
)
from reference.models import (
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class CanonicalImportExecutionTestCase(TestCase):
    def setUp(self):
        super().setUp()
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
            name="Fifth Generation N280",
            start_year=2010,
            end_year=2024,
            is_active=True,
        )

        self.sample_plan = CanonicalImportPlan(
            candidate_reference="cand_toyota_usa_8664_2020",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.FIRST_REPRESENTATION,
            namespace_snapshot_count=0,
            mechanical_basis_existing_id=None,
            resolved_manufacturer_id=self.manufacturer.id,
            resolved_vehicle_model_id=self.vehicle_model.id,
            resolved_generation_id=self.generation.id,
            target_vehicle_definition_fields={
                "model_year": 2020,
                "trim_name": "SR5",
                "engine_name": "4.0L V6",
                "drivetrain": "2WD",
                "market": "US",
            },
            target_slug="2020-sr5-4-0l-v6-2wd-us",
            existing_vehicle_definition_id=None,
            reasons=["First representation in generation/year/market namespace."],
        )

        self.sample_prov = {
            "extractor_id": "toyota_pressroom_extractor",
            "extractor_version": "0.1.0",
            "extraction_mode": "manually_verified_transcription",
            "raw_artifact_hash": "sha256:a8f9e1c2d3e4f5a8f9e1c2d3e4f5a8f9e1c2d3e4f5a8f9e1c2d3e4f5a8f9e1c2",
            "raw_artifact_reference": "storage/raw_source_artifacts/toyota_usa/a8f9e1c2.html",
        }


class ReviewManifestSerializationTests(CanonicalImportExecutionTestCase):
    def test_manifest_building_and_deterministic_hashing(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )

        self.assertTrue(manifest.manifest_hash.startswith("sha256:"))
        self.assertEqual(len(manifest.manifest_hash), 71)

        d = manifest_to_dict(manifest)
        reparsed = dict_to_manifest(d)
        self.assertEqual(reparsed.manifest_hash, manifest.manifest_hash)

    def test_manifest_hash_independent_of_file_whitespace(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        d = manifest_to_dict(manifest)

        compact_json = json.dumps(d, separators=(",", ":"))
        pretty_json = json.dumps(d, indent=4)

        manifest1 = dict_to_manifest(json.loads(compact_json))
        manifest2 = dict_to_manifest(json.loads(pretty_json))

        self.assertEqual(manifest1.manifest_hash, manifest2.manifest_hash)

    def test_manifest_tampered_value_invalidates_hash(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        d = manifest_to_dict(manifest)

        # Alter target trim name without updating manifest_hash
        d["plans"][0]["target_vehicle_definition_fields"]["trim_name"] = "Limited"

        with self.assertRaises(ManifestValidationError) as cm:
            dict_to_manifest(d)
        self.assertIn("Manifest hash mismatch", str(cm.exception))

    def test_manifest_validation_rules(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        d = manifest_to_dict(manifest)

        # Test unsupported version
        d_bad_ver = dict(d)
        d_bad_ver["manifest_version"] = "99.0"
        d_bad_ver["manifest_hash"] = compute_manifest_hash({k: v for k, v in d_bad_ver.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(d_bad_ver)

        # Test unknown top-level field rejection
        d_unknown = dict(d)
        d_unknown["unapproved_field"] = "hack"
        d_unknown["manifest_hash"] = compute_manifest_hash({k: v for k, v in d_unknown.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError) as cm:
            dict_to_manifest(d_unknown)
        self.assertIn("Unknown top-level fields", str(cm.exception))

    def test_manifest_rejects_bool_in_integer_fields(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        d = manifest_to_dict(manifest)

        # 1. Test resolved_generation_id = True raises ManifestValidationError
        d_bool_gen = json.loads(json.dumps(d))
        d_bool_gen["plans"][0]["resolved_generation_id"] = True
        d_bool_gen["manifest_hash"] = compute_manifest_hash({k: v for k, v in d_bool_gen.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError) as cm1:
            dict_to_manifest(d_bool_gen)
        self.assertIn("resolved_generation_id", str(cm1.exception))
        self.assertIn("must be a strict integer", str(cm1.exception))

        # 2. Test namespace_snapshot_count = False raises ManifestValidationError
        d_bool_count = json.loads(json.dumps(d))
        d_bool_count["plans"][0]["namespace_snapshot_count"] = False
        d_bool_count["manifest_hash"] = compute_manifest_hash({k: v for k, v in d_bool_count.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError) as cm2:
            dict_to_manifest(d_bool_count)
        self.assertIn("namespace_snapshot_count", str(cm2.exception))
        self.assertIn("must be a strict integer", str(cm2.exception))

    def test_plan_exact_round_trip_reconstruction(self):

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        self.assertEqual(reconstructed.candidate_reference, self.sample_plan.candidate_reference)
        self.assertEqual(reconstructed.eligibility_status, self.sample_plan.eligibility_status)
        self.assertEqual(reconstructed.planned_action, self.sample_plan.planned_action)
        self.assertEqual(reconstructed.create_basis, self.sample_plan.create_basis)
        self.assertEqual(reconstructed.resolved_generation_id, self.sample_plan.resolved_generation_id)
        self.assertEqual(reconstructed.target_vehicle_definition_fields, self.sample_plan.target_vehicle_definition_fields)
        self.assertEqual(reconstructed.target_slug, self.sample_plan.target_slug)


class WorkflowExecutionTests(CanonicalImportExecutionTestCase):
    def test_single_plan_execution_created(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        review_plan = manifest.plans[0]
        reconstructed_plan = reconstruct_plan_from_manifest(review_plan)

        result, receipt = execute_canonical_import_workflow(
            plan=reconstructed_plan,
            manifest=manifest,
            review_plan=review_plan,
            operator_label="cli:testuser",
        )

        self.assertEqual(result.outcome, ImportExecutionOutcome.CREATED)
        self.assertIsNotNone(result.vehicle_definition_id)

        # Verify VehicleDefinition creation
        vd = VehicleDefinition.objects.get(id=result.vehicle_definition_id)
        self.assertEqual(vd.trim_name, "SR5")
        self.assertEqual(vd.drivetrain, "2WD")

        # Verify ImportExecutionReceipt persistence
        self.assertEqual(ImportExecutionReceipt.objects.count(), 1)
        self.assertEqual(receipt.execution_outcome, "created")
        self.assertEqual(receipt.operator_label, "cli:testuser")
        self.assertEqual(receipt.manifest_hash, manifest.manifest_hash)
        self.assertEqual(receipt.created_vehicle_definition_id, vd.id)
        self.assertEqual(receipt.created_vehicle_definition_pk_snapshot, vd.id)
        self.assertEqual(receipt.created_vehicle_definition_uuid_snapshot, str(vd.uuid))
        self.assertEqual(receipt.created_vehicle_definition_slug_snapshot, vd.slug)

    def test_single_plan_execution_no_op_exact_match(self):
        # Create pre-existing canonical row
        existing_vd = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
        )

        noop_plan = CanonicalImportPlan(
            candidate_reference="cand_toyota_usa_8664",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.NO_OP_EXACT_MATCH,
            create_basis=None,
            namespace_snapshot_count=1,
            resolved_manufacturer_id=self.manufacturer.id,
            resolved_vehicle_model_id=self.vehicle_model.id,
            resolved_generation_id=self.generation.id,
            target_vehicle_definition_fields={
                "model_year": 2020,
                "trim_name": "SR5",
                "engine_name": "4.0L V6",
                "drivetrain": "2WD",
                "market": "US",
            },
            target_slug=existing_vd.slug,
            existing_vehicle_definition_id=existing_vd.id,
            reasons=["Exact match found in canonical Reference database."],
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[noop_plan],
            native_identifiers={noop_plan.candidate_reference: "8664"},
        )
        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        result, receipt = execute_canonical_import_workflow(
            plan=reconstructed,
            manifest=manifest,
            review_plan=review_plan,
            operator_label="cli:testuser",
        )

        self.assertEqual(result.outcome, ImportExecutionOutcome.NO_OP_EXACT_MATCH)
        self.assertEqual(result.vehicle_definition_id, existing_vd.id)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

        self.assertEqual(receipt.execution_outcome, "no_op_exact_match")
        self.assertEqual(receipt.existing_vehicle_definition_id, existing_vd.id)
        self.assertEqual(receipt.existing_vehicle_definition_pk_snapshot, existing_vd.id)

    def test_stale_first_representation_aborts(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )

        # Create row after manifest planning pass
        VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
        )

        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        result, receipt = execute_canonical_import_workflow(
            plan=reconstructed,
            manifest=manifest,
            review_plan=review_plan,
            operator_label="cli:testuser",
        )

        self.assertEqual(result.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)
        self.assertEqual(receipt.execution_outcome, "aborted_stale_plan")

    def test_created_receipt_atomicity_rollback(self):
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[self.sample_plan],
            native_identifiers={self.sample_plan.candidate_reference: "8664"},
        )
        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        # Mock ImportExecutionReceipt.objects.create to raise DatabaseError
        with patch.object(ImportExecutionReceipt.objects, "create", side_effect=DatabaseError("Disk full error")):
            with self.assertRaises(CanonicalExecutionWorkflowError):
                execute_canonical_import_workflow(
                    plan=reconstructed,
                    manifest=manifest,
                    review_plan=review_plan,
                    operator_label="cli:testuser",
                )

        # Assert clean rollback: 0 VehicleDefinition created, 0 receipts
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_expected_rejected_receipt(self):
        # Invalid model year violating generation bounds triggers executor ValidationError -> REJECTED
        invalid_year_plan = CanonicalImportPlan(
            candidate_reference="cand_toyota_usa_invalid",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.FIRST_REPRESENTATION,
            resolved_manufacturer_id=self.manufacturer.id,
            resolved_vehicle_model_id=self.vehicle_model.id,
            resolved_generation_id=self.generation.id,
            target_vehicle_definition_fields={
                "model_year": 1999,  # Generation start_year is 2010
                "trim_name": "SR5",
                "engine_name": "4.0L V6",
                "drivetrain": "2WD",
                "market": "US",
            },
            target_slug="1999-sr5-40l-v6-2wd-us",
            reasons=["Validation will fail model year bounds."],
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[invalid_year_plan],
            native_identifiers={invalid_year_plan.candidate_reference: "8664"},
        )
        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        result, receipt = execute_canonical_import_workflow(
            plan=reconstructed,
            manifest=manifest,
            review_plan=review_plan,
            operator_label="cli:testuser",
        )

        self.assertEqual(result.outcome, ImportExecutionOutcome.REJECTED)
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 1)
        self.assertEqual(receipt.execution_outcome, "rejected")



class ManagementCommandTests(CanonicalImportExecutionTestCase):
    def test_acquire_command_manifest_output_zero_writes(self):
        fixture_path = (
            "reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.json")

            call_command(
                "acquire_manufacturer_specs",
                "--file", fixture_path,
                "--output-manifest", manifest_path,
            )

            # Verify manifest generated
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            parsed_manifest = dict_to_manifest(manifest_data)
            self.assertEqual(parsed_manifest.source_id, "toyota_usa")
            self.assertEqual(len(parsed_manifest.plans), 12)

            # GUARANTEE: Zero canonical database writes
            self.assertEqual(VehicleDefinition.objects.count(), 0)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_execute_command_single_plan_success(self):
        fixture_path = (
            "reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.json")

            call_command(
                "acquire_manufacturer_specs",
                "--file", fixture_path,
                "--output-manifest", manifest_path,
            )

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_dict = json.load(f)
            manifest = dict_to_manifest(manifest_dict)
            ref_8664 = [p for p in manifest.plans if p.native_identifier == "8664"][0].candidate_reference

            out = StringIO()
            with patch("builtins.input", return_value="y"):
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path,
                    "--plan-ref", ref_8664,
                    stdout=out,
                )

            self.assertIn("CANONICAL PROMOTION SUCCESSFUL: CREATED", out.getvalue())
            self.assertEqual(VehicleDefinition.objects.count(), 1)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 1)

    def test_execute_command_refuses_flag_review_plan(self):
        flag_plan = CanonicalImportPlan(
            candidate_reference="cand_toyota_usa_flagged",
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            target_vehicle_definition_fields={},
            reasons=["Trim distinction requires human review."],
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=self.sample_prov["raw_artifact_hash"],
            raw_artifact_reference=self.sample_prov["raw_artifact_reference"],
            extraction_provenance=self.sample_prov,
            plans=[flag_plan],
            native_identifiers={flag_plan.candidate_reference: "8670"},
        )
        manifest_dict = manifest_to_dict(manifest)

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "flag_manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_dict, f)

            with self.assertRaises(CommandError) as cm:
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path,
                    "--plan-ref", "cand_toyota_usa_flagged",
                )

            self.assertIn("has non-executable planned action", str(cm.exception))
            self.assertEqual(VehicleDefinition.objects.count(), 0)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_execute_command_operator_declines(self):
        fixture_path = (
            "reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.json")

            call_command(
                "acquire_manufacturer_specs",
                "--file", fixture_path,
                "--output-manifest", manifest_path,
            )

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_dict = json.load(f)
            manifest = dict_to_manifest(manifest_dict)
            ref_8664 = [p for p in manifest.plans if p.native_identifier == "8664"][0].candidate_reference

            out = StringIO()
            with patch("builtins.input", return_value="n"):
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path,
                    "--plan-ref", ref_8664,
                    stdout=out,
                )

            self.assertIn("Execution authorization declined", out.getvalue())
            self.assertEqual(VehicleDefinition.objects.count(), 0)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 0)


class MultiCandidate4RunnerControlStudyTests(CanonicalImportExecutionTestCase):
    def test_sequential_4runner_execution_and_stale_behavior(self):
        fixture_path = (
            "reference/tests/fixtures/acquisition/toyota/2020_4runner_specs.json"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path_1 = os.path.join(tmpdir, "manifest_1.json")

            # Step 1: Initial Dry-Run against empty database
            call_command(
                "acquire_manufacturer_specs",
                "--file", fixture_path,
                "--output-manifest", manifest_path_1,
            )

            with open(manifest_path_1, "r", encoding="utf-8") as f:
                m1_data = json.load(f)
            manifest_1 = dict_to_manifest(m1_data)

            ref_8664_plan1 = [p for p in manifest_1.plans if p.native_identifier == "8664"][0].candidate_reference
            ref_8666_plan1 = [p for p in manifest_1.plans if p.native_identifier == "8666"][0].candidate_reference

            # Execute Plan 1 (8664 - SR5 2WD)
            with patch("builtins.input", return_value="y"):
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path_1,
                    "--plan-ref", ref_8664_plan1,
                )
            self.assertEqual(VehicleDefinition.objects.count(), 1)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 1)

            # Step 2: Attempt executing Plan 2 (8666 - SR5 4WD) from OLD manifest (planned against empty namespace)
            out2 = StringIO()
            with patch("builtins.input", return_value="y"):
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path_1,
                    "--plan-ref", ref_8666_plan1,
                    stdout=out2,
                )

            # Plan 2 aborts as stale because namespace is no longer empty
            self.assertIn("ABORTED_STALE_PLAN", out2.getvalue())
            self.assertEqual(VehicleDefinition.objects.count(), 1)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 2)

            # Step 3: Generate fresh manifest against updated database (containing SR5 2WD)
            manifest_path_2 = os.path.join(tmpdir, "manifest_2.json")
            call_command(
                "acquire_manufacturer_specs",
                "--file", fixture_path,
                "--output-manifest", manifest_path_2,
            )

            with open(manifest_path_2, "r", encoding="utf-8") as f:
                manifest2_dict = json.load(f)
            manifest2 = dict_to_manifest(manifest2_dict)

            plan_8664 = [p for p in manifest2.plans if p.native_identifier == "8664"][0]
            plan_8666 = [p for p in manifest2.plans if p.native_identifier == "8666"][0]
            plan_8670 = [p for p in manifest2.plans if p.native_identifier == "8670"][0]

            # 8664 is now NO_OP_EXACT_MATCH
            self.assertEqual(plan_8664.planned_action, "no_op_exact_match")

            # 8666 (SR5 4WD) is now MECHANICAL_DIMENSION CREATE
            self.assertEqual(plan_8666.planned_action, "create")
            self.assertEqual(plan_8666.create_basis, "mechanical_dimension")

            # 8670 (SR5 Premium 2WD - trim difference only) is FLAG_REVIEW
            self.assertEqual(plan_8670.planned_action, "flag_review")

            # Step 4: Execute fresh plan for 8666 (SR5 4WD)
            out3 = StringIO()
            with patch("builtins.input", return_value="y"):
                call_command(
                    "execute_canonical_import",
                    "--manifest", manifest_path_2,
                    "--plan-ref", plan_8666.candidate_reference,
                    stdout=out3,
                )

            self.assertIn("CANONICAL PROMOTION SUCCESSFUL: CREATED", out3.getvalue())
            self.assertEqual(VehicleDefinition.objects.count(), 2)
            self.assertEqual(ImportExecutionReceipt.objects.count(), 3)


