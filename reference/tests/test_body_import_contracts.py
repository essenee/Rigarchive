from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json

from django.test import TestCase, SimpleTestCase

from reference.ingestion import body_import_contracts as c
from reference.ingestion.importing.body_import import build_matrix, build_manifest
from reference.ingestion.importing.body_identity import family_slugs, SCOPE
from reference.ingestion.matrix_approval import build_matrix_approval, MatrixApprovalError
from reference.tests.body_import_support import BodyImportFixture, REPOSITORY


class BodyContractPrimitiveTests(SimpleTestCase):
    def test_body_tuple_pair_and_token_validation(self):
        good = {k: "two-door" if k == "door_configuration" else None for k in c.ATTRIBUTES}
        c.validate("BodyTuple", good)
        for key, value in (("door_configuration", True), ("door_configuration", "Two Door"), ("door_configuration", 2), ("body_code", "jl"), ("body_code_namespace", "jeep")):
            bad = good | {key: value}
            with self.subTest(key=key, value=value), self.assertRaises(c.ContractError):
                c.validate("BodyTuple", bad)

    def test_closed_and_empty_body_tuple(self):
        for obj in ({k: None for k in c.ATTRIBUTES}, {}, {**{k: None for k in c.ATTRIBUTES}, "other": None}):
            with self.subTest(obj=obj), self.assertRaises(c.ContractError):
                c.validate("BodyTuple", obj)

    def test_reject_duplicate_json_keys(self):
        with self.assertRaises(c.ContractError):
            c.parse("Parent", '{"pk":1,"pk":2,"uuid":"x"}')

    def test_no_nonfinite_or_boolean_integer(self):
        for value in (True, 1.0, float("nan"), float("inf"), -1, 0):
            with self.subTest(value=value), self.assertRaises(c.ContractError):
                c.validate("Int", value)

    def test_reject_noncanonical_timestamps(self):
        for value in ("2026-11-13T00:00:00+00:00", "2026-11-13T00:00:00.000Z", "2026-02-30T00:00:00Z"):
            with self.subTest(value=value), self.assertRaises(c.ContractError):
                c.validate("Timestamp", value)
        c.validate("Timestamp", "2026-11-13T00:00:00Z")

    def test_canonical_powertrain_no_float_or_noncanonical_decimal(self):
        good = {"engine_displacement_liters": "2", "engine_cylinders": 4, "engine_aspiration": "turbocharged", "fuel_type": "gasoline", "electrification_type": "none"}
        for obj in (good | {"engine_displacement_liters": "2.00"}, good | {"engine_displacement_liters": 2.0}, good | {"engine_cylinders": True}, good | {"extra": None}):
            with self.subTest(obj=obj), self.assertRaises(c.ContractError):
                c.validate("Powertrain", obj)

    def test_unsupported_review_reader(self):
        with self.assertRaisesMessage(c.ContractError, "UNSUPPORTED_REVIEW_VERSION"):
            c.validate("ReviewedArtifact", {"reference": "review.json", "byte_hash": "sha256:" + "a" * 64, "reader": "invented-review", "reader_version": "1", "snapshot": {}})

    def test_slug_length_boundary_and_residual_collision(self):
        member = {"candidate_reference": "one", "legacy_base_slug": "a" * 180, "body_attributes": {"door_configuration": "two-door"}}
        self.assertEqual(family_slugs([member])["one"], "a" * 180)
        with self.assertRaises(ValidationError):
            family_slugs([member | {"legacy_base_slug": "a" * 181}])
        with self.assertRaises(ValidationError):
            family_slugs([member, member | {"candidate_reference": "two"}])

    def test_frozen_candidate_fixtures(self):
        from reference.candidate_v3 import parse_candidate, candidate_hash
        for path in sorted((REPOSITORY / "reference/tests/fixtures/ingestion/candidate_v3").glob("*.json")):
            original = path.read_bytes()
            doc = parse_candidate(original.decode()).to_dict()
            self.assertEqual(doc["candidate_hash"], candidate_hash(doc))
            self.assertEqual(path.read_bytes(), original)


from django.core.exceptions import ValidationError


