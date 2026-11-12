"""RA-044 synthetic contracts; no fixture represents a real factory offering."""
import copy
import hashlib
import json
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from reference.powertrain import FIELDS, decimal_string, engine_label, record_powertrain
from reference.ingestion.contracts import (Envelope, SourceMetadata, SourceApplicability,
    ExtractionProvenance, SourceAssertion, SourceAssertionSet, NormalizedInterpretation,
    TechnicalValue, CandidateIdentity)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.generation_correspondence import digest, validate_bound_plan
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.importer import execute_candidate_import
from reference.ingestion.importing.matrix_workflow import MatrixExecutionError, _references, execute_matrix_year
from reference.ingestion.manifest import manifest_to_dict, dict_to_manifest, compute_manifest_hash, ManifestValidationError
from reference.ingestion.matrix import compute_matrix_digest, MatrixValidationError
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact, candidate_config_doc_to_dict
from reference.models import VehicleDefinition, ImportExecutionReceipt
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup


class StructuredPowertrainTests(SyntheticWranglerSetup, TestCase):
    def setUp(self):
        super().setUp()
        self.jk.is_active = False
        self.jk.save(update_fields=["is_active"])

    def powertrain_candidate(self, *, electrification="none", aspiration="naturally_aspirated",
                             fuel="gasoline", liters="3.6", cylinders=6,
                             trim="Synthetic Sport", label=None, omitted=(), version="2.1.0", extra=None):
        token = uuid.uuid4().hex
        raw = {"make": "Jeep", "model": "Wrangler", "model_year": 2018, "trim": trim,
               "generic_drive_classification": "4WD", "market": "US",
               "engine_name": label or f"{liters}L V{cylinders}",
               "engine_displacement_liters": liters, "engine_cylinders": cylinders,
               "engine_aspiration": aspiration, "fuel_type": fuel, "electrification_type": electrification}
        raw.update(extra or {})
        raw = {k: v for k, v in raw.items() if k not in omitted}
        path = self.root / f"powertrain-{token}.json"
        data = json.dumps(raw, sort_keys=True).encode()
        path.write_bytes(data)
        sas = SourceAssertionSet(Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
            SourceMetadata("synthetic_test", native_record_id=token,
                source_applicability=SourceApplicability(market="US", applicability_scope="configuration"),
                extraction_provenance=ExtractionProvenance("sha256:" + hashlib.sha256(data).hexdigest(),
                    path.name, "synthetic_fixture", "1.0", "synthetic_test")),
            [SourceAssertion(k, k, v, source_context=f"synthetic.{k}") for k, v in raw.items()])
        interps = [NormalizedInterpretation("i-" + k, k, k,
                   TechnicalValue(v, "L", str(v)) if k == FIELDS[0] else v) for k, v in raw.items()]
        return construct_candidate_configuration(
            CandidateIdentity("Jeep", "Wrangler", model_year=2018, market="US", trim_name=trim),
            [sas], interps, candidate_reference=token, schema_version=version)

    def create(self, candidate):
        plan, manifest = self.plan_and_manifest(candidate)
        self.assertEqual(plan.planned_action.value, "create", plan.reasons)
        self.assertEqual(manifest.manifest_version, "2.1")
        result, receipt = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "created", result.messages)
        return VehicleDefinition.objects.get(pk=result.vehicle_definition_id), receipt

    def test_nullable_historical_fields_and_immutable_identity(self):
        record = VehicleDefinition.objects.create(generation=self.jl, model_year=2018,
            trim_name="Old", engine_name="3.6L V6", drivetrain="4WD")
        self.assertEqual(record_powertrain(record), dict.fromkeys(FIELDS))
        original = (record.pk, record.uuid, record.slug)
        record.engine_displacement_liters = Decimal("3.60")
        record.save()
        self.assertEqual((record.pk, record.uuid, record.slug), original)

    def test_model_validation_and_database_constraints(self):
        VehicleDefinition(generation=self.jl, model_year=2018,
                          engine_displacement_liters=Decimal("0.01")).full_clean()
        for key, value in [(FIELDS[0], 0), (FIELDS[0], Decimal("3.601")),
                           (FIELDS[1], 0), (FIELDS[1], True), (FIELDS[2], "unknown"),
                           (FIELDS[3], "electricity"), (FIELDS[4], "MHEV")]:
            with self.subTest(field=key, value=value):
                record = VehicleDefinition(generation=self.jl, model_year=2018, **{key: value})
                with self.assertRaises(ValidationError):
                    record.full_clean()
        for key, value in [(FIELDS[0], 0), (FIELDS[1], 0), (FIELDS[2], ""), (FIELDS[3], "unknown"), (FIELDS[4], "")]:
            with self.subTest(constraint=key), self.assertRaises(IntegrityError), transaction.atomic():
                VehicleDefinition.objects.create(generation=self.jl, model_year=2018, **{key: value})

    def test_decimal_normalization_without_rounding(self):
        self.assertEqual(decimal_string("3.60"), "3.6")
        for value in ("0", "NaN", "3.601", True, 3.6, "1000"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                decimal_string(value)

    def test_generated_descriptor_preserves_marketed_hundredths(self):
        candidate = self.powertrain_candidate(liters="2.75", cylinders=4, omitted=("engine_name",))
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action.value, "create", plan.reasons)
        self.assertEqual(plan.target_vehicle_definition_fields["engine_name"], "2.75L I4")

    def test_one_source_supports_five_fields_and_round_trip(self):
        candidate = self.powertrain_candidate(liters="3.60")
        self.assertEqual(candidate.canonical_powertrain[FIELDS[0]], "3.6")
        encoded = serialize_artifact(candidate)
        self.assertEqual(serialize_artifact(deserialize_artifact(encoded)), encoded)
        plan, manifest = self.plan_and_manifest(candidate)
        validate_bound_plan(plan)
        self.assertEqual(manifest_to_dict(dict_to_manifest(manifest_to_dict(manifest))), manifest_to_dict(manifest))
        self.assertEqual(len(plan.target_vehicle_definition_fields), 10)
        self.assertEqual(plan.generation_resolution["resolution_version"], "1.1")

    def test_missing_evidence_never_defaults_to_conventional(self):
        for key in FIELDS:
            with self.subTest(key=key):
                candidate = self.powertrain_candidate(omitted=(key,))
                self.assertIsNone(candidate.canonical_powertrain[key])
                self.assertNotEqual(plan_candidate_import(candidate).planned_action.value, "create")

    def test_conflicting_or_unqualified_evidence_rejected(self):
        candidate = self.powertrain_candidate()
        extra = copy.deepcopy(next(i for i in candidate.normalized_assertions if i.target_attribute_key == "fuel_type"))
        extra.interpretation_id += "-conflict"
        extra.normalized_concept = "diesel"
        candidate.normalized_assertions.append(extra)
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")
        candidate = self.powertrain_candidate()
        candidate.normalized_assertions[0].source_assertion_ref = "context-only"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_legacy_hash_round_trip_and_no_structured_smuggling(self):
        encoded = serialize_artifact(self.candidate)
        self.assertEqual(serialize_artifact(deserialize_artifact(encoded)), encoded)
        payload = candidate_config_doc_to_dict(self.candidate)
        payload["canonical_powertrain"] = self.powertrain_candidate().canonical_powertrain
        with self.assertRaises(ValueError):
            deserialize_artifact(payload)

    def test_v1_cannot_execute_structured_identity_through_unknown_fields(self):
        candidate = copy.deepcopy(self.candidate)
        candidate.envelope.schema_version = "1.0.0"
        candidate.envelope.artifact_type = "rigarchive.candidate_configuration.v1"
        candidate.generation_evidence = []
        candidate.evidence_documents = []
        candidate.unknown_fields["canonical_powertrain"] = self.powertrain_candidate().canonical_powertrain
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_unrelated_source_assertion_cannot_establish_engine_facts(self):
        candidate = self.powertrain_candidate()
        make_ref = next(i.source_assertion_ref for i in candidate.normalized_assertions if i.target_attribute_key == "make")
        item = next(i for i in candidate.normalized_assertions if i.target_attribute_key == "fuel_type")
        item.source_assertion_ref = make_ref
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_ess_does_not_prove_none_and_etorque_explicitly_supports_mhev(self):
        candidate = self.powertrain_candidate(electrification="mild_hybrid")
        doc = candidate.evidence_documents[0]
        assertion = next(a for a in doc["assertions"] if a["attribute_key"] == "electrification_type")
        assertion["raw_value"] = "eTorque"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "create")
        assertion["raw_value"] = "ESS"
        for i in candidate.normalized_assertions:
            if i.target_attribute_key == "electrification_type":
                i.normalized_concept = "none"
        candidate.canonical_powertrain["electrification_type"] = "none"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_manifest_version_downgrade_rejected(self):
        _, manifest = self.plan_and_manifest(self.powertrain_candidate())
        payload = manifest_to_dict(manifest)
        payload["manifest_version"] = "2.0"
        payload["manifest_hash"] = compute_manifest_hash({k: v for k, v in payload.items() if k != "manifest_hash"})
        with self.assertRaises(ManifestValidationError):
            dict_to_manifest(payload)

    def test_equal_tuple_different_label_preserves_uuid_and_slug(self):
        record, _ = self.create(self.powertrain_candidate())
        before = (record.pk, record.uuid, record.slug, record.engine_name)
        candidate = self.powertrain_candidate(label="Different designation 3.6L V6")
        plan, manifest = self.plan_and_manifest(candidate)
        self.assertEqual(plan.planned_action.value, "no_op_exact_match", plan.reasons)
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "no_op_exact_match")
        record.refresh_from_db()
        self.assertEqual((record.pk, record.uuid, record.slug, record.engine_name), before)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_all_hybrid_types_and_fixed_slug_qualifiers(self):
        for value, suffix in [("none", "us"), ("mild_hybrid", "us-mhev"), ("hybrid", "us-hev"), ("plug_in_hybrid", "us-phev")]:
            with self.subTest(electrification=value):
                candidate = self.powertrain_candidate(electrification=value)
                before = plan_candidate_import(candidate).target_slug
                record, receipt = self.create(candidate)
                self.assertTrue(record.slug.endswith(suffix))
                self.assertEqual(record.slug, before)
                self.assertEqual(receipt.target_fields_json["electrification_type"], value)
        self.assertEqual(VehicleDefinition.objects.count(), 4)

    def test_aspiration_and_fuel_are_mechanical_dimensions(self):
        self.create(self.powertrain_candidate())
        for aspiration, fuel in [("turbocharged", "gasoline"), ("turbocharged", "diesel"),
                                  ("supercharged", "gasoline"), ("twincharged", "gasoline")]:
            with self.subTest(aspiration=aspiration, fuel=fuel):
                candidate = self.powertrain_candidate(aspiration=aspiration, fuel=fuel)
                plan = plan_candidate_import(candidate)
                self.assertEqual(plan.create_basis.value, "mechanical_dimension")
                self.create(candidate)
        self.assertEqual(VehicleDefinition.objects.count(), 5)

    def test_unknown_legacy_peer_blocks_even_identical_label(self):
        VehicleDefinition.objects.create(generation=self.jl, model_year=2018,
            trim_name="Synthetic Sport", engine_name="3.6L V6", drivetrain="4WD")
        self.assertEqual(plan_candidate_import(self.powertrain_candidate()).planned_action.value, "flag_review")

    def test_inactive_identity_and_occupied_slug_block(self):
        candidate = self.powertrain_candidate()
        plan = plan_candidate_import(candidate)
        VehicleDefinition.objects.create(generation=self.jl, model_year=2018, trim_name="Unrelated",
            engine_name="3.6L V6", drivetrain="4WD", slug=plan.target_slug)
        self.assertEqual(plan_candidate_import(candidate).review_category.value, "slug_conflict")

    def test_other_aspiration_and_descriptor_mismatch_require_review(self):
        for kwargs in ({"aspiration": "other"}, {"label": "Synthetic engine without dimensions"}, {"label": "2.0L I4"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(plan_candidate_import(self.powertrain_candidate(**kwargs)).planned_action.value, "flag_review")

    def test_peer_canonical_change_stales_plan(self):
        record, _ = self.create(self.powertrain_candidate())
        plan, manifest = self.plan_and_manifest(self.powertrain_candidate(electrification="mild_hybrid"))
        VehicleDefinition.objects.filter(pk=record.pk).update(electrification_type="hybrid")
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_peer_receipt_change_stales_plan(self):
        _, receipt = self.create(self.powertrain_candidate())
        plan, manifest = self.plan_and_manifest(self.powertrain_candidate(electrification="mild_hybrid"))
        receipt.resolution_snapshot_json["unexpected"] = True
        receipt.save()
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")

    def test_source_byte_change_stales_plan(self):
        candidate = self.powertrain_candidate()
        plan, manifest = self.plan_and_manifest(candidate)
        path = self.root / candidate.evidence_documents[0]["raw_artifact_reference"]
        path.write_bytes(path.read_bytes() + b" ")
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertFalse(VehicleDefinition.objects.exists())

    def test_central_hybrid_labels(self):
        diesel = VehicleDefinition(engine_name="3.0L V6", fuel_type="diesel", engine_aspiration="turbocharged")
        self.assertEqual(engine_label(diesel), "3.0L V6, Turbocharged, Diesel")
        for value, long, short in [("mild_hybrid", "Mild hybrid (MHEV)", "MHEV"),
                                   ("hybrid", "Hybrid (HEV)", "HEV"),
                                   ("plug_in_hybrid", "Plug-in hybrid (PHEV)", "PHEV")]:
            record = VehicleDefinition(engine_name="3.6L V6 eTorque", electrification_type=value)
            self.assertIn(long, engine_label(record))
            self.assertTrue(engine_label(record, short=True).endswith(short))
        for value in (None, "none"):
            record = VehicleDefinition(engine_name="3.6L V6 ESS", electrification_type=value)
            self.assertEqual(engine_label(record, short=True), "3.6L V6 ESS")

    def test_redundant_turbo_engine_label_normalization(self):
        # Redundant standalone Turbo is removed when aspiration is turbocharged
        turbo_gas = VehicleDefinition(engine_name="2.0L I4 Turbo", engine_aspiration="turbocharged", fuel_type="gasoline")
        self.assertEqual(engine_label(turbo_gas, short=True), "2.0L I4 · Turbocharged")
        self.assertEqual(engine_label(turbo_gas, short=False), "2.0L I4, Turbocharged")

        # Redundant Turbo Diesel is normalized when aspiration is turbocharged and fuel is diesel
        turbo_diesel = VehicleDefinition(engine_name="3.0L V6 Turbo Diesel", engine_aspiration="turbocharged", fuel_type="diesel")
        self.assertEqual(engine_label(turbo_diesel, short=True), "3.0L V6 · Turbocharged · Diesel")
        self.assertEqual(engine_label(turbo_diesel, short=False), "3.0L V6, Turbocharged, Diesel")

        # 4xe PHEV retains electrification designation without duplicate Turbo
        turbo_phev = VehicleDefinition(engine_name="2.0L I4 Turbo PHEV", engine_aspiration="turbocharged", fuel_type="gasoline", electrification_type="plug_in_hybrid")
        self.assertEqual(engine_label(turbo_phev, short=True), "2.0L I4 · Turbocharged · PHEV")
        self.assertEqual(engine_label(turbo_phev, short=False), "2.0L I4, Turbocharged, Plug-in hybrid (PHEV)")

        # Unspecified or non-turbo aspiration preserves meaningful descriptor
        unspecified = VehicleDefinition(engine_name="2.4L Turbo I4")
        self.assertEqual(engine_label(unspecified, short=True), "2.4L Turbo I4")
        self.assertEqual(engine_label(unspecified, short=False), "2.4L Turbo I4")

    def matrix(self, candidates):
        rows = []
        for index, candidate in enumerate(candidates):
            plan = plan_candidate_import(candidate)
            self.assertEqual(plan.planned_action.value, "create", plan.reasons)
            evidence, correspondence = _references(plan)
            rows.append({"row_id": f"engine-{index}", "model_year": 2018,
                "target_fields": plan.target_vehicle_definition_fields, "target_slug": plan.target_slug,
                "action": "create", "permitted_create_bases": ["first_representation", "mechanical_dimension"],
                "candidate_reference": candidate.candidate_reference, "candidate_digest": plan.candidate_hash,
                "evidence": evidence, "correspondence": correspondence, "existing_record": None,
                "generation_binding": {"mode": "unique_deterministic", "strategy": "unique_year_range", "resolution_version": "1.1"}})
        return {"matrix_version": "2.1", "model_years": [2018], "market": "US", "rows": rows,
                "parents": {key: {"pk": obj.pk, "uuid": str(obj.uuid), "slug": obj.slug}
                    for key, obj in (("manufacturer", self.make), ("vehicle_model", self.model), ("generation", self.jl))}}

    def run_matrix(self, ordered):
        matrix = self.matrix(ordered)
        expected = {(c.canonical_powertrain["electrification_type"], plan_candidate_import(c).target_slug) for c in ordered}
        approval = build_matrix_approval(matrix, operator="synthetic_director", confirmed=True)
        candidates = {c.candidate_reference: c for c in ordered}
        _, report = execute_matrix_year(matrix, approval, 2018, candidates, self.root, execution_operator="synthetic_director")
        self.assertEqual([r["status"] for r in report["rows"]], ["newly_created", "newly_created"])
        identities = set(VehicleDefinition.objects.values_list("electrification_type", "slug"))
        self.assertEqual(identities, expected)
        count = ImportExecutionReceipt.objects.count()
        execute_matrix_year(matrix, approval, 2018, candidates, self.root, execution_operator="synthetic_director")
        self.assertEqual(ImportExecutionReceipt.objects.count(), count)
        self.assertEqual(VehicleDefinition.objects.count(), 2)
        return identities

    def test_matrix_conventional_then_mhev_is_idempotent(self):
        self.run_matrix([self.powertrain_candidate(), self.powertrain_candidate(electrification="mild_hybrid")])

    def test_matrix_mhev_then_conventional_is_idempotent(self):
        self.run_matrix([self.powertrain_candidate(electrification="mild_hybrid"), self.powertrain_candidate()])

    def test_matrix_atomic_rollback_after_later_receipt_failure(self):
        ordered = [self.powertrain_candidate(), self.powertrain_candidate(electrification="mild_hybrid")]
        matrix = self.matrix(ordered)
        approval = build_matrix_approval(matrix, operator="synthetic_director", confirmed=True)
        original = ImportExecutionReceipt.save
        count = [0]
        def fail_second(receipt, *args, **kwargs):
            if receipt._state.adding:
                count[0] += 1
                if count[0] == 2:
                    raise RuntimeError("Synthetic second receipt failure")
            return original(receipt, *args, **kwargs)
        with patch.object(ImportExecutionReceipt, "save", fail_second), self.assertRaises(MatrixExecutionError):
            execute_matrix_year(matrix, approval, 2018, {c.candidate_reference: c for c in ordered}, self.root,
                                execution_operator="synthetic_director")
        self.assertEqual(count[0], 2)
        self.assertFalse(VehicleDefinition.objects.exists())
        self.assertFalse(ImportExecutionReceipt.objects.exists())

    def test_matrix_duplicate_semantics_and_downgrades_rejected(self):
        candidates = [self.powertrain_candidate(), self.powertrain_candidate(electrification="mild_hybrid")]
        matrix = self.matrix(candidates)
        compute_matrix_digest(matrix)
        matrix["matrix_version"] = "2.0"
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)
        matrix["matrix_version"] = "2.1"
        matrix["rows"][1]["target_fields"]["electrification_type"] = "none"
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)

    def test_layout_only_difference_is_reviewed_without_duplicate(self):
        self.create(self.powertrain_candidate())
        plan = plan_candidate_import(self.powertrain_candidate(label="3.6L I6"))
        self.assertEqual(plan.planned_action.value, "flag_review")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_multiple_sources_and_shared_assertion_support(self):
        candidate = self.powertrain_candidate()
        # Preserve qualified lineage while splitting retained assertion sets.
        first = candidate.evidence_documents[0]
        second = copy.deepcopy(first)
        second["assertion_set_id"] += "-supplement"
        selected = {"fuel_type", "electrification_type"}
        second["assertions"] = [a for a in first["assertions"] if a["attribute_key"] in selected]
        first["assertions"] = [a for a in first["assertions"] if a["attribute_key"] not in selected]
        for interp in candidate.normalized_assertions:
            if interp.target_attribute_key in selected:
                parts = interp.source_assertion_ref.split("|")
                parts[2] = second["assertion_set_id"]
                interp.source_assertion_ref = "|".join(parts)
        candidate.evidence_documents.append(second)
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "create")
        # A single retained configuration assertion can support multiple facts.
        shared = "full-powertrain"
        first["assertions"].append({"assertion_id": shared, "attribute_key": "powertrain_configuration",
                                    "raw_value": candidate.canonical_powertrain.copy(), "source_context": "synthetic.full-row"})
        prefix = "|".join(first[k] for k in ("source_id", "raw_artifact_hash", "assertion_set_id"))
        for interp in candidate.normalized_assertions:
            if interp.target_attribute_key in FIELDS:
                interp.source_assertion_ref = prefix + "|" + shared
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "create")

    def test_peer_documents_and_new_peer_stale_existing_plan(self):
        record, receipt = self.create(self.powertrain_candidate())
        plan, manifest = self.plan_and_manifest(self.powertrain_candidate(electrification="mild_hybrid"))
        self.create(self.powertrain_candidate(electrification="hybrid"))
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 2)

    def test_unavailable_or_incomplete_peer_source_blocks(self):
        _, receipt = self.create(self.powertrain_candidate())
        doc = receipt.resolution_snapshot_json["generation_resolution"]["documents"][0]
        (self.root / doc["raw_artifact_reference"]).unlink()
        plan = plan_candidate_import(self.powertrain_candidate(electrification="mild_hybrid"))
        self.assertEqual(plan.planned_action.value, "flag_review")

    def test_conflicting_source_market_rejected(self):
        candidate = self.powertrain_candidate()
        candidate.evidence_documents[0]["source_applicability"]["market"] = "CA"
        self.assertEqual(plan_candidate_import(candidate).planned_action.value, "reject")

    def test_presentation_uses_central_labels_without_url_changes(self):
        from reference.services import _label_configuration_choices
        records = []
        for value in ("none", "mild_hybrid", "hybrid", "plug_in_hybrid"):
            record, _ = self.create(self.powertrain_candidate(electrification=value))
            records.append(record)
            if value != "none":
                self.assertIn(engine_label(record).split(", ")[-1], str(record))
        choices = _label_configuration_choices(records)
        self.assertIn("MHEV", str(choices))
        self.assertIn("PHEV", str(choices))

    def test_manufacturer_and_emissions_codes_do_not_split_identity(self):
        record, _ = self.create(self.powertrain_candidate(extra={"manufacturer_engine_code": "SYNTHETIC-FED"}))
        candidate = self.powertrain_candidate(extra={"manufacturer_engine_code": "SYNTHETIC-CA"})
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action.value, "no_op_exact_match", plan.reasons)
        self.assertEqual(plan.existing_vehicle_definition_id, record.pk)

    def test_verified_tuning_alternatives_require_review(self):
        self.create(self.powertrain_candidate(extra={"horsepower": 280, "torque": 260}))
        candidate = self.powertrain_candidate(extra={"horsepower": 285, "torque": 260})
        plan = plan_candidate_import(candidate)
        self.assertEqual(plan.planned_action.value, "flag_review", plan.reasons)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_transmission_choices_do_not_multiply_identity(self):
        record, _ = self.create(self.powertrain_candidate(extra={"transmission": "synthetic manual"}))
        plan = plan_candidate_import(self.powertrain_candidate(extra={"transmission": "synthetic automatic"}))
        self.assertEqual(plan.planned_action.value, "no_op_exact_match", plan.reasons)
        self.assertEqual(plan.existing_vehicle_definition_id, record.pk)

    def test_exact_inactive_identity_requires_review(self):
        record, _ = self.create(self.powertrain_candidate())
        record.is_active = False
        record.save(update_fields=["is_active"])
        self.assertEqual(plan_candidate_import(self.powertrain_candidate()).planned_action.value, "flag_review")

    def test_structured_tuple_cannot_be_forged_under_old_proof(self):
        plan, manifest = self.plan_and_manifest(self.powertrain_candidate())
        plan.generation_resolution["engine_distinction"]["version"] = "1.0"
        with self.assertRaises(ValidationError):
            validate_bound_plan(plan)

    def test_legacy_null_peer_assessed_from_explicit_receipt_evidence_without_backfill(self):
        record, receipt = self.create(self.powertrain_candidate())
        from reference.powertrain import BASE_FIELDS
        original_identity = (record.pk, record.uuid, record.slug)
        # Synthetic historical receipt with five explicit retained facts and legacy target semantics.
        resolution = receipt.resolution_snapshot_json["generation_resolution"]
        resolution["resolution_version"] = "1.0"
        resolution["fields"] = {k: getattr(record, k) for k in ("engine_name", "trim_name", "drivetrain")}
        resolution.pop("engine_distinction")
        receipt.target_fields_json = {k: getattr(record, k) for k in BASE_FIELDS}
        receipt.save()
        VehicleDefinition.objects.filter(pk=record.pk).update(**dict.fromkeys(FIELDS))
        candidate = self.powertrain_candidate(electrification="mild_hybrid")
        plan, manifest = self.plan_and_manifest(candidate)
        self.assertEqual(plan.planned_action.value, "create", plan.reasons)
        self.assertEqual(plan.generation_resolution["engine_distinction"]["peers"][0]["canonical_state"]["electrification_type"], None)
        result, _ = self.execute(plan, manifest)
        self.assertEqual(result.outcome.value, "created", result.messages)
        record.refresh_from_db()
        self.assertEqual(record_powertrain(record), dict.fromkeys(FIELDS))
        self.assertEqual((record.pk, record.uuid, record.slug), original_identity)



