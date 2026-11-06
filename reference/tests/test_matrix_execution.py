import copy
import json
from unittest.mock import patch

from django.test import TestCase

from reference.ingestion.importing.matrix_workflow import (
    MatrixExecutionError, MatrixYear, _references, execute_matrix_year,
)
from reference.ingestion.matrix_approval import MatrixApprovalError, build_matrix_approval
from reference.models import ImportExecutionReceipt, VehicleDefinition
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup


class MatrixExecutionTests(SyntheticWranglerSetup, TestCase):
    def setUp(self):
        super().setUp()
        self.publish()
        self.plan, self.manifest = self.plan_and_manifest()
        evidence, correspondence = _references(self.plan)
        self.row = {
            "row_id": "sport", "model_year": 2018, "target_fields": self.plan.target_vehicle_definition_fields,
            "target_slug": self.plan.target_slug, "action": "create",
            "permitted_create_bases": [self.plan.create_basis.value],
            "candidate_reference": self.plan.candidate_reference, "candidate_digest": self.plan.candidate_hash,
            "evidence": evidence, "correspondence": correspondence, "existing_record": None,
        }
        self.matrix = {
            "matrix_version": "1.0", "model_years": [2018], "market": "US", "rows": [self.row],
            "parents": {
                key: {"pk": record.pk, "uuid": str(record.uuid), "slug": record.slug}
                for key, record in (("manufacturer", self.make), ("vehicle_model", self.model), ("generation", self.jk))
            },
        }
        self.approval = self.approve()
        self.candidates = {self.plan.candidate_reference: self.candidate}

    def approve(self):
        return build_matrix_approval(self.matrix, operator="cli:test", confirmed=True)

    def run_year(self):
        return execute_matrix_year(self.matrix, self.approval, 2018, self.candidates, self.root, execution_operator="cli:executor")

    def test_create_receipt_and_repeat(self):
        _, report = self.run_year()
        self.assertEqual(report["rows"][0]["status"], "newly_created")
        receipt = ImportExecutionReceipt.objects.get(operation_type="vehicle_definition_import")
        self.assertEqual(receipt.resolution_snapshot_json["matrix"]["row_id"], "sport")
        self.assertEqual(receipt.resolution_snapshot_json["matrix"]["matrix_digest"], self.approval["matrix_digest"])
        _, report = self.run_year()
        self.assertEqual(report["rows"][0]["status"], "previously_completed")
        self.assertEqual(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").count(), 1)

    def test_scope_and_tampering(self):
        with self.assertRaises(MatrixExecutionError):
            MatrixYear(self.matrix, self.approval, 2019, self.candidates)
        changed = copy.deepcopy(self.matrix)
        changed["rows"][0]["row_id"] = "substituted"
        with self.assertRaises(MatrixApprovalError):
            MatrixYear(changed, self.approval, 2018, self.candidates)
        self.candidates.clear()
        with self.assertRaises(MatrixExecutionError):
            self.run_year()
        self.assertFalse(VehicleDefinition.objects.exists())

    def test_existing_requires_explicit_review_or_completion_receipt(self):
        outcome, _ = self.execute(self.plan, self.manifest)
        record = VehicleDefinition.objects.get(pk=outcome.vehicle_definition_id)
        with self.assertRaises(MatrixExecutionError):
            self.run_year()
        self.row.update(action="reviewed_existing", permitted_create_bases=[], existing_record={
            "pk": record.pk, "uuid": str(record.uuid), "slug": record.slug,
        })
        self.approval = self.approve()
        _, report = self.run_year()
        self.assertEqual(report["rows"][0]["status"], "reviewed_existing")
        self.assertEqual(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").count(), 1)

    def test_failure_after_import_rolls_back_record_and_receipt_and_allows_retry(self):
        with patch.object(ImportExecutionReceipt, "save", autospec=True) as save:
            # Fail at matrix linkage, after the normal workflow has created both records.
            from django.db.models import Model
            def save_receipt(receipt, *args, **kwargs):
                if kwargs.get("update_fields"):
                    raise RuntimeError("sensitive details")
                return Model.save(receipt, *args, **kwargs)
            save.side_effect = save_receipt
            with self.assertRaises(MatrixExecutionError):
                self.run_year()
        self.assertFalse(VehicleDefinition.objects.exists())
        self.assertFalse(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").exists())
        failure = json.loads(next(self.root.glob("matrix-*/failure.json")).read_text())
        self.assertEqual(failure["rollback"], "transaction_aborted")
        self.assertNotIn("sensitive details", json.dumps(failure))
        self.assertTrue(self.run_year()[1]["complete"])

    def add_row(self, year, designation, drive):
        candidate = self.make_candidate(designation, year=year, drive=drive)
        self.publish(self.review(candidate, start_year=year, end_year=year))
        plan, _ = self.plan_and_manifest(candidate)
        evidence, correspondence = _references(plan)
        row = self.row | {
            "row_id": designation, "model_year": year,
            "target_fields": plan.target_vehicle_definition_fields, "target_slug": plan.target_slug,
            "candidate_reference": plan.candidate_reference, "candidate_digest": plan.candidate_hash,
            "evidence": evidence, "correspondence": correspondence,
        }
        self.matrix["rows"].append(row)
        self.matrix["model_years"] = sorted({*self.matrix["model_years"], year})
        self.candidates[plan.candidate_reference] = candidate
        return row

    def test_same_year_replan_uses_current_mechanical_basis(self):
        second = self.add_row(2018, "second", "2WD")
        second["permitted_create_bases"] = ["first_representation", "mechanical_dimension"]
        self.row["row_id"] = "first"
        self.approval = self.approve()
        _, report = self.run_year()
        self.assertEqual([r["status"] for r in report["rows"]], ["newly_created", "newly_created"])
        self.assertEqual(list(ImportExecutionReceipt.objects.filter(
            operation_type="vehicle_definition_import",
        ).order_by("pk").values_list("create_basis", flat=True)), ["first_representation", "mechanical_dimension"])

    def test_stale_second_row_rolls_back_year_but_preserves_earlier_year(self):
        from reference.ingestion.importing import CanonicalImportResult, ImportExecutionOutcome
        from reference.ingestion.importing.workflow import execute_canonical_import_workflow

        self.jk.start_year = 2017
        self.jk.save(update_fields=["start_year"])
        self.add_row(2017, "earlier", "4WD")
        second = self.add_row(2018, "second", "2WD")
        second["permitted_create_bases"] = ["first_representation", "mechanical_dimension"]
        self.row["row_id"] = "first"
        self.approval = self.approve()
        execute_matrix_year(self.matrix, self.approval, 2017, self.candidates, self.root, execution_operator="cli:executor")

        def execute(plan, manifest, review, **kwargs):
            if plan.candidate_reference == second["candidate_reference"]:
                return CanonicalImportResult(plan.candidate_reference, ImportExecutionOutcome.ABORTED_STALE_PLAN), None
            return execute_canonical_import_workflow(plan, manifest, review, **kwargs)

        with patch("reference.ingestion.importing.matrix_workflow.execute_canonical_import_workflow", side_effect=execute):
            with self.assertRaises(MatrixExecutionError):
                self.run_year()
        self.assertEqual(list(VehicleDefinition.objects.values_list("model_year", flat=True)), [2017])
        self.assertEqual(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").count(), 1)
        failure = json.loads(next(self.root.glob("matrix-2018-*/failure.json")).read_text())
        self.assertEqual(failure["previously_completed_years"], [2017])
        self.assertEqual(failure["row_id"], "second")
        self.assertIn("aborted_stale_plan", failure["reason"])
        self.assertTrue(self.run_year()[1]["complete"])

    def test_commands_require_affirmation_and_dry_run_is_read_only(self):
        from io import StringIO
        from django.core.management import call_command
        from reference.ingestion.serialization import serialize_artifact

        matrix = self.root / "matrix.json"
        approval = self.root / "approval.json"
        candidate = self.root / "candidate.json"
        matrix.write_text(json.dumps(self.matrix))
        candidate.write_text(serialize_artifact(self.candidate))
        with patch("builtins.input", return_value="n"):
            call_command("approve_generation_trim_matrix", matrix=matrix, output=approval, stdout=StringIO())
        self.assertFalse(approval.exists())
        with patch("builtins.input", return_value="yes"):
            call_command("approve_generation_trim_matrix", matrix=matrix, output=approval, operator="director_role", stdout=StringIO())
        self.assertEqual(json.loads(approval.read_text())["operator"], "director_role")
        options = dict(matrix=matrix, approval=approval, candidate=[str(candidate)], year=2018,
                       output_dir=self.root, stdout=StringIO())
        with patch("builtins.input", side_effect=AssertionError("Dry run prompted")):
            call_command("execute_generation_trim_matrix_year", dry_run=True, **options)
        self.assertFalse(VehicleDefinition.objects.exists())
        with patch("builtins.input", return_value="yes"):
            call_command("execute_generation_trim_matrix_year", operator="execution_role", agent="declared_agent", **options)
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        receipt = ImportExecutionReceipt.objects.get(operation_type="vehicle_definition_import")
        self.assertEqual(receipt.operator_label, "execution_role")
        self.assertEqual(receipt.execution_channel, "cli")
        self.assertEqual(receipt.resolution_snapshot_json["attribution"]["execution_agent"], "declared_agent")

    def test_invalid_completion_receipts_conflict(self):
        from django.db import transaction

        self.run_year()
        receipt = ImportExecutionReceipt.objects.get(operation_type="vehicle_definition_import")
        for change in ("duplicate", "duplicate_wrong_slug", "matrix_digest", "row_id", "approval_digest",
                       "deleted", "inactive", "wrong_identity"):
            with self.subTest(change=change), transaction.atomic():
                if change.startswith("duplicate"):
                    duplicate = ImportExecutionReceipt.objects.get(pk=receipt.pk)
                    duplicate.pk = None
                    from uuid import uuid4
                    duplicate.uuid = uuid4()
                    if change == "duplicate_wrong_slug":
                        duplicate.target_slug = "different-slug"
                    duplicate.save(force_insert=True)
                elif change in {"matrix_digest", "row_id", "approval_digest"}:
                    snapshot = copy.deepcopy(receipt.resolution_snapshot_json)
                    snapshot["matrix"][change] = "altered"
                    ImportExecutionReceipt.objects.filter(pk=receipt.pk).update(resolution_snapshot_json=snapshot)
                else:
                    records = VehicleDefinition.objects.filter(pk=receipt.created_vehicle_definition_id)
                    if change == "deleted":
                        records.delete()
                    elif change == "inactive":
                        records.update(is_active=False)
                    else:
                        records.update(trim_name="Different trim")
                report = MatrixYear(self.matrix, self.approval, 2018, self.candidates).status()
                self.assertFalse(report["complete"])
                self.assertEqual(report["rows"][0]["status"], "conflict")
                transaction.set_rollback(True)

    def test_initial_artifact_failure_stops_before_execution(self):
        from reference.ingestion.importing.matrix_workflow import MatrixArtifactsUnavailable

        for target in ("mkdtemp", "write_json", "Path.write_bytes"):
            with self.subTest(target=target), patch(
                f"reference.ingestion.importing.matrix_workflow.{target}", side_effect=PermissionError,
            ):
                with self.assertRaisesRegex(MatrixArtifactsUnavailable, "No canonical execution began.*PermissionError"):
                    self.run_year()
                self.assertFalse(VehicleDefinition.objects.exists())
                self.assertFalse(list(self.root.glob("matrix-*/failure.json")))

    def test_result_write_failure_preserves_committed_rows_and_attribution(self):
        from reference.ingestion.importing.matrix_workflow import MatrixReportingIncomplete, write_json

        def fail_result(path, payload):
            if path.name == "result.json":
                raise OSError("sensitive path")
            write_json(path, payload)

        with patch("reference.ingestion.importing.matrix_workflow.write_json", side_effect=fail_result):
            with self.assertRaisesRegex(MatrixReportingIncomplete, "committed.*Model year: 2018"):
                self.run_year()
        receipt = ImportExecutionReceipt.objects.get(operation_type="vehicle_definition_import")
        self.assertEqual(receipt.operator_label, "cli:executor")
        operators = json.loads(next(self.root.glob("matrix-*/operators.json")).read_text())
        self.assertEqual(operators, {"approval_operator": "cli:test", "execution_operator": "cli:executor", "execution_agent": "codex", "execution_interface": "cli"})
        status = MatrixYear(self.matrix, self.approval, 2018, self.candidates).status()
        self.assertEqual(status["rows"][0]["status"], "previously_completed")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_execution_operator_required(self):
        with self.assertRaisesRegex(MatrixExecutionError, "execution operator"):
            execute_matrix_year(self.matrix, self.approval, 2018, self.candidates, self.root, execution_operator=" ")
        self.assertFalse(VehicleDefinition.objects.exists())
        self.assertFalse(list(self.root.glob("matrix-*")))

    def test_higher_year_can_complete_before_lower_year(self):
        self.jk.start_year = 2017
        self.jk.save(update_fields=["start_year"])
        self.add_row(2017, "lower", "4WD")
        self.approval = self.approve()
        self.run_year()
        _, report = execute_matrix_year(
            self.matrix, self.approval, 2017, self.candidates, self.root, execution_operator="cli:executor",
        )
        self.assertEqual(report["previously_completed_years"], [2018])
        self.assertEqual(report["completed_during_attempt"], [2017])
        self.assertEqual(report["year_statuses"], {2017: "complete", 2018: "complete"})

    def unique_matrix(self):
        candidate = self.make_candidate(None)
        self.jl.is_active = False
        self.jl.save(update_fields=["is_active"])
        plan, _ = self.plan_and_manifest(candidate)
        evidence, correspondence = _references(plan)
        self.assertEqual(plan.generation_resolution["basis"], "unique_year_range")
        self.matrix["matrix_version"] = "2.0"
        self.row.update(
            candidate_reference=plan.candidate_reference, candidate_digest=plan.candidate_hash,
            evidence=evidence, correspondence=correspondence,
            generation_binding={"mode": "unique_deterministic", "strategy": "unique_year_range",
                                "resolution_version": "1.0"},
        )
        self.candidates = {plan.candidate_reference: candidate}
        self.approval = self.approve()

    def test_unique_resolution_executes_and_receipt_detects_changed_strategy(self):
        self.unique_matrix()
        _, report = self.run_year()
        self.assertEqual(report["rows"][0]["generation_binding"]["generation"]["uuid"], str(self.jk.uuid))
        receipt = ImportExecutionReceipt.objects.get(operation_type="vehicle_definition_import")
        self.assertEqual(receipt.resolution_snapshot_json["matrix"]["generation_binding"]["mode"],
                         "unique_deterministic")
        snapshot = receipt.resolution_snapshot_json
        snapshot["generation_resolution"]["basis"] = "reviewed_source_correspondence"
        ImportExecutionReceipt.objects.filter(pk=receipt.pk).update(resolution_snapshot_json=snapshot)
        self.assertEqual(MatrixYear(self.matrix, self.approval, 2018, self.candidates).status()["rows"][0]["status"],
                         "conflict")

    def test_stale_unique_resolution_stops_before_writes(self):
        self.unique_matrix()
        for active in (False, True):
            with self.subTest(overlap=active):
                self.jl.is_active = active
                self.jl.save(update_fields=["is_active"])
                self.jk.is_active = active
                self.jk.save(update_fields=["is_active"])
                with self.assertRaises(MatrixExecutionError):
                    self.run_year()
                self.assertFalse(VehicleDefinition.objects.exists())
                self.assertFalse(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").exists())

    def test_v2_explicit_mode_and_exact_approval(self):
        self.matrix["matrix_version"] = "2.0"
        self.row["generation_binding"] = {
            "mode": "explicit_correspondence", "strategy": "reviewed_source_correspondence",
            "resolution_version": "1.0",
        }
        with self.assertRaises(MatrixApprovalError):
            self.run_year()
        self.approval = self.approve()
        self.assertTrue(self.run_year()[1]["complete"])

    def test_v2_approval_command_rejects_new_overlap_before_prompt(self):
        from io import StringIO
        from django.core.management import CommandError, call_command
        from reference.ingestion.serialization import serialize_artifact

        self.unique_matrix()
        matrix = self.root / "v2.json"
        matrix.write_text(json.dumps(self.matrix))
        candidate = self.root / "candidate.json"
        candidate.write_text(serialize_artifact(next(iter(self.candidates.values()))))
        self.jl.is_active = True
        self.jl.save(update_fields=["is_active"])
        approval = self.root / "approval.json"
        with patch("builtins.input", side_effect=AssertionError("Ambiguous binding prompted")), self.assertRaises(CommandError):
            call_command("approve_generation_trim_matrix", matrix=matrix, candidate=[str(candidate)],
                         output=approval, stdout=StringIO())
        self.assertFalse(approval.exists())

    def test_v2_generation_uuid_change_invalidates_approval(self):
        from uuid import uuid4
        from reference.ingestion.matrix import compute_matrix_digest

        self.unique_matrix()
        digest = compute_matrix_digest(self.matrix)
        self.assertEqual(digest, compute_matrix_digest(copy.deepcopy(self.matrix)))
        self.matrix["parents"]["generation"]["uuid"] = str(uuid4())
        self.assertNotEqual(digest, compute_matrix_digest(self.matrix))
        with self.assertRaises(MatrixApprovalError):
            self.run_year()
        self.approval = self.approve()
        with self.assertRaises(MatrixExecutionError):
            self.run_year()
        self.assertFalse(VehicleDefinition.objects.exists())