class BodyContractGraphTests(TestCase):
    def setUp(self):
        self.fx = BodyImportFixture()
        self.addCleanup(self.fx.close)
        self.plan = self.fx.plan()

    def test_all_closed_contract_nodes_validate(self):
        p = self.plan
        nodes = {"Plan3": p, "Proof3": p["proof"], "BodyState": p["body"], "BodyTuple": p["body"]["attributes"], "GenerationState": p["generation"], "ScopeResolution": p["generation"]["scope"],
                 "FamilyState": p["proof"]["family"], "FamilyMember": p["proof"]["family"]["release_members"][0], "EvidenceState": p["evidence"], "CorrespondenceState": p["generation"]["correspondences"][0], "TargetFields": p["target_fields"], "ArtifactPin": p["evidence"]["artifact_pins"][0]}
        for kind, value in nodes.items():
            with self.subTest(kind=kind):
                self.assertEqual(c.parse(kind, c.serialize(kind, value)), value)
                with self.assertRaises(c.ContractError):
                    c.validate(kind, value | {"extra": None})

    def test_nested_hash_drift_not_repaired(self):
        bad = deepcopy(self.plan)
        bad["body"]["attributes"]["door_configuration"] = "four-door"
        bad = c.seal(bad, "plan_hash")
        with self.assertRaises(c.ContractError):
            c.validate("Plan3", bad)

    def test_noncanonical_array_order_and_duplicate_subjects(self):
        for members in (list(reversed(self.plan["proof"]["family"]["release_members"])), [self.plan["proof"]["family"]["release_members"][0]] * 31):
            bad = deepcopy(self.plan["proof"]["family"])
            bad["release_members"] = members
            with self.assertRaises(c.ContractError):
                c.validate("FamilyState", bad)

    def test_all_31_slugs_and_ten_vectors(self):
        family = self.plan["proof"]["family"]
        slugs = family_slugs(family["release_members"])
        self.assertEqual(len(slugs), 31)
        self.assertEqual(len(set(slugs.values())), 31)
        self.assertEqual(slugs, family_slugs(list(reversed(family["release_members"]))))
        import csv
        rows = list(csv.DictReader((REPOSITORY / "docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/trim_normalization_audit.csv").open()))
        groups = {}
        for row in rows:
            if row["scope_status_unchanged"] == "ACTIVE_CONSUMER":
                groups.setdefault(row["hypothetical_normalized_slug"], []).append(row)
        pairs = 0
        for base, group in groups.items():
            pairs += len(group) == 2
            for row in group:
                self.assertEqual(slugs[row["candidate_id"]], base + ("-" + row["body_style"] if len(group) == 2 else ""))
        self.assertEqual(pairs, 10)

    def test_matrix_approval_and_manifest_exact_hashes(self):
        matrix = build_matrix([self.plan])
        approval = build_matrix_approval(matrix, operator="project-owner", confirmed=True, approved_at=datetime(2026, 11, 13, tzinfo=timezone.utc))
        manifest = build_manifest(matrix, approval)
        self.assertEqual(c.parse("Manifest3", c.serialize("Manifest3", manifest)), manifest)
        bad = deepcopy(manifest)
        bad["matrix"]["rows"][0]["target_slug"] += "-tampered"
        bad = c.seal(bad, "manifest_hash")
        with self.assertRaises(c.ContractError):
            c.validate("Manifest3", bad)

    def test_approval_requires_real_confirmation_boundary(self):
        with self.assertRaises(MatrixApprovalError):
            build_matrix_approval(build_matrix([self.plan]), operator="project-owner", confirmed=False)

    def test_no_uuid_minted_by_planning(self):
        from unittest.mock import patch
        with patch("django.db.models.UUIDField.get_default", side_effect=AssertionError("No planning UUIDs")):
            self.fx.plan()

    def test_existing_matrix_manifest_dispatch_and_legacy_execution_guards(self):
        from reference.ingestion.matrix import validate_matrix, canonical_matrix_payload, compute_matrix_digest
        from reference.ingestion.manifest import dict_to_manifest, manifest_to_dict
        from reference.ingestion.importing.matrix_workflow import MatrixYear, MatrixExecutionError
        from reference.ingestion.importing.importer import execute_candidate_import
        from reference.ingestion.importing.workflow import execute_canonical_import_workflow, CanonicalExecutionWorkflowError
        matrix = build_matrix([self.plan])
        validate_matrix(matrix)
        self.assertEqual(canonical_matrix_payload(matrix), matrix)
        self.assertEqual(compute_matrix_digest(matrix), c.digest(matrix))
        manifest = build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))
        self.assertEqual(manifest_to_dict(dict_to_manifest(manifest)), manifest)
        with self.assertRaises(MatrixExecutionError):
            MatrixYear(matrix, manifest["approval"], 2024, {})
        with self.assertRaises(ValidationError):
            execute_candidate_import(self.plan)
        with self.assertRaises(CanonicalExecutionWorkflowError):
            execute_canonical_import_workflow(self.plan, manifest, {})

    def test_pending_classification_is_not_promoted(self):
        value = deepcopy(self.fx.candidates["JL24-01"])
        value["reconciliation_and_review"] = {"requires_human_review": True, "review_workflow_disposition": "pending_review", "attribute_states": {"fuel_type": {"reconciliation_state": "incomplete", "review_disposition": "pending_review"}}}
        self.fx.write_candidate("JL24-01", value)
        result = self.fx.release.plan("JL24-01")
        self.assertEqual(result["diagnostics"][0]["code"], "UNRESOLVED_REVIEW")

    def test_body_timestamp_drift_invalidates_exact_plan(self):
        from reference.ingestion.importing.body_import import revalidate
        plans = [self.plan]
        matrix = build_matrix(plans)
        manifest = build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))
        self.fx.bodies["two-door"].save()
        self.assertEqual(revalidate(manifest, plans, self.fx.release)["result"], "stale")

    def test_new_peer_invalidates_prior_authorization(self):
        from reference.ingestion.importing.body_import import revalidate
        matrix = build_matrix([self.plan])
        manifest = build_manifest(matrix, build_matrix_approval(matrix, operator="project-owner", confirmed=True))
        from reference.models import VehicleDefinition
        VehicleDefinition.objects.create(generation=self.fx.generation, model_year=2024, trim_name="Other", drivetrain="4WD", slug="new-peer")
        self.assertEqual(revalidate(manifest, [self.plan], self.fx.release)["result"], "stale")
