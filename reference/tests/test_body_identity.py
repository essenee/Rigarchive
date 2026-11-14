"""ADR-0013 pure regressions; no databases, approvals, candidates or parent writes."""
import copy
import hashlib
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from reference.body_identity import (
    BASELINE_CONTRACT, BODY_CONTRACT, DIMENSIONS, ScopedAliases,
    baseline_preimage, body_preimage, canonical_json, compare_bodies,
    normalize_dimensions, resolve_body_observation, semantic_digest, validate_preimage,
)
from reference.ingestion.candidate.v3_foundations import (
    UnresolvedV3Contract, deserialize_identity_fields, identity_fields_digest,
    serialize_identity_fields, validate_identity_fields, validate_qualified_interpretations,
)
from reference.ingestion.contracts import NormalizedInterpretation

SCOPE = {"manufacturer_key": "jeep", "model_key": "wrangler", "generation_key": "jl"}
POWERTRAIN = {"engine_displacement_liters": "3.6", "engine_cylinders": 6,
              "engine_aspiration": "naturally_aspirated", "fuel_type": "gasoline",
              "electrification_type": "none"}


def baseline(**overrides):
    values = dict(scope=SCOPE, model_year=2024, trim_name="Sport", drivetrain="4WD",
                  market="US", canonical_powertrain=POWERTRAIN)
    return baseline_preimage(**(values | overrides))