class PowertrainMigrationTests(TransactionTestCase):
    def test_additive_migration_preserves_all_existing_columns(self):
        # This test runs exclusively through Django's isolated test connection.
        self.assertNotEqual(str(connection.settings_dict["NAME"]), str(Path(__file__).parents[2] / "db.sqlite3"))
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_target = [("reference", "0009_factory_equipment_compatibility")]
        executor.migrate(old_target)
        try:
            apps = executor.loader.project_state(old_target).apps
            manufacturer = apps.get_model("reference", "Manufacturer").objects.create(name="Synthetic migration manufacturer")
            model = apps.get_model("reference", "VehicleModel").objects.create(manufacturer=manufacturer, name="Synthetic model")
            generation = apps.get_model("reference", "Generation").objects.create(vehicle_model=model, name="Synthetic generation", start_year=2018)
            old = apps.get_model("reference", "VehicleDefinition").objects.create(
                generation=generation, model_year=2018, trim_name="Synthetic Sport", engine_name="3.6L V6",
                drivetrain="4WD", market="US", slug="existing-immutable-locator", notes="Preserve historical data")
            apps.get_model("reference", "ImportExecutionReceipt").objects.create(
                operator_label="synthetic_legacy", operation_type="vehicle_definition_import", execution_outcome="created",
                resolved_generation_id=generation.pk, created_vehicle_definition_id=old.pk,
                created_vehicle_definition_pk_snapshot=old.pk,
                created_vehicle_definition_uuid_snapshot=str(old.uuid), created_vehicle_definition_slug_snapshot=old.slug,
                target_fields_json={"engine_name": old.engine_name}, resolution_snapshot_json={"historical": "unchanged"})
            snapshots = {}
            with connection.cursor() as cursor:
                for table in connection.introspection.table_names():
                    if table == "django_migrations":
                        continue
                    columns = [c.name for c in connection.introspection.get_table_description(cursor, table)]
                    select = ",".join(connection.ops.quote_name(c) for c in columns)
                    cursor.execute(f'SELECT {select} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    snapshots[table] = (columns, cursor.fetchall())
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            with connection.cursor() as cursor:
                for table, (columns, rows) in snapshots.items():
                    select = ",".join(connection.ops.quote_name(c) for c in columns)
                    cursor.execute(f'SELECT {select} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    self.assertEqual(cursor.fetchall(), rows, table)
            record = VehicleDefinition.objects.get(pk=old.pk)
            self.assertEqual(record_powertrain(record), dict.fromkeys(FIELDS))
        finally:
            MigrationExecutor(connection).migrate(latest)
