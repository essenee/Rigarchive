"""Synthetic protocol tests. No fixture here establishes a real Jeep configuration."""
import copy
import io
import json
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, connections, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from reference.models import (Manufacturer, VehicleModel, Generation, VehicleDefinition,
                              GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt)
from reference.ingestion.contracts import (Envelope, SourceMetadata, SourceApplicability,
    ExtractionProvenance, SourceAssertion, SourceAssertionSet, NormalizedInterpretation,
    TechnicalValue, CandidateIdentity)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.generation_correspondence import (digest, publish_correspondence,
    CorrespondenceReceiptError, resolve_generation, guard_legacy_scope)
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.workflow import execute_canonical_import_workflow, CanonicalExecutionWorkflowError
from reference.ingestion.manifest import (build_review_manifest, manifest_to_dict, dict_to_manifest,
    reconstruct_plan_from_manifest, compute_manifest_hash, ManifestValidationError)
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact


class SyntheticWranglerSetup:
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(BASE_DIR=self.root, MEDIA_ROOT=self.root / "media")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.make = Manufacturer.objects.create(name="Jeep")
        self.model = VehicleModel.objects.create(manufacturer=self.make, name="Wrangler")
        # Both ranges are synthetic one-year test scopes, not historical assertions.
        self.jk = Generation.objects.create(vehicle_model=self.model, name="Synthetic JK", start_year=2018, end_year=2018)
        self.jl = Generation.objects.create(vehicle_model=self.model, name="Synthetic JL", start_year=2018, end_year=2018)
        self.candidate = self.make_candidate("JK")

    def make_candidate(self, designation="JK", second=None):
        fixture = {"synthetic_test_only": True, "make": "Jeep", "model": "Wrangler", "year": 2018,
                   "trim": "Synthetic Sport", "drive": "4WD", "displacement": 3.6,
                   "cylinders": 6, "engine_name": "Synthetic 3.6L V6", "market": "US"}
        if designation is not None:
            fixture["generation_designation"] = designation
        if second:
            fixture["generation_code"] = second
        path = self.root / f"source-{designation}-{second}.json"
        raw = json.dumps(fixture, sort_keys=True).encode()
        path.write_bytes(raw)
        import hashlib
        raw_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
        assertions = [SourceAssertion(k, k, v, source_context=f"synthetic.{k}") for k, v in fixture.items()]
        sas = SourceAssertionSet(
            Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
            SourceMetadata("synthetic_test", native_record_id="row-1",
                source_applicability=SourceApplicability(market="US", applicability_scope="configuration"),
                extraction_provenance=ExtractionProvenance(raw_hash, path.name, "synthetic_fixture", "1.0", "synthetic_test")),
            assertions,
        )
        concepts = {"make": "make", "model": "model", "year": "model_year", "trim": "trim",
                    "drive": "generic_drive_classification", "displacement": "engine_displacement_liters",
                    "cylinders": "engine_cylinders", "engine_name": "engine_name", "market": "market"}
        interps = [NormalizedInterpretation("i-" + k, k, target,
                   TechnicalValue(v, "L", str(v)) if k == "displacement" else v)
                   for k, target in concepts.items() for v in [fixture[k]]]
        return construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler", model_year=2018, market="US", trim_name=fixture["trim"]),
            [sas], interps, schema_version="2.0.0", candidate_reference=f"synthetic-{designation}-{second}",
        )

    def review(self, candidate=None, generation=None, previous=None, **changes):
        candidate = candidate or self.candidate
        identity = candidate.generation_evidence[0]
        payload = {
            "review_version": "1.0", "revision_uuid": str(uuid.uuid4()),
            "correspondence_uuid": str(previous.correspondence_uuid) if previous else str(uuid.uuid4()),
            "revision_number": previous.revision_number + 1 if previous else 1,
            "supersedes_uuid": str(previous.uuid) if previous else None,
            "vehicle_model_uuid": str(self.model.uuid), "generation_uuid": str((generation or self.jk).uuid),
            "source_id": identity["source_id"], "source_namespace": identity["source_namespace"],
            "identity_type": identity["identity_type"], "native_identifier": identity["native_identifier"],
            "market": "US", "start_year": 2018, "end_year": 2018, "restrictions": {},
            "evidence": candidate.evidence_documents, "finding": "established", "reviewer": "synthetic reviewer",
            "reviewed_at": timezone.now().isoformat(), "review_notes": "Synthetic protocol finding only.",
        }
        payload.update(changes)
        return payload

    def publish(self, payload=None):
        payload = payload or self.review()
        return publish_correspondence(payload, digest(payload), authorized=True, operator_label="test")

    def plan_and_manifest(self, candidate=None):
        candidate = candidate or self.candidate
        plan = plan_candidate_import(candidate)
        doc = candidate.evidence_documents[0]
        manifest = build_review_manifest(doc["source_id"], doc["raw_artifact_hash"],
                                         doc["raw_artifact_reference"], doc, [plan])
        return plan, manifest

    def execute(self, plan, manifest):
        return execute_canonical_import_workflow(plan, manifest, manifest.plans[0], operator_label="test")


