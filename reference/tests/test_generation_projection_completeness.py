"""Regression coverage for omitted generation evidence; all data is isolated/synthetic."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from reference.ingestion.contracts import CandidateIdentity, SourceMetadata
from reference.ingestion.generation_correspondence import (
    digest, resolve_generation, revalidate_resolution, validate_generation_evidence,
)
from reference.ingestion.importing.planner import plan_candidate_import, plan_candidate_import_with_adjudications
from reference.ingestion.importing.importer import execute_candidate_import
from reference.ingestion.importing.workflow import CanonicalExecutionWorkflowError
from reference.ingestion.manifest import (
    dict_to_manifest, manifest_to_dict, reconstruct_plan_from_manifest,
    compute_manifest_hash, ManifestValidationError,
)
from reference.ingestion.serialization import (
    candidate_config_doc_to_dict, deserialize_artifact, serialize_artifact,
)
from reference.ingestion.validation import validate_candidate_configuration
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup


class GenerationProjectionCompletenessTests(SyntheticWranglerSetup, TestCase):
    def assert_blocked(self, candidate):
        with self.assertRaises(ValidationError):
            validate_candidate_configuration(candidate)
        for plan in (plan_candidate_import(candidate), plan_candidate_import_with_adjudications(candidate, [object()])):
            self.assertNotIn(plan.planned_action.value, ("create", "no_op_exact_match"))
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def unique_scope(self):
        self.jl.is_active = False
        self.jl.save()

    def test_empty_projection_with_explicit_assertion_is_rejected(self):
        self.unique_scope()
        candidate = copy.deepcopy(self.candidate)
        candidate.generation_evidence = []
        self.assert_blocked(candidate)
        # The validator is observational: it must not repair a submitted omission.
        self.assertEqual(candidate.generation_evidence, [])

    def test_partial_projection_is_rejected(self):
        candidate = self.make_candidate("JK", "JK")
        self.assertEqual(len(candidate.generation_evidence), 2)
        candidate.generation_evidence.pop()
        self.assert_blocked(candidate)

    def test_unknown_generation_term_cannot_disappear(self):
        self.unique_scope()
        candidate = self.make_candidate("UNKNOWN SOURCE TERM")
        validate_candidate_configuration(candidate)
        self.assertEqual(candidate.generation_evidence[0]["native_identifier"], "UNKNOWN SOURCE TERM")
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")
        candidate.generation_evidence = []
        self.assert_blocked(candidate)

    def test_conflicting_projection_cannot_be_partially_omitted(self):
        candidate = self.make_candidate("JK", "JL")
        self.publish(self.review(candidate))
        validate_candidate_configuration(candidate)
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")
        candidate.generation_evidence.pop()
        self.assert_blocked(candidate)

    def test_same_local_assertion_id_in_different_documents_is_independent(self):
        candidate = copy.deepcopy(self.candidate)
        other = self.make_candidate("JL")
        candidate.evidence_documents.extend(other.evidence_documents)
        candidate.generation_evidence.extend(other.generation_evidence)
        candidate.evidence_raw_hashes = sorted(set(candidate.evidence_raw_hashes + other.evidence_raw_hashes))
        validate_candidate_configuration(candidate)
        self.assertEqual(candidate.generation_evidence[0]["assertion_id"], candidate.generation_evidence[1]["assertion_id"])
        self.assertNotEqual(candidate.generation_evidence[0]["document_hash"], candidate.generation_evidence[1]["document_hash"])
        candidate.generation_evidence.pop()
        self.assert_blocked(candidate)

    def test_duplicate_projected_reference_is_rejected(self):
        candidate = copy.deepcopy(self.candidate)
        candidate.generation_evidence.append(copy.deepcopy(candidate.generation_evidence[0]))
        self.assert_blocked(candidate)

    def test_complete_absence_allows_unique_year_resolution(self):
        self.unique_scope()
        candidate = self.make_candidate(None)
        validate_candidate_configuration(candidate)
        resolved = resolve_generation(self.model, 2018, "US", [], candidate.evidence_documents)
        self.assertEqual(resolved["basis"], "unique_year_range")
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "create")

    def test_complete_explicit_projection_resolves_reviewed_correspondence(self):
        self.publish()
        validate_candidate_configuration(self.candidate)
        plan = plan_candidate_import(self.candidate)
        self.assertEqual(plan.resolved_generation_id, self.jk.pk)
        self.assertEqual(plan.generation_resolution["basis"], "reviewed_source_correspondence")

    def test_direct_resolver_checks_completeness_before_parent_lookup(self):
        self.unique_scope()
        with patch("reference.models.Generation.objects.filter", side_effect=AssertionError("Parent lookup must follow completeness validation")):
            with self.assertRaises(ValidationError):
                resolve_generation(self.model, 2018, "US", [], self.candidate.evidence_documents)
            with self.assertRaises(ValidationError):
                resolve_generation(self.model, 2018, "US", [], [])

    def test_serialization_and_deserialization_omissions_are_rejected(self):
        raw = candidate_config_doc_to_dict(self.candidate)
        for omitted in (False, True):
            with self.subTest(omitted=omitted):
                altered = copy.deepcopy(raw)
                if omitted:
                    altered.pop("generation_evidence")
                else:
                    altered["generation_evidence"] = []
                with self.assertRaises(ValidationError):
                    deserialize_artifact(altered)
        candidate = copy.deepcopy(self.candidate)
        candidate.generation_evidence = []
        with self.assertRaises(ValidationError):
            serialize_artifact(candidate)
        restored = deserialize_artifact(serialize_artifact(self.candidate))
        validate_candidate_configuration(restored)

    def test_missing_retained_assertions_fails_closed(self):
        candidate = self.make_candidate(None)
        for field, value in (("assertions", []), ("assertions", None)):
            altered = copy.deepcopy(candidate)
            altered.evidence_documents[0][field] = value
            self.assert_blocked(altered)
        with self.assertRaises(ValidationError):
            validate_generation_evidence([], [])

    def omitted_plan(self):
        """Tamper a once valid unique-year plan while retaining an explicit source assertion."""
        self.unique_scope()
        self.publish()
        plan, manifest = self.plan_and_manifest()
        tampered = copy.deepcopy(plan)
        tampered.candidate_snapshot["generation_evidence"] = []
        tampered.candidate_hash = digest(tampered.candidate_snapshot)
        tampered.generation_resolution["generation_evidence"] = []
        tampered.generation_resolution["basis"] = "unique_year_range"
        tampered.generation_resolution["correspondences"] = []
        return tampered, manifest

    def test_recomputed_hashes_cannot_authorize_omission(self):
        tampered, manifest = self.omitted_plan()
        raw = manifest_to_dict(manifest)
        for field in ("candidate_snapshot", "candidate_hash", "generation_resolution"):
            raw["plans"][0][field] = getattr(tampered, field)
        raw["manifest_hash"] = compute_manifest_hash({k: v for k, v in raw.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(raw)
        with self.assertRaises(CanonicalExecutionWorkflowError):
            self.execute(tampered, manifest)
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_direct_reconstruction_and_execution_block_omission(self):
        tampered, manifest = self.omitted_plan()
        review = copy.deepcopy(manifest.plans[0])
        for field in ("candidate_snapshot", "candidate_hash", "generation_resolution"):
            setattr(review, field, getattr(tampered, field))
        with self.assertRaises(ManifestValidationError):
            reconstruct_plan_from_manifest(review)
        with self.assertRaises(ValidationError):
            revalidate_resolution(tampered)
        self.assertEqual(execute_candidate_import(tampered).outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_legacy_paths_cannot_drop_v2_authorization_or_retained_assertions(self):
        tampered, manifest = self.omitted_plan()
        legacy_candidate = copy.deepcopy(self.candidate)
        legacy_candidate.envelope.artifact_type = "rigarchive.candidate_configuration.v1"
        legacy_candidate.envelope.schema_version = "1.0.0"
        legacy_candidate.generation_evidence = []
        self.assertEqual(plan_candidate_import(legacy_candidate).planned_action.value, "flag_review")
        legacy_candidate.evidence_documents = []
        from reference.ingestion.contracts import NormalizedInterpretation
        for key in ("generation_section", "source_model_code"):
            with self.subTest(legacy_generation_key=key):
                hinted = copy.deepcopy(legacy_candidate)
                hinted.normalized_assertions.append(NormalizedInterpretation(
                    "legacy-generation-hint", "generation-assertion", key, "JK"))
                self.assertEqual(plan_candidate_import(hinted).planned_action.value, "flag_review")
        legacy_manifest = copy.deepcopy(manifest)
        legacy_manifest.manifest_version = "1.0"
        with self.assertRaises(ManifestValidationError):
            manifest_to_dict(legacy_manifest)
        tampered.generation_resolution = {}
        with self.assertRaises(ValidationError):
            revalidate_resolution(tampered)
        self.assertEqual(execute_candidate_import(tampered).outcome.value, "aborted_stale_plan")

    def test_real_legacy_toyota_and_volkswagen_candidates_still_plan(self):
        from reference.ingestion.acquisition.jd_power_extractor import JDPowerExtractor
        from reference.ingestion.normalization.jd_power import JDPowerNormalizer
        from reference.ingestion.candidate.builder import construct_candidate_configuration
        folder = Path(__file__).parent / "fixtures" / "acquisition" / "jd_power"
        for make, model, year, filename in (
            ("Toyota", "4Runner", 2018, "2018_4runner_configurations.json"),
            ("Volkswagen", "Touareg", 2016, "2016_touareg_configurations.json"),
        ):
            with self.subTest(model=model):
                manufacturer = Manufacturer.objects.create(name=make)
                vm = VehicleModel.objects.create(manufacturer=manufacturer, name=model)
                generation = Generation.objects.create(vehicle_model=vm, name="Synthetic legacy scope", start_year=year, end_year=year)
                metadata = SourceMetadata("jd_power", target_context={"make": make, "model": model, "model_year": year})
                aset = JDPowerExtractor().extract(json.loads((folder / filename).read_text()), metadata)[0]
                interps = JDPowerNormalizer().normalize(aset)
                candidate = construct_candidate_configuration(CandidateIdentity(make, model, model_year=year), [aset], interps)
                self.assertEqual(candidate.envelope.schema_version, "1.0.0")
                plan = plan_candidate_import(candidate)
                self.assertEqual(plan.planned_action.value, "create")
                self.assertEqual(plan.resolved_generation_id, generation.pk)
