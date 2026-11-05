"""Authentic Unlimited evidence with isolated, test-only planning state."""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from reference.ingestion.acquisition.jeep import JK_UNLIMITED_SPORT_HASH, extract_jk_unlimited_sport
from reference.ingestion.acquisition.snapshots import snapshot_metadata_from_dict
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity
from reference.ingestion.generation_correspondence import revalidate_resolution
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.manifest import (
    ManifestValidationError, build_review_manifest, compute_manifest_hash, dict_to_manifest, manifest_to_dict,
    reconstruct_plan_from_manifest,
)
from reference.ingestion.normalization.jeep import normalize_jeep
from reference.ingestion.serialization import deserialize_artifact, serialize_artifact
from reference.models import (
    Generation, GenerationCorrespondenceRevision, ImportExecutionReceipt,
    Manufacturer, VehicleDefinition, VehicleModel,
)

FIXED_TIME = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
SLUG = "2018-unlimited-sport-36l-v6-4wd-us"
TARGET = dict(model_year=2018, trim_name="Unlimited Sport", engine_name="3.6L V6",
              drivetrain="4WD", market="US")


class JKStage3Tests(TestCase):
    def setUp(self):
        super().setUp()
        folder = settings.BASE_DIR / "storage/raw_source_artifacts/jeep_usa"
        stem = JK_UNLIMITED_SPORT_HASH.removeprefix("sha256:")
        pdf, sidecar = folder / f"{stem}.pdf", folder / f"{stem}.meta.json"
        w1 = settings.BASE_DIR / "storage/acquisition_inputs/jeep_2018/w1_applicability_review_20261104T163800Z"
        if not all(p.is_file() for p in (pdf, sidecar, w1 / "jk_assertions.json",
                                         w1 / "jk_proposed_correspondence_revision.json")):
            self.skipTest("Authentic Stage 1 or retained W1 correspondence evidence unavailable.")
        self.source = extract_jk_unlimited_sport(
            pdf.read_bytes(), snapshot_metadata_from_dict(json.loads(sidecar.read_text())),
        )
        self.interpretations = normalize_jeep(self.source)
        self.w1_source = deserialize_artifact((w1 / "jk_assertions.json").read_text())
        self.w1 = json.loads((w1 / "jk_proposed_correspondence_revision.json").read_text())
        review = self.w1["review"]
        make = Manufacturer.objects.create(pk=20, name="Jeep")
        self.model = VehicleModel.objects.create(
            pk=21, uuid=review["vehicle_model_uuid"], manufacturer=make, name="Wrangler",
        )
        self.jk = Generation.objects.create(pk=31, uuid=review["generation_uuid"],
            vehicle_model=self.model, name="JK", start_year=2007, end_year=2018)
        self.jl = Generation.objects.create(pk=32, uuid="38d3c3ac-f825-4406-abb5-c2d12b9129a4",
            vehicle_model=self.model, name="JL", start_year=2018)
        for pk, generation, uuid in (
            (714, self.jk, "edf85ecf-568a-4d8a-b1b2-936e0a4f49e3"),
            (715, self.jl, "9bad2422-3c20-4e72-a52b-280080026472"),
        ):
            VehicleDefinition.objects.create(pk=pk, uuid=uuid, generation=generation,
                                             **(TARGET | {"trim_name": "Sport"}))
        # Serialization sorted the W1 source assertions. The correspondence
        # pins the reviewed order, so recover that order without editing any
        # assertion IDs, values, locations, or provenance.
        indexed = {row.assertion_id: row for row in self.w1_source.source_assertions}
        order = [row["assertion_id"] for row in review["evidence"][0]["assertions"]]
        self.assertEqual(set(indexed), set(order))
        self.w1_review_order = replace(self.w1_source, source_assertions=[indexed[key] for key in order])

    def tearDown(self):
        self.assertFalse(ImportExecutionReceipt.objects.exists())
        super().tearDown()

    def candidate(self, source=None, *, supporting=()):
        return construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler", model_year=2018, market="US", trim_name="Unlimited Sport"),
            [source or self.source, *supporting], self.interpretations,
            schema_version="2.0.0", candidate_reference="offline-jk-unlimited-sport",
            created_at=FIXED_TIME.isoformat(),
        )

    def revision(self, evidence, *, previous=None, **changes):
        return GenerationCorrespondenceRevision.objects.create(**(dict(
            vehicle_model=self.model, generation=self.jk, source_id="jeep_usa",
            source_namespace="generation_designation", identity_type="generation_designation",
            native_identifier="JK", market="US", start_year=2018, end_year=2018,
            evidence=evidence, finding="established", reviewer="Offline test fixture",
            reviewed_at=FIXED_TIME, review_notes="Synthetic resolver state only.",
        ) | (dict(supersedes=previous, correspondence_uuid=previous.correspondence_uuid,
                  revision_number=previous.revision_number + 1) if previous else {}) | changes))

    def seed_w1(self):
        r = self.w1["review"]
        fixture = self.revision(
            r["evidence"], uuid=r["revision_uuid"], correspondence_uuid=r["correspondence_uuid"],
            reviewer=r["reviewer"], reviewed_at=datetime.fromisoformat(r["reviewed_at"]),
            review_notes=r["review_notes"], restrictions=r["restrictions"],
            content_hash=self.w1["content_hash"],
        )
        self.assertEqual(fixture.review_payload(), r)
        return fixture

    def assert_create(self, plan):
        self.assertEqual((plan.eligibility_status.value, plan.planned_action.value,
                          plan.create_basis.value if plan.create_basis else None),
                         ("eligible", "create", "source_established_grade"))
        self.assertEqual(plan.resolved_generation_id, self.jk.pk)
        self.assertEqual(plan.target_vehicle_definition_fields, TARGET)
        self.assertEqual(plan.target_slug, SLUG)
        self.assertIsNone(plan.existing_vehicle_definition_id)
        self.assertEqual(plan.namespace_snapshot_count, 1)

    def assert_blocked(self, candidate, reason):
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action.value, "flag_review")
        self.assertIn(reason, " ".join(plan.reasons))

    def manifest(self, candidate, plan):
        doc = candidate.evidence_documents[0]
        with patch("reference.ingestion.manifest.datetime", wraps=datetime) as clock:
            clock.now.return_value = FIXED_TIME
            return manifest_to_dict(build_review_manifest(
                doc["source_id"], doc["raw_artifact_hash"], doc["raw_artifact_reference"], doc, [plan],
            ))

    def test_exact_w1_document_supports_unlimited_without_lending_configuration_facts(self):
        self.seed_w1()
        self.assert_blocked(self.candidate(), "does not match candidate evidence")
        self.assert_blocked(self.candidate(supporting=(self.w1_source,)), "does not match candidate evidence")
        candidate = self.candidate(supporting=(self.w1_review_order,))
        self.assertEqual(candidate.envelope.schema_version, "2.0.0")
        self.assertEqual(len(candidate.generation_evidence), 2)
        self.assertTrue(self.w1["review"]["evidence"][0] in candidate.evidence_documents)
        self.assertEqual(candidate.evidence_raw_hashes, [JK_UNLIMITED_SPORT_HASH])
        self.assertEqual(len(candidate.normalized_assertions), 8)
        for interpretation in candidate.normalized_assertions:
            self.assertIn("|pdf-page-10-sport-unlimited|", interpretation.source_assertion_ref)
            self.assertEqual(interpretation.manufacturer_term, interpretation.raw_source_value)
        encoded = serialize_artifact(candidate)
        self.assertEqual(encoded, serialize_artifact(self.candidate(supporting=(self.w1_review_order,))))
        roundtrip = deserialize_artifact(encoded)
        plan = plan_candidate_import(roundtrip)
        self.assert_create(plan)
        self.assertEqual(asdict(plan), asdict(plan_candidate_import(roundtrip)))
        revalidate_resolution(plan)
        manifest = dict_to_manifest(self.manifest(roundtrip, plan))
        self.assertEqual(asdict(reconstruct_plan_from_manifest(manifest.plans[0])), asdict(plan))
        self.assertEqual(VehicleDefinition.objects.count(), 2)

    def test_new_exact_binding_without_other_live_chains_resolves(self):
        candidate = self.candidate()
        self.assert_blocked(candidate, "Missing reviewed generation correspondence")
        self.revision(candidate.evidence_documents, restrictions={"trim_name": "Unlimited Sport"})
        self.assert_create(plan_candidate_import(candidate))
        self.assert_blocked(self.candidate(replace(self.source, provenance=replace(
            self.source.provenance, native_record_id="unreviewed-row",
        ))), "does not match candidate evidence")
        self.seed_w1()
        self.assert_blocked(candidate, "does not match candidate evidence")
        self.assert_create(plan_candidate_import(self.candidate(supporting=(self.w1_review_order,))))

    def test_missing_or_contradictory_generation_evidence_blocks(self):
        candidate = self.candidate()
        self.revision(candidate.evidence_documents)
        missing = replace(self.source, source_assertions=[
            a for a in self.source.source_assertions if a.attribute_key != "generation_designation"
        ])
        self.assert_blocked(self.candidate(missing), "overlapping generations")
        omitted = replace(candidate, generation_evidence=[])
        self.assertEqual(plan_candidate_import(omitted).planned_action.value, "reject")
        self.revision(candidate.evidence_documents, generation=self.jl)
        self.assert_blocked(candidate, "Conflicting generation correspondences")

    def test_altered_document_membership_blocks_even_with_same_hash_and_set_id(self):
        candidate = self.candidate()
        self.revision(candidate.evidence_documents)
        modified = replace(self.source, source_assertions=[
            replace(a, source_context="Different location") if a.attribute_key == "drive_descriptor" else a
            for a in self.source.source_assertions
        ])
        self.assert_blocked(self.candidate(modified), "does not match candidate evidence")

    def test_fabricated_combination_does_not_enter_normalization(self):
        fabricated = replace(self.source, source_assertions=[
            replace(a, source_context="Unrelated grade column") if a.attribute_key == "drive_descriptor" else a
            for a in self.source.source_assertions
        ])
        with self.assertRaisesRegex(ValueError, "Exact reviewed"):
            normalize_jeep(fabricated)

    def test_exact_match_and_inactive_slug_collision(self):
        candidate = self.candidate()
        self.revision(candidate.evidence_documents)
        target = VehicleDefinition.objects.create(generation=self.jk, **TARGET)
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action.value, "no_op_exact_match")
        self.assertEqual(plan.existing_vehicle_definition_id, target.pk)
        target.is_active = False
        target.save()
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.eligibility_status.value, "requires_review")
        self.assertEqual(plan.planned_action.value, "flag_review")
        self.assertEqual(plan.review_category.value, "slug_conflict")
        self.assertIn("Historical slug collision", " ".join(plan.reasons))
        proposed = VehicleDefinition(generation=self.jk, slug=plan.target_slug, **TARGET)
        with self.assertRaises(ValidationError):
            proposed.validate_constraints()
        self.assertEqual(plan.target_slug, target.slug)

    def test_manifest_integrity_and_stale_reviewed_resolution(self):
        candidate = self.candidate()
        first = self.revision(candidate.evidence_documents)
        plan = plan_candidate_import(candidate)
        payload = self.manifest(candidate, plan)
        self.assertEqual(payload, self.manifest(candidate, plan))
        self.assertEqual(payload["manifest_version"], "2.0")
        parsed = dict_to_manifest(json.loads(json.dumps(payload)))
        restored = reconstruct_plan_from_manifest(parsed.plans[0])
        self.assertEqual(asdict(restored), asdict(plan))
        revalidate_resolution(restored)
        tampered = deepcopy(payload)
        tampered["plans"][0]["target_slug"] = "different"
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(tampered)
        tampered = deepcopy(payload)
        tampered["plans"][0]["resolved_generation_id"] = self.jl.pk
        tampered["manifest_hash"] = compute_manifest_hash(
            {key: value for key, value in tampered.items() if key != "manifest_hash"}
        )
        # The parser verifies the digest and internal snapshot. The read-only
        # resolution recheck binds the outer target ID to that snapshot.
        rehashed = dict_to_manifest(tampered)
        with self.assertRaisesRegex(ValidationError, "parent binding mismatch"):
            revalidate_resolution(reconstruct_plan_from_manifest(rehashed.plans[0]))
        self.revision(candidate.evidence_documents, previous=first, review_notes="Synthetic successor.")
        with self.assertRaisesRegex(ValidationError, "stale"):
            revalidate_resolution(restored)
        successor = GenerationCorrespondenceRevision.objects.get(supersedes=first)
        self.revision(candidate.evidence_documents, previous=successor, finding="withdrawn", generation=None)
        self.assert_blocked(candidate, "withdrawn")
        with self.assertRaisesRegex(ValidationError, "withdrawn"):
            revalidate_resolution(restored)
        self.assertEqual(VehicleDefinition.objects.count(), 2)