class CorrespondenceTests(SyntheticWranglerSetup, TestCase):
    def test_retained_synthetic_scenario_fixtures(self):
        folder = Path(__file__).parent / "fixtures" / "ingestion" / "generation_overlap"
        for path in sorted(folder.glob("*.json")):
            with self.subTest(scenario=path.name):
                case = json.loads(path.read_text())
                self.assertTrue(case["synthetic_test_only"])
                candidate = self.make_candidate(case["designation"], case.get("second"))
                if case["expected"].startswith("Synthetic"):
                    target = self.jk if case["designation"] == "JK" else self.jl
                    # Independent correspondence chains created by earlier scenarios are consistent.
                    self.publish(self.review(candidate, target))
                    self.assertEqual(plan_candidate_import(candidate).resolved_generation_id, target.pk)
                elif case.get("invalid_year"):
                    revision, receipt = self.publish(self.review(candidate, start_year=case["invalid_year"]))
                    self.assertIsNone(revision)
                elif case.get("findings"):
                    # Test the chain on a distinct source identity to keep subtests independent.
                    candidate = self.make_candidate("CHAIN")
                    first, _ = self.publish(self.review(candidate))
                    self.publish(self.review(candidate, previous=first, finding="withdrawn"))
                    self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")
                else:
                    self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")

    def test_wrong_market_restriction_and_inactive_parent_block(self):
        self.publish(self.review(market="CA"))
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "flag_review")
        self.publish(self.review(restrictions={"trim_name": "Other"}))
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "flag_review")
        self.make.is_active = False
        self.make.save()
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "reject")

    def test_unlinked_evidence_and_invalid_selector_cannot_publish(self):
        payload = self.review(native_identifier="NOT IN SOURCE")
        with self.assertRaises(ValidationError):
            self.publish(payload)
        candidate = copy.deepcopy(self.candidate)
        candidate.generation_evidence[0]["source_namespace"] = "invented"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")
        candidate = copy.deepcopy(self.candidate)
        candidate.evidence_documents[0]["assertion_set_id"] = "ambiguous|id"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_changed_candidate_source_revision_requires_new_review(self):
        self.publish()
        candidate = copy.deepcopy(self.candidate)
        doc = candidate.evidence_documents[0]
        doc["raw_artifact_hash"] = "sha256:" + "b" * 64
        candidate.evidence_raw_hashes = [doc["raw_artifact_hash"]]
        candidate.generation_evidence[0]["document_hash"] = doc["raw_artifact_hash"]
        for interp in candidate.normalized_assertions:
            interp.source_assertion_ref = interp.source_assertion_ref.replace(
                self.candidate.evidence_documents[0]["raw_artifact_hash"], doc["raw_artifact_hash"])
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")

    def test_new_conflicting_mapping_stales_reviewed_plan(self):
        self.publish()
        plan, manifest = self.plan_and_manifest()
        self.publish(self.review(generation=self.jl))
        result, receipt = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(receipt.execution_outcome, "aborted_stale_plan")

    def test_noop_parent_change_cannot_hide_stale_state(self):
        self.publish()
        plan, manifest = self.plan_and_manifest()
        self.execute(plan, manifest)
        noop, reviewed = self.plan_and_manifest()
        self.jk.is_active = False
        self.jk.save()
        self.assertEqual(self.execute(noop, reviewed)[0].outcome.value, "aborted_stale_plan")

    def test_publication_decline_and_unsupported_versions(self):
        payload = self.review()
        path = self.root / "review.json"
        path.write_text(json.dumps({"review": payload, "content_hash": digest(payload)}))
        with patch("builtins.input", return_value="no"):
            call_command("publish_generation_correspondence", review=str(path), stdout=io.StringIO())
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)
        self.publish()
        _, manifest = self.plan_and_manifest()
        raw = manifest_to_dict(manifest)
        raw["manifest_version"] = "3.0"
        raw["manifest_hash"] = compute_manifest_hash({k: v for k, v in raw.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)

    def test_rejected_source_attempt_has_receipt_without_publication(self):
        payload = self.review()
        source = self.root / payload["evidence"][0]["raw_artifact_reference"]
        source.write_text("tampered retained evidence")
        revision, receipt = self.publish(payload)
        self.assertIsNone(revision)
        self.assertEqual(receipt.execution_outcome, "rejected")
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 1)

    def test_publication_requires_authorization_and_evidence_cannot_escape_root(self):
        payload = self.review()
        with self.assertRaises(ValidationError):
            publish_correspondence(payload, digest(payload))
        payload["evidence"] = copy.deepcopy(payload["evidence"])
        payload["evidence"][0]["raw_artifact_reference"] = "../outside-evidence.json"
        revision, receipt = self.publish(payload)
        self.assertIsNone(revision)
        self.assertEqual(receipt.execution_outcome, "rejected")

    def test_legacy_inspection_safe_execution_and_overlap_refusal(self):
        self.jl.delete()
        from reference.ingestion.importing import CanonicalImportPlan, ImportEligibilityStatus, ImportPlannedAction, ImportCreateBasis
        fields = {"model_year": 2018, "trim_name": "Synthetic Sport", "engine_name": "Synthetic 3.6L V6", "drivetrain": "4WD", "market": "US"}
        vd = VehicleDefinition(generation=self.jk, **fields)
        plan = CanonicalImportPlan("legacy-test", ImportEligibilityStatus.ELIGIBLE, ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.FIRST_REPRESENTATION, resolved_manufacturer_id=self.make.pk,
            resolved_vehicle_model_id=self.model.pk, resolved_generation_id=self.jk.pk,
            target_vehicle_definition_fields=fields, target_slug=vd.build_slug())
        doc = self.candidate.evidence_documents[0]
        manifest = build_review_manifest(doc["source_id"], doc["raw_artifact_hash"], doc["raw_artifact_reference"], doc, [plan])
        self.assertEqual(dict_to_manifest(manifest_to_dict(manifest)).manifest_version, "1.0")
        self.assertEqual(self.execute(plan, manifest)[0].outcome.value, "created")
        Generation.objects.create(vehicle_model=self.model, name="Legacy overlap", start_year=2018)
        self.assertEqual(self.execute(plan, manifest)[0].outcome.value, "aborted_stale_plan")

    def test_manifest_primary_provenance_is_bound_even_with_recomputed_hash(self):
        self.publish()
        _, manifest = self.plan_and_manifest()
        raw = manifest_to_dict(manifest)
        raw["extraction_provenance"]["extractor_id"] = "fabricated_parser"
        raw["manifest_hash"] = compute_manifest_hash({k: v for k, v in raw.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)

    def test_jk_jl_resolve_without_changing_ranges(self):
        before = list(Generation.objects.values("uuid", "start_year", "end_year", "slug"))
        revision, receipt = self.publish()
        self.assertEqual(receipt.operation_type, "correspondence_publication")
        jl = self.make_candidate("JL")
        self.publish(self.review(jl, self.jl))
        self.assertEqual(plan_candidate_import(self.candidate).resolved_generation_id, self.jk.pk)
        self.assertEqual(plan_candidate_import(jl).resolved_generation_id, self.jl.pk)
        self.assertEqual(before, list(Generation.objects.values("uuid", "start_year", "end_year", "slug")))
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_missing_explicit_and_unidentified_overlap(self):
        for candidate in [self.candidate, self.make_candidate(None)]:
            candidate.candidate_identity.generation_name = "Synthetic JK"
            self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")
        self.jl.is_active = False
        self.jl.save()
        self.assertEqual(plan_candidate_import(self.make_candidate(None)).planned_action.value, "create")
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "flag_review")

    def test_conflicting_correspondences_and_source_identities(self):
        self.publish()
        self.publish(self.review(generation=self.jl))
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "flag_review")
        self.assertEqual(plan_candidate_import(self.make_candidate("JK", "JL")).planned_action.value, "flag_review")

    def test_invalid_scope_and_unknown_restrictions(self):
        other = VehicleModel.objects.create(manufacturer=self.make, name="Other")
        target = Generation.objects.create(vehicle_model=other, name="Other", start_year=2018)
        for payload in [self.review(generation=target), self.review(start_year=2017), self.review(restrictions={"body": "guess"})]:
            try:
                revision, receipt = self.publish(payload)
            except ValidationError:
                continue
            self.assertIsNone(revision)
            self.assertEqual(receipt.execution_outcome, "aborted_stale_plan")
        self.assertEqual(Revision.objects.count(), 0)

    def test_append_only_successor_withdrawal_and_no_forks(self):
        first, _ = self.publish()
        for action in [lambda: first.save(), lambda: first.delete(),
                       lambda: Revision.objects.filter(pk=first.pk).update(finding="withdrawn"),
                       lambda: Revision.objects.all().delete()]:
            with self.assertRaises(ValidationError):
                action()
        withdrawal = self.review(previous=first, finding="withdrawn")
        second, _ = self.publish(withdrawal)
        competing, failed = self.publish(self.review(previous=first))
        self.assertIsNone(competing)
        self.assertEqual(failed.execution_outcome, "aborted_stale_plan")
        self.assertEqual(Revision.objects.filter(supersedes=first).count(), 1)
        self.assertEqual(plan_candidate_import(self.candidate).planned_action.value, "flag_review")
        repeat, receipt = self.publish(withdrawal)
        self.assertEqual(repeat, second)
        self.assertEqual(receipt.execution_outcome, "no_op_exact_match")

    def test_candidate_v2_round_trip_and_document_qualified_lineage(self):
        candidate = deserialize_artifact(serialize_artifact(self.candidate))
        self.assertEqual(candidate.generation_evidence, self.candidate.generation_evidence)
        self.assertEqual(candidate.evidence_documents, self.candidate.evidence_documents)
        self.assertTrue(all("|sha256:" in i.source_assertion_ref for i in candidate.normalized_assertions))
        self.publish()
        self.assertEqual(plan_candidate_import(candidate).resolved_generation_id, self.jk.pk)

    def test_two_documents_from_same_publisher_keep_local_ids_separate(self):
        import hashlib
        sets, interps = [], []
        for number in (1, 2):
            path = self.root / f"same-publisher-{number}.txt"
            path.write_text(f"Synthetic document {number}")
            raw_hash = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            set_id = f"section-{number}"
            sets.append(SourceAssertionSet(
                Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
                SourceMetadata("synthetic_test", native_record_id=set_id,
                    extraction_provenance=ExtractionProvenance(raw_hash, path.name, "synthetic", "1.0", "synthetic_test")),
                [SourceAssertion("local-id", "make", "Jeep", "section.make")],
            ))
            interps.append(NormalizedInterpretation(
                "local-interpretation", "local-id", "make", "Jeep",
                unknown_fields={"document_qualifier": f"synthetic_test|{raw_hash}|{set_id}|"},
            ))
        candidate = construct_candidate_configuration(CandidateIdentity("Jeep", "Wrangler"), sets, interps, schema_version="2.0.0")
        self.assertEqual(len(candidate.evidence_documents), 2)
        self.assertEqual(len({i.source_assertion_ref for i in candidate.normalized_assertions}), 2)

    def test_manifest_v2_tampering_and_target_candidate_binding(self):
        self.publish()
        plan, manifest = self.plan_and_manifest()
        self.assertEqual(manifest.manifest_version, "2.0")
        parsed = dict_to_manifest(manifest_to_dict(manifest))
        self.assertEqual(reconstruct_plan_from_manifest(parsed.plans[0]), plan)
        raw = manifest_to_dict(manifest)
        raw["plans"][0]["target_vehicle_definition_fields"]["trim_name"] = "Fabricated"
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)
        raw["manifest_hash"] = compute_manifest_hash({k: v for k, v in raw.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)
        raw = manifest_to_dict(manifest)
        raw["plans"][0]["generation_resolution"]["parents"]["generation_id"] = True
        raw["manifest_hash"] = compute_manifest_hash({k: v for k, v in raw.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)

    def test_exact_authorization_no_replan_create_then_auditable_noop(self):
        self.publish()
        plan, manifest = self.plan_and_manifest()
        with patch("reference.ingestion.importing.planner.plan_candidate_import", side_effect=AssertionError("Replanning forbidden")):
            result, receipt = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "created")
        self.assertEqual(receipt.resolution_snapshot_json["candidate_hash"], plan.candidate_hash)
        original = VehicleDefinition.objects.get()
        identity = (original.uuid, original.slug)
        plan, manifest = self.plan_and_manifest()
        before = ImportExecutionReceipt.objects.count()
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "no_op_exact_match")
        self.assertEqual(ImportExecutionReceipt.objects.count(), before + 1)
        original.refresh_from_db()
        self.assertEqual((original.uuid, original.slug), identity)
        altered = copy.deepcopy(plan)
        from reference.ingestion.importing import ImportCreateBasis
        altered.create_basis = ImportCreateBasis.FIRST_REPRESENTATION
        with self.assertRaises(CanonicalExecutionWorkflowError):
            self.execute(altered, manifest)

    def test_source_change_and_successor_stale_create_and_noop(self):
        revision, _ = self.publish()
        plan, manifest = self.plan_and_manifest()
        self.publish(self.review(previous=revision, finding="withdrawn"))
        result, receipt = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        # A distinct fresh chain with changed bytes is not allowed to recycle the old review.
        path = self.root / self.candidate.evidence_documents[0]["raw_artifact_reference"]
        path.write_text("changed source revision")
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")

    def test_noop_revalidates_parents_and_correspondence(self):
        revision, _ = self.publish()
        plan, manifest = self.plan_and_manifest()
        self.execute(plan, manifest)
        noop, reviewed = self.plan_and_manifest()
        self.publish(self.review(previous=revision, finding="withdrawn"))
        result, receipt = self.execute(noop, reviewed)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_atomic_publication_and_import_receipt_failure(self):
        with patch.object(ImportExecutionReceipt.objects, "create", side_effect=RuntimeError("storage failed")):
            with self.assertRaises(CorrespondenceReceiptError):
                self.publish()
        self.assertEqual(Revision.objects.count(), 0)
        self.publish()
        plan, manifest = self.plan_and_manifest()
        with patch.object(ImportExecutionReceipt.objects, "create", side_effect=RuntimeError("storage failed")):
            with self.assertRaises(CanonicalExecutionWorkflowError):
                self.execute(plan, manifest)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_zero_write_planning_empty_namespace_and_offline_cli(self):
        self.publish()
        def no_writes(execute, sql, params, many, context):
            if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE")):
                raise AssertionError(sql)
            return execute(sql, params, many, context)
        candidate_path = self.root / "candidate.json"
        candidate_path.write_text(serialize_artifact(self.candidate))
        with connection.execute_wrapper(no_writes):
            self.plan_and_manifest()
            call_command("plan_generation_population", manufacturer="Missing", model="Missing", model_year=2018, stdout=io.StringIO())
            call_command("plan_canonical_import", candidate=str(candidate_path), output=str(self.root / "manifest.json"), stdout=io.StringIO())
        self.assertFalse(Manufacturer.objects.filter(name="Missing").exists())

    def test_legacy_guards_before_any_write(self):
        from reference.ingestion.orchestration.generation_bootstrap import GenerationBootstrapOrchestrator
        from reference.ingestion.manifest import PopulationBatchManifest
        from reference.ingestion.importing.correction import execute_canonical_record_correction
        orchestrator = GenerationBootstrapOrchestrator(fixture_dir=self.root)
        manifest = PopulationBatchManifest("synthetic", "Jeep", "Wrangler", "US", 2018, 2018, 0, 0, 0, 0)
        vd = VehicleDefinition.objects.create(generation=self.jk, model_year=2018)
        before = ImportExecutionReceipt.objects.count()
        for operation in [lambda: orchestrator.execute_authorized_batch(manifest),
                          lambda: orchestrator.run_bootstrap_pipeline("Jeep", "Wrangler"),
                          lambda: execute_canonical_record_correction(vd, candidate_document=self.candidate)]:
            with self.assertRaises(ValidationError):
                operation()
        vd.refresh_from_db()
        self.assertTrue(vd.is_active)
        self.assertEqual(ImportExecutionReceipt.objects.count(), before)

    def test_bootstrap_preflights_proposed_taxonomy_and_late_fixture(self):
        from reference.ingestion.orchestration.generation_bootstrap import GenerationBootstrapOrchestrator
        from reference.ingestion.acquisition.wikipedia import GenerationTaxonomy
        from unittest.mock import Mock
        taxes = [GenerationTaxonomy("Synthetic", "Unseeded", "US", n, str(n), str(n), 2018, 2018)
                 for n in (1, 2)]
        wiki = Mock()
        wiki.extract_taxonomies.return_value = taxes
        orchestrator = GenerationBootstrapOrchestrator(wiki_extractor=wiki, fixture_dir=self.root)
        with self.assertRaises(ValidationError):
            orchestrator.run_bootstrap_pipeline("Synthetic", "Unseeded")
        self.assertFalse(Manufacturer.objects.filter(name="Synthetic").exists())
        wiki.extract_taxonomies.return_value = taxes[:1]
        (self.root / "2019_unseeded_configurations.json").write_text(json.dumps({
            "configurations": [{"generation_designation": "unreviewed"}]}))
        with self.assertRaises(ValidationError):
            orchestrator.run_bootstrap_pipeline("Synthetic", "Unseeded")
        self.assertFalse(Manufacturer.objects.filter(name="Synthetic").exists())

    def test_unique_year_toyota_volkswagen_and_overlap_staleness(self):
        for make, model in [("Toyota", "4Runner"), ("Toyota", "Tacoma"), ("Volkswagen", "Touareg")]:
            m, _ = Manufacturer.objects.get_or_create(name=make)
            vm = VehicleModel.objects.create(manufacturer=m, name=model)
            g = Generation.objects.create(vehicle_model=vm, name="Synthetic unambiguous", start_year=2018)
            # The public v2 resolver requires retained assertions to establish absence.
            resolution = resolve_generation(vm, 2018, "US", [], self.make_candidate(None).evidence_documents)
            self.assertEqual(resolution["basis"], "unique_year_range")
            self.assertEqual(resolution["parents"]["generation_id"], g.pk)
        self.jl.delete()
        candidate = self.make_candidate(None)
        plan, manifest = self.plan_and_manifest(candidate)
        Generation.objects.create(vehicle_model=self.model, name="New overlap", start_year=2018)
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")

    def test_unrelated_generation_does_not_stale_explicit_resolution(self):
        self.publish()
        plan, manifest = self.plan_and_manifest()
        Generation.objects.create(vehicle_model=self.model, name="Unrelated", start_year=2020)
        self.assertEqual(self.execute(plan, manifest)[0].outcome.value, "created")


