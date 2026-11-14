from copy import deepcopy
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from reference.ingestion import body_import_contracts as c
from reference.ingestion.importing.body_import import build_matrix, build_manifest, execute_body_import_batch
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.models import VehicleDefinition, ImportExecutionReceipt
from reference.tests.body_import_support import BodyImportFixture


class BodyAwareImportTests(TestCase):
    def setUp(self):
        self.fx = BodyImportFixture()
        self.addCleanup(self.fx.close)

    def authorize(self, plans):
        matrix = build_matrix(plans)
        approval = build_matrix_approval(matrix, operator="project-owner", confirmed=True)
        return build_manifest(matrix, approval)

    def execute(self, plans):
        return execute_body_import_batch(self.authorize(plans), plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)

    def test_atomic_sport_door_pair_and_receipt(self):
        plans = [self.fx.plan(key) for key in ("JL24-01", "JL24-11")]
        receipts = self.execute(plans)
        self.assertEqual(VehicleDefinition.objects.count(), 2)
        self.assertEqual({v.trim_name for v in VehicleDefinition.objects.all()}, {"Sport"})
        self.assertEqual(len({v.slug for v in VehicleDefinition.objects.all()}), 2)
        for receipt in receipts:
            c.validate("Receipt3", receipt.resolution_snapshot_json["body_import"])
            self.assertEqual(receipt.operator_label, "project-owner")
            self.assertEqual(receipt.resolution_snapshot_json["body_import"]["execution_agent"], "implementation-agent")

    def test_noop_preserves_vehicle(self):
        self.execute([self.fx.plan()])
        before = list(VehicleDefinition.objects.values())
        plan = self.fx.plan()
        self.assertEqual(plan["action"], "no_op")
        receipt = self.execute([plan])[0]
        self.assertEqual(list(VehicleDefinition.objects.values()), before)
        self.assertEqual(receipt.execution_outcome, "no_op_exact_match")

    def test_missing_parent_assessment(self):
        self.fx.bodies["two-door"].delete()
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "BODY_PARENT_UNAVAILABLE")

    def test_rollback_on_receipt_failure(self):
        plans = [self.fx.plan(key) for key in ("JL24-01", "JL24-11")]
        manifest = self.authorize(plans)
        before = ImportExecutionReceipt.objects.count()
        with patch("reference.ingestion.importing.body_import._persist", side_effect=RuntimeError("isolated failure")), self.assertRaises(RuntimeError):
            execute_body_import_batch(manifest, plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)

    def test_all_31_atomic_release(self):
        candidates, contexts, family = self.fx.release.load()
        from reference.ingestion.importing.body_identity import plan_resolved
        plans = [plan_resolved(candidate, *contexts[key], family, self.fx.release) for key, candidate in sorted(candidates.items())]
        receipts = self.execute(plans)
        self.assertEqual(len(receipts), 31)
        self.assertEqual(VehicleDefinition.objects.count(), 31)
        self.assertEqual(len(set(VehicleDefinition.objects.values_list("slug", flat=True))), 31)

    def test_subset_slug_independence_and_explicit_dispatch(self):
        from reference.candidate_v3 import parse_candidate
        from reference.ingestion.importing.planner import plan_candidate_import
        plan = plan_candidate_import(parse_candidate(self.fx.candidates["JL24-11"]), body_release=self.fx.release)
        self.assertEqual(plan["target_slug"], self.fx.plan("JL24-11")["target_slug"])
        with self.assertRaises(ValidationError):
            plan_candidate_import(parse_candidate(self.fx.candidates["JL24-11"]))

    def test_descriptor_alias_noop(self):
        self.execute([self.fx.plan()])
        vd = VehicleDefinition.objects.get()
        vd.engine_name = "2.0L I4 Turbo (EC1)"
        vd.save(update_fields=["engine_name"])
        plan = self.fx.plan()
        self.assertEqual(plan["action"], "no_op")
        self.assertEqual(plan["target_fields"]["engine_name"], vd.engine_name)

    def test_supported_null_fk_noop_does_not_backfill(self):
        self.execute([self.fx.plan()])
        vd = VehicleDefinition.objects.get()
        vd.factory_body_configuration = None
        vd.save(update_fields=["factory_body_configuration"])
        plan = self.fx.plan()
        self.assertEqual(plan["action"], "no_op")
        self.assertIsNone(plan["target_fields"]["factory_body_configuration_uuid"])
        self.execute([plan])
        vd.refresh_from_db()
        self.assertIsNone(vd.factory_body_configuration_id)

    def test_unassessed_null_overlap_blocks(self):
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2024, trim_name="Sport", engine_name="2.0L I4 Turbo", drivetrain="4WD", market="US", slug="unknown-legacy")
        self.assertEqual(self.fx.plan()["action"], "blocked")

    def test_unrelated_null_peer_not_universal_gate(self):
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2024, trim_name="Other", engine_name="Unknown", drivetrain="4WD", market="US", slug="unrelated-legacy")
        self.assertEqual(self.fx.plan()["action"], "create")

    def test_inactive_equal_peer_blocks(self):
        self.execute([self.fx.plan()])
        VehicleDefinition.objects.update(is_active=False)
        self.assertEqual(self.fx.plan()["action"], "blocked")

    def test_inactive_slug_occupancy_blocks(self):
        plan = self.fx.plan()
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2023, trim_name="Other", slug=plan["target_slug"], is_active=False)
        blocked = self.fx.plan()
        self.assertEqual(blocked["action"], "blocked")
        self.assertEqual(blocked["diagnostics"][0]["code"], "SLUG_OCCUPIED")

    def test_sparse_compatible_body_blocks(self):
        from reference.models import FactoryBodyConfiguration
        FactoryBodyConfiguration.objects.create(generation=self.fx.generation, door_configuration="two-door", body_style="suv")
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "BODY_AMBIGUOUS")

    def test_cross_generation_parent_rejected(self):
        from reference.models import Generation
        other = Generation.objects.create(vehicle_model=self.fx.generation.vehicle_model, name="Other", start_year=2018)
        body = self.fx.bodies["two-door"]
        body.generation = other
        body.save()
        self.assertEqual(self.fx.release.plan("JL24-01")["diagnostics"][0]["code"], "BODY_PARENT_UNAVAILABLE")

    def test_existing_body_execution_explicitly_unsupported(self):
        value = deepcopy(self.fx.candidates["JL24-01"])
        from uuid import uuid4
        value["factory_body"].update(disposition="existing", parent_uuid=str(self.fx.bodies["two-door"].uuid), binding_revision={"revision_uuid": str(uuid4()), "content_hash": "sha256:" + "a" * 64, "applicability_ref": "app"})
        self.fx.write_candidate("JL24-01", value)
        self.assertEqual(self.fx.release.plan("JL24-01")["diagnostics"][0]["code"], "UNSUPPORTED_BODY_MODE")

    def test_missing_source_bytes(self):
        (self.fx.root / "evidence/JL24-01.json").unlink()
        result = self.fx.release.plan("JL24-01")
        self.assertIn(result["diagnostics"][0]["code"], ("UNAVAILABLE_ARTIFACT", "UNRESOLVED_DEPENDENCY"))
        self.assertIsNotNone(result["candidate_hash"])

    def test_family_member_missing(self):
        from reference.ingestion.importing.body_identity import Release
        release = Release(self.fx.paths[:-1], root=self.fx.root)
        self.assertEqual(release.plan("JL24-01")["diagnostics"][0]["code"], "FAMILY_INCOMPLETE")

    def test_quarantined_reference_rejected(self):
        candidate = deepcopy(self.fx.candidates["JL24-01"])
        candidate["candidate_reference"] = "JL24-Q01"
        self.fx.write_candidate("JL24-01", candidate)
        self.assertEqual(self.fx.release.plan("JL24-01")["diagnostics"][0]["code"], "FAMILY_INCOMPLETE")

    def test_source_provisional_values_never_approve_projection(self):
        from reference.ingestion.importing.body_identity import INVENTORY_ROOT, INVENTORIES
        candidate = deepcopy(self.fx.candidates["JL24-01"])
        # Retain fabricated full configuration assertions, point at real provisional
        # CSV bytes, and rehash every local reference: byte hash alone must not accept.
        old = candidate["evidence_documents"][0]["raw_artifact_hash"]
        old_path = candidate["evidence_documents"][0]["raw_artifact_reference"]
        new = INVENTORIES["candidate_inventory.csv"]
        import json
        candidate = json.loads(json.dumps(candidate).replace(old, new).replace(old_path, INVENTORY_ROOT + "candidate_inventory.csv"))
        self.fx.write_candidate("JL24-01", candidate)
        result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertNotEqual(result.get("action"), "create")

    def assert_stale(self, mutate):
        from reference.ingestion.importing.body_import import revalidate
        plans = [self.fx.plan()]
        manifest = self.authorize(plans)
        before_vd, before_receipts = VehicleDefinition.objects.count(), ImportExecutionReceipt.objects.count()
        mutate()
        report = revalidate(manifest, plans, self.fx.release)
        self.assertEqual(report["result"], "stale")
        with self.assertRaises(ValidationError):
            execute_body_import_batch(manifest, plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), before_vd)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before_receipts)

    def test_candidate_hash_drift(self):
        def mutate():
            value = deepcopy(self.fx.candidates["JL24-01"])
            value["envelope"]["generator"] = "isolated changed candidate"
            self.fx.write_candidate("JL24-01", value)
        self.assert_stale(mutate)

    def test_source_evidence_drift(self):
        self.assert_stale(lambda: (self.fx.root / "evidence/JL24-01.json").write_bytes(b"changed"))

    def test_body_edit_drift(self):
        def mutate():
            body = self.fx.bodies["two-door"]
            body.body_style = "suv"
            body.save()
        self.assert_stale(mutate)

    def test_generation_drift(self):
        def mutate():
            gen = self.fx.generation
            gen.notes = "Unrelated note" if hasattr(gen, "notes") else ""
            gen.end_year = 2023
            gen.save()
        self.assert_stale(mutate)

    def test_correspondence_supersession(self):
        from reference.models import GenerationCorrespondenceRevision
        from reference.ingestion.generation_correspondence import publish_correspondence, digest
        from uuid import uuid4
        def mutate():
            old = GenerationCorrespondenceRevision.objects.get(source_id="ra049-isolated-source-JL24-01")
            payload = old.review_payload()
            payload.update(revision_uuid=str(uuid4()), revision_number=2, supersedes_uuid=str(old.uuid), finding="withdrawn")
            revision, _ = publish_correspondence(payload, digest(payload), authorized=True, operator_label="project-owner", execution_agent="implementation-agent")
            self.assertIsNotNone(revision)
        # Supersession itself writes an isolated publication receipt; separately check
        # that execution creates no vehicles or further receipts.
        plans = [self.fx.plan()]
        manifest = self.authorize(plans)
        mutate()
        before = ImportExecutionReceipt.objects.count()
        with self.assertRaises(ValidationError):
            execute_body_import_batch(manifest, plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_peer_set_and_active_state_drift(self):
        self.execute([self.fx.plan("JL24-11")])
        def mutate():
            VehicleDefinition.objects.update(is_active=False)
        self.assert_stale(mutate)

    def test_slug_namespace_drift(self):
        plans = [self.fx.plan()]
        manifest = self.authorize(plans)
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2023, trim_name="Other", slug=plans[0]["target_slug"], is_active=False)
        before = ImportExecutionReceipt.objects.count()
        with self.assertRaises(ValidationError):
            execute_body_import_batch(manifest, plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_family_inventory_drift(self):
        from reference.ingestion.importing.body_identity import INVENTORY_ROOT
        self.assert_stale(lambda: (self.fx.root / (INVENTORY_ROOT + "candidate_inventory.csv")).write_text("changed"))

    def test_review_only_and_unconfirmed_json_rejected(self):
        plan = self.fx.plan()
        manifest = self.authorize([plan])
        for flags in ({}, {"confirmed": True, "review_only": True}):
            with self.subTest(flags=flags), self.assertRaises(ValidationError):
                execute_body_import_batch(manifest, [plan], self.fx.release, operator="project-owner", execution_agent="implementation-agent", **flags)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_authorization_drift_rejected(self):
        plan = self.fx.plan()
        manifest = self.authorize([plan])
        manifest["approval"]["operator"] = "another-owner"
        with self.assertRaises(ValidationError):
            execute_body_import_batch(manifest, [plan], self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_actual_second_receipt_failure_rolls_back_first_vehicle(self):
        plans = [self.fx.plan(key) for key in ("JL24-01", "JL24-11")]
        manifest = self.authorize(plans)
        before = ImportExecutionReceipt.objects.count()
        original = ImportExecutionReceipt.objects.create
        calls = []
        def fail_second(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("Second isolated receipt fails")
            return original(*args, **kwargs)
        with patch.object(ImportExecutionReceipt.objects, "create", side_effect=fail_second), self.assertRaises(RuntimeError):
            execute_body_import_batch(manifest, plans, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)

    def test_later_body_edit_does_not_rewrite_receipt(self):
        receipt = self.execute([self.fx.plan()])[0]
        before = deepcopy(receipt.resolution_snapshot_json)
        body = self.fx.bodies["two-door"]
        body.body_style = "suv"
        body.save()
        receipt.refresh_from_db()
        self.assertEqual(receipt.resolution_snapshot_json, before)
        c.validate("Receipt3", before["body_import"])

    def test_legacy_engine_reader_rejects_version3_receipt(self):
        from reference.ingestion.importing.powertrain_identity import assess_peer
        self.execute([self.fx.plan()])
        with self.assertRaisesMessage(ValidationError, "versioned body-aware reader"):
            assess_peer(VehicleDefinition.objects.get())

    def test_different_powertrain_is_distinct_with_same_body(self):
        self.execute([self.fx.plan("JL24-01")])
        plan = self.fx.plan("JL24-02")
        self.assertEqual(plan["action"], "create")
        self.execute([plan])
        self.assertEqual(VehicleDefinition.objects.count(), 2)
        self.assertEqual(len(set(VehicleDefinition.objects.values_list("factory_body_configuration_id", flat=True))), 1)

    def test_multiple_overlapping_peers_block_without_arbitrary_selection(self):
        self.execute([self.fx.plan()])
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2024, trim_name="Sport", engine_name="2.0L I4 Turbo", drivetrain="4WD", slug="unassessed-duplicate", **self.fx.candidates["JL24-01"]["canonical_powertrain"])
        self.assertEqual(self.fx.plan()["action"], "blocked")

    def test_valid_findings_cannot_be_invented_by_rehashing(self):
        candidate = deepcopy(self.fx.candidates["JL24-01"])
        candidate["normalized_assertions"][0]["normalization"]["id"] = "reviewed_classification"
        self.fx.write_candidate("JL24-01", candidate)
        result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_duplicate_candidate_json_key(self):
        path = self.fx.root / "candidates/JL24-01.json"
        path.write_text(path.read_text().replace('"candidate_reference":', '"candidate_reference":"JL24-Q01","candidate_reference":', 1))
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "DUPLICATE_KEY")

    def test_retained_path_escape_and_symlink_rejected(self):
        from reference.ingestion.importing.body_identity import read_retained
        with self.assertRaises(ValidationError):
            read_retained(self.fx.root, "../db.sqlite3")
        link = self.fx.root / "source-link.json"
        link.symlink_to(self.fx.root / "evidence/JL24-01.json")
        with self.assertRaises(ValidationError):
            read_retained(self.fx.root, "source-link.json")


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import connections, close_old_connections, DatabaseError
from django.test import TransactionTestCase


class BodyImportConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.fx = BodyImportFixture()
        self.addCleanup(self.fx.close)

    def authorize(self, plans):
        matrix = build_matrix(plans)
        return build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))

    def race(self, left, right):
        plans = [[self.fx.plan(left)], [self.fx.plan(right)]]
        manifests = [self.authorize(p) for p in plans]
        barrier = Barrier(2, timeout=15)
        from reference.ingestion.importing import body_import
        original = body_import._persist
        def synchronized(*args, **kwargs):
            barrier.wait()
            return original(*args, **kwargs)
        def execute(index):
            close_old_connections()
            try:
                execute_body_import_batch(manifests[index], plans[index], self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
                return "committed"
            except (DatabaseError, ValidationError):
                return "aborted"
            finally:
                connections.close_all()
        with patch.object(body_import, "_persist", side_effect=synchronized):
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(execute, (0, 1)))
        self.assertLessEqual(outcomes.count("committed"), 1)
        # A retry is a new plan and a new real test confirmation, never old approval.
        for key in (left, right):
            fresh = [self.fx.plan(key)]
            execute_body_import_batch(self.authorize(fresh), fresh, self.fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        return outcomes

    def test_concurrent_identical_creates(self):
        self.race("JL24-01", "JL24-01")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_concurrent_body_distinct_creates(self):
        self.race("JL24-01", "JL24-11")
        self.assertEqual(VehicleDefinition.objects.count(), 2)
        self.assertEqual(len(set(VehicleDefinition.objects.values_list("factory_body_configuration_id", flat=True))), 2)