class SparseBodyIdentityTests(SimpleTestCase):
    def body(self, **dimensions):
        return body_preimage(SCOPE, dimensions)

    def test_no_body_requires_no_parent_or_review(self):
        result = resolve_body_observation(None, [])
        self.assertEqual(result.relation, "no_body")
        self.assertFalse(result.requires_review)
        ordinary = baseline(model_year=2007, trim_name="SR5", scope={
            "manufacturer_key": "toyota", "model_key": "4runner", "generation_key": "test-fourth"})
        self.assertIsNone(ordinary["body_digest"])
        self.assertIsNone(ordinary["series"])
        semantic_digest(ordinary)

    def test_all_seven_fields_are_supported_independently(self):
        self.assertEqual(len(DIMENSIONS), 7)
        for field in DIMENSIONS:
            with self.subTest(field=field):
                value = {"namespace": "factory", "token": "test-code"} if field == "body_code" else "test"
                self.assertEqual(self.body(**{field: value})["dimensions"], {field: value})

    def test_missing_fields_are_omitted_without_status_findings(self):
        sparse = self.body(door_configuration="two-door", roof_height_designation=None,
                           body_style=None, side_door_arrangement="")
        self.assertEqual(sparse["dimensions"], {"door_configuration": "two-door"})
        self.assertEqual(semantic_digest(sparse), semantic_digest(self.body(door_configuration="two-door")))

    def test_empty_parent_is_rejected_without_blocking_no_body_path(self):
        for dimensions in ({}, {key: None for key in DIMENSIONS}):
            with self.assertRaises(ValidationError):
                body_preimage(SCOPE, dimensions)

    def test_unknown_fields_and_fabricated_statuses_rejected(self):
        for dimensions in ({"height_mm": 2000}, {"roof_height_designation": {"state": "not_applicable"}}):
            with self.assertRaises(ValidationError):
                body_preimage(SCOPE, dimensions)

    def test_tokens_are_not_automatically_casefolded_or_trimmed(self):
        for value in ("2 Door", "UPPER", " high", "a--b", "é", "a" * 129, False, 2):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.body(door_configuration=value)

    def test_reviewed_scoped_aliases_reuse_identity(self):
        aliases = ScopedAliases(SCOPE, {"door_configuration": {"2 Door": "two-door", "2-door": "two-door"}})
        expected = semantic_digest(self.body(door_configuration="two-door"))
        for raw in ("2 Door", "2-door"):
            mapped = body_preimage(SCOPE, {"door_configuration": raw}, aliases=aliases)
            self.assertEqual(semantic_digest(mapped), expected)

    def test_aliases_cannot_cross_generation(self):
        aliases = ScopedAliases(SCOPE | {"generation_key": "jk"}, {})
        with self.assertRaises(ValidationError):
            body_preimage(SCOPE, {"door_configuration": "two-door"}, aliases=aliases)

    def test_generation_and_manufacturer_are_identity_scope(self):
        dimensions = {"door_configuration": "two-door"}
        original = body_preimage(SCOPE, dimensions)
        for scope in (SCOPE | {"generation_key": "jk"}, SCOPE | {"manufacturer_key": "other"}):
            self.assertNotEqual(semantic_digest(original), semantic_digest(body_preimage(scope, dimensions)))

    def test_scope_cannot_be_missing_or_extended(self):
        for scope in ({}, SCOPE | {"uuid": "anything"}, SCOPE | {"model_key": "Wrangler"}):
            with self.assertRaises(ValidationError):
                body_preimage(scope, {"door_configuration": "two-door"})

    def test_body_codes_require_namespace_and_affect_digest_when_identity_bearing(self):
        a = self.body(body_code={"namespace": "factory-a", "token": "code"})
        b = self.body(body_code={"namespace": "factory-b", "token": "code"})
        self.assertNotEqual(semantic_digest(a), semantic_digest(b))
        for bad in ("code", {"token": "code"}, {"namespace": "factory", "token": "CODE"}):
            with self.assertRaises(ValidationError):
                self.body(body_code=bad)

    def test_doors_distinguish_body_and_baseline(self):
        a = semantic_digest(self.body(door_configuration="two-door"))
        b = semantic_digest(self.body(door_configuration="four-door"))
        self.assertNotEqual(a, b)
        self.assertNotEqual(semantic_digest(baseline(body_digest=a)), semantic_digest(baseline(body_digest=b)))

    def test_sparse_transit_dimensions_and_independent_series(self):
        scope = {"manufacturer_key": "ford", "model_key": "transit", "generation_key": "test-generation"}
        body = body_preimage(scope, {"wheelbase_designation": "long", "body_length_designation": "extended",
                                     "roof_height_designation": "high"})
        self.assertEqual(len(body["dimensions"]), 3)
        a = baseline(scope=scope, body_digest=semantic_digest(body), series_digest="sha256:" + "a" * 64)
        b = baseline(scope=scope, body_digest=semantic_digest(body), series_digest="sha256:" + "b" * 64)
        self.assertNotEqual(semantic_digest(a), semantic_digest(b))

    def test_structural_side_doors_distinguish_but_equipment_does_not_enter_basis(self):
        a = self.body(side_door_arrangement="single-sliding")
        b = self.body(side_door_arrangement="dual-sliding")
        self.assertEqual(compare_bodies(a, b).relation, "distinct")
        with self.assertRaises(ValidationError):
            self.body(door_equipment="powered")

    def test_missing_dimension_is_compatible_not_equal_or_distinct(self):
        a = self.body(roof_height_designation="high")
        b = self.body(roof_height_designation="high", wheelbase_designation="long")
        result = compare_bodies(a, b)
        self.assertEqual(result.relation, "compatible")
        self.assertFalse(result.requires_review)
        self.assertEqual(compare_bodies(a, None).relation, "compatible")

    def test_known_distinct_configurations_are_not_source_contradictions(self):
        a = self.body(roof_height_designation="high")
        b = self.body(roof_height_designation="low")
        self.assertEqual(compare_bodies(a, b).relation, "distinct")
        self.assertFalse(compare_bodies(a, b).requires_review)
        conflict = compare_bodies(a, b, same_configuration=True)
        self.assertTrue(conflict.requires_review)
        self.assertEqual(conflict.differing_dimensions, ("roof_height_designation",))

    def test_unique_sparse_match_is_not_an_equality_proof(self):
        observation = self.body(roof_height_designation="high")
        known = self.body(roof_height_designation="high", wheelbase_designation="long")
        result = resolve_body_observation(observation, [known])
        self.assertEqual(result.relation, "uniquely_compatible")
        self.assertFalse(result.requires_review)
        self.assertNotEqual(semantic_digest(observation), semantic_digest(known))

    def test_partial_observation_cannot_chain_merge_known_alternatives(self):
        a = self.body(roof_height_designation="high", wheelbase_designation="long")
        b = self.body(roof_height_designation="high")
        c = self.body(roof_height_designation="high", wheelbase_designation="short")
        self.assertEqual(compare_bodies(a, b).relation, "compatible")
        self.assertEqual(compare_bodies(b, c).relation, "compatible")
        self.assertEqual(compare_bodies(a, c).relation, "distinct")
        first = resolve_body_observation(b, [a, c])
        self.assertTrue(first.requires_review)
        self.assertEqual(first, resolve_body_observation(b, [c, a]))

    def test_known_door_alternatives_cannot_be_suppressed_by_omission(self):
        known = [self.body(door_configuration=value) for value in ("two-door", "four-door")]
        self.assertTrue(resolve_body_observation(None, known).requires_review)

    def test_duplicate_alternatives_do_not_manufacture_ambiguity(self):
        a = self.body(door_configuration="two-door")
        self.assertFalse(resolve_body_observation(a, [a, copy.deepcopy(a)]).requires_review)

    def test_serialization_order_is_irrelevant(self):
        a = self.body(door_configuration="two-door", roof_height_designation="high")
        b = dict(reversed(list(a.items())))
        b["dimensions"] = dict(reversed(list(a["dimensions"].items())))
        self.assertEqual(canonical_json(a), canonical_json(b))
        self.assertEqual(semantic_digest(a), semantic_digest(b))

    def test_nonidentity_metadata_and_nulls_cannot_enter_frozen_preimage(self):
        a = self.body(door_configuration="two-door")
        for bad in (a | {"evidence_hash": "anything"}, a | {"dimensions": a["dimensions"] | {"body_style": None}}):
            with self.assertRaises(ValidationError):
                semantic_digest(bad)

    def test_baseline_engine_fields_and_null_parent_shape(self):
        value = baseline()
        self.assertNotIn("engine_name", value)
        self.assertEqual(value["canonical_powertrain"], POWERTRAIN)
        with self.assertRaises(ValidationError):
            semantic_digest(value | {"engine_name": "3.6L"})
        with self.assertRaises(ValidationError):
            baseline(canonical_powertrain=POWERTRAIN | {"fuel_type": None})

    def test_baseline_rejects_invalid_values(self):
        for fields in ({"scope": None}, {"model_year": True}, {"trim_name": ""},
                       {"drivetrain": "4x4"}, {"market": "EU"}, {"body_digest": "bad"},
                       {"series_digest": "bad"}, {"canonical_powertrain": None}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                baseline(**fields)

    def test_historical_contracts_are_not_reinterpreted(self):
        for contract in ("factory-body-semantic/1", "vehicle-definition-body/1"):
            with self.assertRaises(ValidationError):
                validate_preimage({"identity_contract": contract})


class V3FoundationTests(SimpleTestCase):
    def test_historical_21_fixture_and_hash_meaning_are_unchanged(self):
        from reference.ingestion.serialization import deserialize_artifact, serialize_artifact
        from reference.ingestion.validation import IngestionValidationError

        path = Path(__file__).parent / "fixtures/ingestion/historical_jl24_candidate_2_1_0.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "2f341d71c8cc7aee323ad5fadedbdf6422b409c87f06f068986f6f15716d7c6a")
        raw = json.loads(path.read_text())
        original = deserialize_artifact(raw)
        self.assertEqual(original.envelope.schema_version, "2.1.0")
        self.assertEqual(json.loads(serialize_artifact(original)), raw)
        # Existing readers must never consume v3 by dropping unfamiliar fields.
        raw["envelope"]["schema_version"] = "3.0.0"
        with self.assertRaises(IngestionValidationError):
            deserialize_artifact(raw)

    def test_optional_fields_and_nulls_need_no_body_review(self):
        for fields in ({}, {"factory_body": None, "factory_series": None},
                       {"canonical_powertrain": POWERTRAIN, "canonical_identity_contract": BASELINE_CONTRACT}):
            text = serialize_identity_fields("3.0.0", fields)
            self.assertEqual(deserialize_identity_fields("3.0.0", text), fields)

    def test_partial_engine_projection_is_a_draft_not_eligibility(self):
        fields = {"canonical_powertrain": POWERTRAIN | {"fuel_type": None}}
        validate_identity_fields("3.0.0", fields)

    def test_explicit_dispatch_rejects_legacy_and_unknown_versions(self):
        for version in ("2.1.0", "3.0.1", "4.0.0", None):
            with self.assertRaises(ValidationError):
                validate_identity_fields(version, {})

    def test_closed_fields_and_known_contract(self):
        for value in ({"unknown_fields": {}}, {"canonical_identity_contract": "vehicle-definition-body/1"},
                      {"canonical_powertrain": POWERTRAIN | {"engine_name": "extra"}}):
            with self.assertRaises(ValidationError):
                validate_identity_fields("3.0.0", value)

    def test_unresolved_parent_wire_details_cannot_be_silently_invented(self):
        for key in ("factory_body", "factory_series"):
            for value in ({}, {"uuid": "caller"}, {"dimensions": {"door_configuration": "two-door"}}):
                with self.assertRaises(UnresolvedV3Contract):
                    validate_identity_fields("3.0.0", {key: value})

    def test_projection_hash_is_stable_but_not_a_candidate_proof(self):
        a = {"factory_body": None, "canonical_powertrain": POWERTRAIN}
        b = dict(reversed(list(a.items())))
        self.assertEqual(identity_fields_digest("3.0.0", a), identity_fields_digest("3.0.0", b))
        self.assertNotEqual(identity_fields_digest("3.0.0", a), identity_fields_digest("3.0.0", {}))

    def test_duplicate_json_and_nonfinite_numbers_rejected(self):
        for text in ('{"factory_body":null,"factory_body":null}', '{"canonical_powertrain":NaN}', '[]'):
            with self.assertRaises(ValidationError):
                deserialize_identity_fields("3.0.0", text)

    def test_qualified_document_lineage_is_required(self):
        doc = {"source_id": "test", "raw_artifact_hash": "sha256:" + "a" * 64,
               "raw_artifact_reference": "not-opened.json", "extractor_id": "fixture",
               "extractor_version": "1", "extraction_mode": "manual", "assertion_set_id": "test-set",
               "assertions": [{"assertion_id": "door", "attribute_key": "doors",
                               "raw_value": "2-Door", "source_context": "fixture row"}]}
        ref = "|".join(("test", doc["raw_artifact_hash"], "test-set", "door"))
        interpretation = NormalizedInterpretation("test", ref, "door_configuration", "two-door")
        validate_qualified_interpretations([interpretation], [doc])
        interpretation.source_assertion_ref = "door"
        with self.assertRaises(ValidationError):
            validate_qualified_interpretations([interpretation], [doc])
        with self.assertRaises(ValidationError):
            validate_qualified_interpretations([], [])


class WranglerInventoryRegressionTests(SimpleTestCase):
    def test_readonly_inventory_has_21_without_doors_and_31_with_doors(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/ingestion/my2024_body_identity_projection.json").read_text())
        rows = fixture["rows"]
        self.assertEqual(len(rows), 31)
        self.assertEqual(sum(row["doors"] == "2-door" for row in rows), 10)
        self.assertEqual(sum(row["doors"] == "4-door" for row in rows), 21)
        without, with_doors = [], []
        for row in rows:
            value = baseline(trim_name=row["trim_name"], canonical_powertrain=row["powertrain"])
            without.append(semantic_digest(value))
            body = body_preimage(SCOPE, {"door_configuration": {"2-door": "two-door", "4-door": "four-door"}[row["doors"]]})
            with_doors.append(semantic_digest(value | {"body_digest": semantic_digest(body)}))
            self.assertNotIn("Unlimited", row["trim_name"])
        self.assertEqual(len(set(without)), 21)
        self.assertEqual(len(set(with_doors)), 31)
        self.assertEqual(len(rows) - len(set(without)), 10)
        self.assertTrue(any("Unlimited" in row["raw_trim"] for row in rows))
        root = Path(__file__).resolve().parents[2]
        for relative, expected in fixture["sources"].items():
            path = root / relative
            if path.exists():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
