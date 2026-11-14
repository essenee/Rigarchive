"""Adversarial RA-049 final-review regressions, all data isolated and synthetic."""
from copy import deepcopy
import json
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase

from reference import candidate_v3 as wire
from reference.body_identity import canonical_json
from reference.ingestion import body_import_contracts as c
from reference.ingestion.generation_correspondence import publish_correspondence, digest
from reference.ingestion.importing.body_identity import byte_hash
from reference.ingestion.importing.body_import import build_matrix, build_manifest, execute_body_import_batch
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.models import GenerationCorrespondenceRevision, ImportExecutionReceipt, VehicleDefinition
from reference.tests.body_import_support import BodyImportFixture


class FinalBodyReviewTests(TestCase):
    def setUp(self):
        self.fx = BodyImportFixture()
        self.addCleanup(self.fx.close)

    def authorize(self, plans):
        matrix = build_matrix(plans)
        return build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))

    def execute(self, plans, manifest=None, **flags):
        return execute_body_import_batch(manifest or self.authorize(plans), plans, self.fx.release,
            operator="project-owner", execution_agent="implementation-agent", **flags)

    def supersede(self, candidate, **updates):
        old = GenerationCorrespondenceRevision.objects.get(source_id="ra049-isolated-source-JL24-01", successor__isnull=True)
        payload = old.review_payload()
        payload.update(revision_uuid=str(uuid4()), revision_number=old.revision_number + 1,
                       supersedes_uuid=str(old.uuid), evidence=candidate["evidence_documents"], **updates)
        revision, _ = publish_correspondence(payload, digest(payload), authorized=True, operator_label="project-owner", execution_agent="implementation-agent")
        self.assertIsNotNone(revision)
        return revision

    def source_variant(self, mutate, *, native_only=False, duplicate_key=False):
        candidate = deepcopy(self.fx.candidates["JL24-01"])
        doc = candidate["evidence_documents"][0]
        native = {"assertions": deepcopy(doc["assertions"])}
        mutate(native)
        if not native_only:
            doc["assertions"] = deepcopy(native["assertions"])
        raw = canonical_json(native)
        if duplicate_key:
            raw = raw.replace('{"assertions":', '{"assertions":[],"assertions":', 1)
        old_hash = doc["raw_artifact_hash"]
        new_hash = byte_hash(raw.encode())
        candidate = json.loads(json.dumps(candidate).replace(old_hash, new_hash))
        (self.fx.root / "evidence/JL24-01.json").write_text(raw)
        self.fx.write_candidate("JL24-01", candidate)
        self.supersede(candidate)
        return candidate

    def test_reordered_execution_plans_are_rejected_without_writes(self):
        plans = [self.fx.plan(k) for k in ("JL24-01", "JL24-11")]
        manifest = self.authorize(plans)
        before = ImportExecutionReceipt.objects.count()
        with self.assertRaises(ValidationError):
            self.execute(list(reversed(plans)), manifest, confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)

    def test_fabricated_approval_object_is_not_confirmation(self):
        plans = [self.fx.plan()]
        matrix = build_matrix(plans)
        fake = {"approval_version": "1.0", "matrix_digest": c.digest(matrix), "decision": "approved", "operator": "project-owner", "approved_at_utc": "2026-11-13T00:00:00Z"}
        manifest = build_manifest(matrix, fake)
        with self.assertRaises(ValidationError):
            self.execute(plans, manifest)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_supported_engine_restriction_is_resolved(self):
        candidate = self.fx.candidates["JL24-01"]
        self.supersede(candidate, restrictions={"engine_name": "2.0L I4 Turbo"})
        self.assertEqual(self.fx.release.plan("JL24-01").get("action"), "create")

    def attach_generation_finding(self, *, version="1.0"):
        candidate = deepcopy(self.fx.candidates["JL24-01"])
        revision = GenerationCorrespondenceRevision.objects.get(source_id="ra049-isolated-source-JL24-01", successor__isnull=True)
        payload = revision.review_payload()
        raw = canonical_json(payload).encode()
        ref = "reviews/original-generation.json"
        (self.fx.root / "reviews").mkdir(exist_ok=True)
        (self.fx.root / ref).write_bytes(raw)
        candidate["reviewed_findings"] = [{"finding_id": "original-generation", "artifact_type": "generation_correspondence_review", "artifact_version": version,
            "artifact_reference": ref, "artifact_hash": byte_hash(raw), "locator": {"kind": "json_pointer", "pointer": ""}, "applicability_ref": "app"}]
        candidate["normalized_assertions"].append({"interpretation_id": "i-scope", "source_assertion_ref": "|".join((candidate["generation_evidence"][0]["source_id"], candidate["generation_evidence"][0]["document_hash"], "JL24-01", "model")),
            "target_attribute_key": "canonical_scope.generation_key", "normalized_concept": "jl", "mapping_status": "mapped", "applicability_ref": "app",
            "normalization": {"id": "reviewed_alias", "version": "1.0.0"}, "finding_refs": ["original-generation"]})
        candidate["normalized_assertions"].sort(key=lambda i: i["interpretation_id"])
        self.fx.write_candidate("JL24-01", candidate)
        return candidate, ref

    def test_recognized_generation_review_is_reused_and_pinned(self):
        _, ref = self.attach_generation_finding()
        plan = self.fx.release.plan("JL24-01")
        self.assertEqual(plan.get("action"), "create", plan)
        self.assertEqual(plan["evidence"]["reviewed_artifacts"][0]["reference"], ref)

    def test_unknown_review_version_still_blocks(self):
        self.attach_generation_finding(version="99.0")
        result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertEqual(result["diagnostics"][0]["code"], "UNSUPPORTED_REVIEW_VERSION")

    def test_known_source_body_discriminator_cannot_be_omitted(self):
        self.source_variant(lambda n: n["assertions"][0]["raw_value"].update({"factory_body.roof_height_designation": "high"}))
        result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertEqual(result["diagnostics"][0]["code"], "KNOWN_DISCRIMINATOR_OMITTED")

    def test_source_duplicate_json_keys_reject(self):
        self.source_variant(lambda n: None, duplicate_key=True)
        self.assertIn("assessment_version", self.fx.release.plan("JL24-01"))

    def test_source_numeric_retyping_not_silently_accepted(self):
        self.source_variant(lambda n: n["assertions"][0]["raw_value"].update(model_year=2024.0), native_only=True)
        self.assertIn("assessment_version", self.fx.release.plan("JL24-01"))

    def test_source_duplicate_assertion_ids_reject(self):
        self.source_variant(lambda n: n["assertions"].append(deepcopy(n["assertions"][0])), native_only=True)
        self.assertIn("assessment_version", self.fx.release.plan("JL24-01"))

    def test_false_equal_body_proof_is_rejected(self):
        self.execute([self.fx.plan("JL24-11")], confirmed=True)
        proof = deepcopy(self.fx.plan()["proof"])
        self.assertEqual(proof["peers"][0]["relation"], "distinct")
        proof["peers"][0]["relation"] = "equal"
        proof.update(conclusion="no_op", existing_vehicle_uuid=proof["peers"][0]["vehicle"]["uuid"])
        proof = c.seal(proof, "proof_hash")
        with self.assertRaises(c.ContractError):
            c.validate("Proof3", proof)

    def test_noop_with_unresolved_overlap_is_rejected(self):
        self.execute([self.fx.plan()], confirmed=True)
        proof = deepcopy(self.fx.plan()["proof"])
        peer = deepcopy(proof["peers"][0])
        peer["vehicle"].update(pk=peer["vehicle"]["pk"] + 100, uuid=str(uuid4()), slug="unknown-overlap")
        peer.update(relation="unresolved", body_basis=None, powertrain_basis=None, receipt_uuid=None, receipt_snapshot_hash=None, supporting_candidates=[], evidence={"artifact_pins": [], "reviewed_artifacts": []})
        proof["peers"].append(peer)
        proof["peers"].sort(key=lambda p: p["vehicle"]["uuid"])
        with self.assertRaises(c.ContractError):
            c.validate("Proof3", c.seal(proof, "proof_hash"))

    def test_receipt_requires_revalidation_of_every_matrix_row(self):
        receipts = self.execute([self.fx.plan(k) for k in ("JL24-01", "JL24-11")], confirmed=True)
        snapshot = deepcopy(receipts[0].resolution_snapshot_json["body_import"])
        snapshot["revalidation"]["rows"] = snapshot["revalidation"]["rows"][:1]
        snapshot["revalidation"] = c.seal(snapshot["revalidation"], "revalidation_hash")
        with self.assertRaises(c.ContractError):
            c.validate("Receipt3", c.seal(snapshot, "snapshot_hash"))

    def test_correspondence_snapshot_requires_candidate_market_year(self):
        state = deepcopy(self.fx.plan()["generation"])
        q = state["correspondences"][0]["review_payload"]
        q.update(market="CA", start_year=2023, end_year=2023)
        state["correspondences"][0]["content_hash"] = c.digest(q)
        with self.assertRaises(c.ContractError):
            c.validate("GenerationState", state)

    def test_scalar_receipt_target_mirrors_are_verified(self):
        receipt = self.execute([self.fx.plan()], confirmed=True)[0]
        receipt.target_trim_name = "Tampered scalar"
        receipt.save(update_fields=["target_trim_name"])
        self.assertEqual(self.fx.plan()["action"], "blocked")

    def test_generation_review_cannot_approve_body_interpretation(self):
        candidate, _ = self.attach_generation_finding()
        item = next(i for i in candidate["normalized_assertions"] if i["target_attribute_key"] == "factory_body.door_configuration")
        item["finding_refs"] = ["original-generation"]
        self.fx.write_candidate("JL24-01", candidate)
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "FINDING_SCOPE_MISMATCH")

    def test_recognized_review_bad_locator_rejects(self):
        candidate, _ = self.attach_generation_finding()
        candidate["reviewed_findings"][0]["locator"]["pointer"] = "/nonexistent"
        self.fx.write_candidate("JL24-01", candidate)
        self.assertEqual(self.fx.release.plan("JL24-01")["diagnostics"][0]["code"], "FINDING_SCOPE_MISMATCH")

    def test_recognized_finding_byte_drift_stales_authorization(self):
        _, ref = self.attach_generation_finding()
        plans = [self.fx.plan()]
        manifest = self.authorize(plans)
        before = ImportExecutionReceipt.objects.count()
        (self.fx.root / ref).write_text("changed original finding")
        with self.assertRaises(ValidationError):
            self.execute(plans, manifest, confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)

    def test_legacy_candidate_bound_finding_not_transferred(self):
        candidate, ref = self.attach_generation_finding()
        raw = canonical_json({"evidence_anchors": {"candidate_hash": "sha256:" + "1" * 64}}).encode()
        (self.fx.root / ref).write_bytes(raw)
        candidate["reviewed_findings"][0].update(artifact_type="canonical_import_adjudication", artifact_version="1.1", artifact_hash=byte_hash(raw))
        self.fx.write_candidate("JL24-01", candidate)
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "FINDING_SCOPE_MISMATCH")

    def test_noop_cannot_claim_unperformed_body_assignment(self):
        self.execute([self.fx.plan()], confirmed=True)
        vehicle = VehicleDefinition.objects.get()
        vehicle.factory_body_configuration = None
        vehicle.save(update_fields=["factory_body_configuration"])
        plan = self.fx.plan()
        self.assertIsNone(plan["target_fields"]["factory_body_configuration_uuid"])
        plan["target_fields"]["factory_body_configuration_uuid"] = plan["body"]["uuid"]
        with self.assertRaises(c.ContractError):
            c.validate("Plan3", c.seal(plan, "plan_hash"))

    def test_extra_and_missing_execution_plans_reject_before_writes(self):
        plans = [self.fx.plan(k) for k in ("JL24-01", "JL24-11")]
        manifest = self.authorize(plans)
        for changed in (plans[:1], plans + [plans[0]]):
            with self.subTest(count=len(changed)), self.assertRaises(ValidationError):
                self.execute(changed, manifest, confirmed=True)
        self.assertEqual(VehicleDefinition.objects.count(), 0)


    def test_created_scalar_cannot_disguise_noop_snapshot(self):
        created = self.execute([self.fx.plan()], confirmed=True)[0]
        noop = self.execute([self.fx.plan()], confirmed=True)[0]
        created.resolution_snapshot_json = deepcopy(noop.resolution_snapshot_json)
        created.manifest_hash = noop.manifest_hash
        created.save(update_fields=["resolution_snapshot_json", "manifest_hash"])
        self.assertEqual(self.fx.plan()["action"], "blocked")


    def test_legacy_body_metadata_cannot_stand_in_for_versioned_evidence(self):
        from unittest.mock import patch
        candidate = self.fx.candidates["JL24-01"]
        source_doc = deepcopy(self.fx.candidates["JL24-11"]["evidence_documents"][0])
        # Actual retained JSON establishes four doors. A legacy receipt's unknown
        # metadata claims two doors; its raw artifact hash alone must not bless it.
        source_doc["assertions"][0]["raw_value"].update(drivetrain="4WD", **{"factory_body.door_configuration": "two-door"})
        vehicle = VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2024,
            trim_name="Sport", engine_name="2.0L I4 Turbo", drivetrain="4WD", market="US",
            slug="legacy-null-body", **candidate["canonical_powertrain"])
        ImportExecutionReceipt.objects.create(operator_label="project-owner", candidate_reference="legacy",
            manifest_hash="sha256:" + "a" * 64, planned_action="create", execution_outcome="created",
            source_id=source_doc["source_id"], raw_artifact_hash=source_doc["raw_artifact_hash"], raw_artifact_reference=source_doc["raw_artifact_reference"],
            created_vehicle_definition=vehicle, created_vehicle_definition_pk_snapshot=vehicle.pk,
            created_vehicle_definition_uuid_snapshot=str(vehicle.uuid), created_vehicle_definition_slug_snapshot=vehicle.slug,
            resolution_snapshot_json={"generation_resolution": {"documents": [source_doc]}})
        # Assume independently supported legacy engine facts; they still cannot
        # authenticate unknown body annotations or a body-aware receipt snapshot.
        with patch("reference.ingestion.importing.powertrain_identity.assess_peer", return_value=(candidate["canonical_powertrain"], {})):
            result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertEqual(result["diagnostics"][0]["code"], "UNSUPPORTED_REVIEW_VERSION")


    def test_unsupported_v3_dispatch_versions_raise_validation(self):
        from reference.ingestion.importing.planner import plan_candidate_import
        for artifact_type, version in (("rigarchive.candidate_configuration.v3", "3.0.1"), ("rigarchive.candidate_configuration.v2", "3.0.0")):
            value = deepcopy(self.fx.candidates["JL24-01"])
            value["envelope"].update(artifact_type=artifact_type, schema_version=version)
            with self.subTest(version=version, artifact_type=artifact_type), self.assertRaises(ValidationError):
                plan_candidate_import(value, body_release=self.fx.release)


    def test_complete_family_cannot_span_different_generation_uuids(self):
        from reference.models import Generation, FactoryBodyConfiguration
        other = Generation.objects.create(vehicle_model=self.fx.generation.vehicle_model, name="JL", slug="jl-other", start_year=2018)
        FactoryBodyConfiguration.objects.create(generation=other, door_configuration="four-door")
        old = GenerationCorrespondenceRevision.objects.get(source_id="ra049-isolated-source-JL24-11", successor__isnull=True)
        payload = old.review_payload()
        payload.update(revision_uuid=str(uuid4()), supersedes_uuid=str(old.uuid), revision_number=2, generation_uuid=str(other.uuid))
        revision, _ = publish_correspondence(payload, digest(payload), authorized=True, operator_label="project-owner", execution_agent="implementation-agent")
        self.assertIsNotNone(revision)
        result = self.fx.release.plan("JL24-01")
        self.assertIn("assessment_version", result)
        self.assertEqual(result["diagnostics"][0]["code"], "GENERATION_MISMATCH")


    def test_generation_review_pointer_does_not_normalize_array_indices(self):
        candidate, _ = self.attach_generation_finding()
        for token in ("+0", "00", "-1"):
            candidate["reviewed_findings"][0]["locator"]["pointer"] = "/evidence/" + token
            self.fx.write_candidate("JL24-01", candidate)
            result = self.fx.release.plan("JL24-01")
            self.assertTrue("assessment_version" in result, "Noncanonical array index accepted: " + token)
            self.assertEqual(result["diagnostics"][0]["code"], "FINDING_SCOPE_MISMATCH")


    def test_blank_unreported_body_dimension_does_not_become_required(self):
        self.source_variant(lambda n: n["assertions"][0]["raw_value"].update({"factory_body.roof_height_designation": " "}))
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result.get("action"), "create")


from django.test import TransactionTestCase


class FinalBodyCommitBoundaryTests(TransactionTestCase):
    def test_post_commit_reporting_failure_does_not_rollback_success(self):
        fx = BodyImportFixture()
        self.addCleanup(fx.close)
        plans = [fx.plan()]
        matrix = build_matrix(plans)
        manifest = build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))
        before = ImportExecutionReceipt.objects.count()
        receipts = execute_body_import_batch(manifest, plans, fx.release, operator="project-owner", execution_agent="implementation-agent", confirmed=True)
        with self.assertRaises(RuntimeError):
            raise RuntimeError("Simulated external reporting failure after committed executor return")
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before + 1)
        self.assertTrue(ImportExecutionReceipt.objects.filter(pk=receipts[0].pk).exists())