class ConcurrentPublicationTests(SyntheticWranglerSetup, TransactionTestCase):
    def test_two_writers_cannot_publish_competing_successors(self):
        previous, _ = self.publish()
        payloads = [self.review(previous=previous) for _ in range(2)]
        barrier = threading.Barrier(2)
        original = Revision.save
        def synchronized_save(row, *args, **kwargs):
            if row.supersedes_id:
                barrier.wait(timeout=10)
            return original(row, *args, **kwargs)
        def run(payload):
            close_old_connections()
            try:
                return self.publish(payload)[1].execution_outcome
            except CorrespondenceReceiptError:
                # A competing SQLite writer may also prevent durable failure logging.
                return "infrastructure_failure"
            finally:
                connections.close_all()
        with patch.object(Revision, "save", synchronized_save):
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(run, payloads))
        self.assertLessEqual(outcomes.count("created"), 1, outcomes)
        if "created" not in outcomes:
            # SQLite can abort both deferred upgrades. A fresh reviewed attempt is required.
            self.assertEqual(Revision.objects.filter(supersedes=previous).count(), 0)
            self.assertEqual(self.publish(self.review(previous=previous))[1].execution_outcome, "created")
        self.assertEqual(Revision.objects.filter(supersedes=previous).count(), 1)
        self.assertEqual(ImportExecutionReceipt.objects.filter(operation_type="correspondence_publication", execution_outcome="created").count(), 2)
