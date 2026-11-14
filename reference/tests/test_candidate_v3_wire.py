"""Executable RA-046 vectors and boundaries; no operational data or approvals."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from django.test import SimpleTestCase

from reference.body_identity import body_preimage, compare_bodies, resolve_body_observation, semantic_digest
from reference.candidate_v3 import (
    CandidateV3Document, CandidateV3Error, baseline_identity_digest, candidate_hash,
    parse_candidate, pending_parent_checksum, serialize_candidate, validate_structure,
)
from reference.candidate_v3_evidence import validate_evidence

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures/ingestion/candidate_v3"
EXPECTED = {
    "A": "6544ca772bf73fa9fa337fac4c57c432ea1e097b14b69da674e7048304bdd845",
    "B": "64957e82777a10cf672c805988b93db8980698dbaedc0d819a132621e2fd7061",
    "C": "16fa47436f17f64fa0664fcbbad38623690ac243166d23c007da3bf9c14472bb",
    "D": "3023842810116dcad47684397a2287f060cc7c07c04d42755e677409e1a4bbc2",
    "E": "2570d7f349b1cc9a63444ac6d582841b5ad7e6c26ce9718d7058bec42dabe877",
    "F": "310737915dc3ea120c080ae4a15676403867fc15cd0875a3d14f75fa2cc81606",
    "G": "932586e2f1cc7831781dead71ba117a85bbbd1ebb19338ee6ffbee4f141266a2",
    "H": "085f3cf2dfd1743be5278b4605a86a00ceb476a6fc0797f3504e7932e7136afe",
}


def fixture(letter="G"):
    return json.loads((FIXTURES / (letter + ".json")).read_text())


def seal(c):
    c["candidate_hash"] = candidate_hash(c)
    return c


def independent_hash(v):
    return "sha256:" + hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


class CandidateV3WireTests(SimpleTestCase):
    def assertContract(self, c, code):
        with self.assertRaises(CandidateV3Error) as caught:
            parse_candidate(c)
        self.assertEqual(caught.exception.diagnostic.stage, "contract")
        self.assertEqual(caught.exception.diagnostic.code, code)
        return caught.exception.diagnostic

    def test_all_eight_exact_vectors_and_roundtrips(self):
        for letter, expected in EXPECTED.items():
            with self.subTest(letter=letter):
                c = fixture(letter)
                doc = parse_candidate(c)
                self.assertEqual(c["candidate_hash"], "sha256:" + expected)
                self.assertEqual(candidate_hash(doc), c["candidate_hash"])
                self.assertEqual(doc.to_dict(), json.loads(serialize_candidate(doc)))
                self.assertEqual(serialize_candidate(doc), serialize_candidate(parse_candidate(serialize_candidate(doc))))
                for kind in ("factory_body", "factory_series"):
                    if c[kind]:
                        self.assertEqual(c[kind]["identity"]["semantic_digest"], independent_hash(c[kind]["identity"]["preimage"]))

    def test_fixtures_are_copied_without_correcting_specification(self):
        text = (ROOT / "docs/architecture/designs/RA-046-Candidate-v3-Exact-Wire-Contract-Specification.md").read_text()
        blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
        self.assertEqual(len(blocks), 8)
        for letter, block in zip("ABCDEFGH", blocks):
            self.assertEqual((FIXTURES / (letter + ".json")).read_text(), block + "\n")

    def test_standalone_import_does_not_bootstrap_models_or_database(self):
        process = subprocess.run([sys.executable, "-c",
            "import sys; import reference.candidate_v3; import reference.candidate_v3_evidence; "
            "assert 'reference.models' not in sys.modules; assert 'django.db' not in sys.modules"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_no_body_ordinary_candidate_needs_no_placeholder(self):
        c = fixture("A")
        self.assertIsNone(c["factory_body"])
        self.assertIsNone(c["factory_series"])
        self.assertEqual(baseline_identity_digest(c), "sha256:e0e20c5d3fe167de1bf1ac5c769ffaae88101c3591d987f31f340a788277a906")
        report = validate_evidence(c)
        self.assertFalse(report.has_evidence_errors)
        self.assertFalse(any(d.path == "/factory_body" for d in report.diagnostics))

    def test_sparse_body_and_independent_series(self):
        c = fixture("F")
        self.assertEqual(set(c["factory_body"]["identity"]["preimage"]["dimensions"]),
                         {"wheelbase_designation", "body_length_designation", "roof_height_designation"})
        self.assertEqual(c["factory_body"]["disposition"], "pending")
        self.assertEqual(c["factory_series"]["disposition"], "existing")
        self.assertFalse(validate_evidence(c).has_evidence_errors)

    def test_existing_and_pending_are_distinct_closed_unions(self):
        c = fixture("D"); del c["factory_body"]["binding_revision"]
        self.assertContract(seal(c), "MISSING_FIELD")
        c = fixture("E"); c["factory_body"]["parent_uuid"] = fixture("D")["factory_body"]["parent_uuid"]
        self.assertContract(seal(c), "UNKNOWN_FIELD")
        c = fixture("G"); c["factory_body"]["disposition"] = "unresolved"
        self.assertContract(seal(c), "INVALID_TYPE")

    def test_door_digests_distinct_and_original_unlimited_preserved(self):
        a, b = fixture("B"), fixture("C")
        self.assertNotEqual(a["factory_body"]["identity"]["semantic_digest"], b["factory_body"]["identity"]["semantic_digest"])
        self.assertEqual(b["candidate_identity"]["trim_name"], "Sport")
        self.assertIn("Unlimited Sport", json.dumps(b["evidence_documents"]))
        for c in (a, b):
            self.assertFalse(validate_evidence(c).has_evidence_errors)
            self.assertIsNone(baseline_identity_digest(c))  # Draft engines, not eligible imports.

    def test_pending_checksum_expected_vector_and_verification(self):
        body = fixture("B")["factory_body"]
        expected = "sha256:a14bf5e2b2bd2f7b4cf303f686e886a3afcf5f7084f6384f9d623cdbdd643c01"
        self.assertEqual(pending_parent_checksum(body, expected=expected), expected)
        with self.assertRaises(CandidateV3Error): pending_parent_checksum(body, expected="sha256:" + "0" * 64)
        self.assertEqual(pending_parent_checksum(body), independent_hash(body))
        with self.assertRaises(CandidateV3Error): pending_parent_checksum(fixture("D")["factory_body"])

    def test_series_pending_checksum_has_no_new_wire_member(self):
        c = fixture("F"); p = c["factory_series"]
        p["disposition"] = "pending"; del p["parent_uuid"]; del p["binding_revision"]
        parse_candidate(seal(c))
        self.assertEqual(pending_parent_checksum(p, kind="series"), independent_hash(p))
        p["checksum"] = independent_hash(p)
        self.assertContract(seal(c), "UNKNOWN_FIELD")

    def test_unknown_fields_at_nested_boundaries(self):
        for select in (lambda c:c, lambda c:c["envelope"], lambda c:c["factory_body"],
                       lambda c:c["factory_body"]["identity"]["preimage"],
                       lambda c:c["evidence_documents"][0], lambda c:c["normalized_assertions"][0]):
            c = fixture(); select(c)["unexpected"] = True
            with self.subTest(select=select): self.assertContract(seal(c), "UNKNOWN_FIELD")

    def test_required_fields(self):
        c = fixture()
        for key in ("envelope", "candidate_reference", "canonical_scope", "drivetrain", "configuration_refs", "candidate_hash"):
            value = deepcopy(c); del value[key]
            with self.subTest(key=key): self.assertContract(value, "MISSING_FIELD")
        c = fixture(); del c["envelope"]["$schema"]
        self.assertContract(seal(c), "MISSING_FIELD")

    def test_nullable_optional_fields_omission_is_preserved(self):
        c = fixture("A")
        for k in ("factory_body", "factory_series", "canonical_powertrain"): del c[k]
        doc = parse_candidate(seal(c))
        self.assertNotIn("factory_body", doc.to_dict())
        self.assertIsNone(baseline_identity_digest(doc))

    def test_invalid_types_and_booleans_in_numbers(self):
        for field, value in (("model_year", True), ("trim_name", 4), ("market", [])):
            c = fixture(); c["candidate_identity"][field] = value
            with self.subTest(field=field): self.assertContract(seal(c), "INVALID_TYPE")
        c = fixture("A"); c["canonical_powertrain"]["engine_cylinders"] = True
        self.assertContract(seal(c), "INVALID_TYPE")

    def test_invalid_tokens(self):
        c = fixture(); c["canonical_scope"]["generation_key"] = "UPPER"
        self.assertContract(seal(c), "INVALID_TOKEN")
        c = fixture(); c["factory_body"]["identity"]["preimage"]["dimensions"]["roof_height_designation"] = " high"
        self.assertContract(seal(c), "INVALID_TOKEN")

    def test_duplicate_keys_include_exact_nested_path(self):
        text = (FIXTURES / "G.json").read_text().replace('"roof_height_designation": "high"', '"roof_height_designation": "high", "roof_height_designation": "low"')
        result = self.assertContract(text, "DUPLICATE_KEY")
        self.assertIn("/dimensions/roof_height_designation", result.path)
        self.assertContract('{"envelope":{},"envelope":{}}', "DUPLICATE_KEY")

    def test_duplicate_ids_and_noncanonical_order(self):
        c = fixture(); c["normalized_assertions"].append(deepcopy(c["normalized_assertions"][0]))
        self.assertContract(seal(c), "DUPLICATE_ID")
        c = fixture(); c["normalized_assertions"].reverse()
        self.assertContract(seal(c), "NONCANONICAL_ORDER")

    def test_dispatch_triple_and_normalizer_versions(self):
        for key, value in (("schema_version", "3.0.1"), ("artifact_type", "rigarchive.candidate_configuration.v2"), ("$schema", "other")):
            c = fixture(); c["envelope"][key] = value
            with self.subTest(key=key): self.assertContract(seal(c), "UNSUPPORTED_VERSION")
        c = fixture(); c["normalized_assertions"][0]["normalization"]["version"] = "2.0.0"
        self.assertContract(seal(c), "INVALID_TYPE")

    def test_invalid_decimal_and_nonfinite_numbers(self):
        for value in ("4.0", "NaN", "0", "3.333", 3.6):
            c = fixture("A"); c["canonical_powertrain"]["engine_displacement_liters"] = value
            with self.subTest(value=value): self.assertContract(seal(c), "INVALID_DECIMAL")
        for literal in ("NaN", "Infinity", "1e999"):
            text = (FIXTURES / "A.json").read_text().replace('"engine_cylinders": 6', '"engine_cylinders": ' + literal)
            with self.subTest(literal=literal): self.assertContract(text, "INVALID_TYPE")

    def test_invalid_hashes_and_preimages(self):
        c = fixture(); c["candidate_hash"] = "bad"
        self.assertContract(c, "INVALID_HASH")
        c = fixture(); c["factory_body"]["identity"]["preimage"]["dimensions"] = {}
        self.assertContract(seal(c), "INVALID_PREIMAGE")
        c = fixture(); c["factory_body"]["identity"]["preimage"]["dimensions"]["roof_height_designation"] = None
        self.assertContract(seal(c), "INVALID_TOKEN")

    def test_broken_local_reference_and_hash_inventory(self):
        c = fixture(); c["normalized_assertions"][0]["source_assertion_ref"] += "missing"
        self.assertContract(seal(c), "BROKEN_REFERENCE")
        c = fixture(); c["evidence_raw_hashes"] = ["sha256:" + "0" * 64]
        self.assertContract(seal(c), "BROKEN_REFERENCE")

    def test_semantic_and_whole_candidate_hash_failures_are_distinct(self):
        c = fixture(); c["factory_body"]["identity"]["semantic_digest"] = "sha256:" + "0" * 64
        self.assertContract(seal(c), "SEMANTIC_DIGEST_MISMATCH")
        c = fixture(); c["candidate_reference"] += "-changed"
        self.assertContract(c, "ARTIFACT_HASH_MISMATCH")

    def test_unicode_preserved_and_surrogate_rejected(self):
        c = fixture(); c["envelope"]["generator"] = "é"
        output = serialize_candidate(parse_candidate(seal(c)))
        self.assertIn("é", output); self.assertNotIn("\\u00e9", output)
        other = deepcopy(c); other["envelope"]["generator"] = "e\u0301"
        self.assertNotEqual(candidate_hash(c), candidate_hash(other))
        c["envelope"]["generator"] = "\ud800"
        self.assertContract(c, "INVALID_TYPE")

    def test_object_key_order_not_raw_array_order(self):
        c = fixture(); reversed_ = dict(reversed(list(c.items())))
        self.assertEqual(candidate_hash(c), candidate_hash(reversed_))
        c["evidence_documents"][0]["assertions"][0]["raw_value"]["ordered"] = [1, 2]
        h = candidate_hash(c)
        c["evidence_documents"][0]["assertions"][0]["raw_value"]["ordered"].reverse()
        self.assertNotEqual(candidate_hash(c), h)

    def test_optional_metadata_changes_artifact_not_body_meaning(self):
        c = fixture(); body = c["factory_body"]["identity"]["semantic_digest"]
        old = c["candidate_hash"]; c["envelope"]["created_at"] = "2026-11-13T15:00:00Z"
        parse_candidate(seal(c))
        self.assertNotEqual(old, c["candidate_hash"])
        self.assertEqual(body, c["factory_body"]["identity"]["semantic_digest"])

    def test_returned_dictionary_does_not_mutate_document(self):
        doc = parse_candidate(fixture()); value = doc.to_dict(); value["candidate_reference"] = "changed"
        self.assertNotEqual(value, doc.to_dict()); serialize_candidate(doc)

    def test_all_seven_body_dimensions_and_namespaced_codes(self):
        c = fixture(); d = c["factory_body"]["identity"]["preimage"]["dimensions"]
        for key in ("body_style", "wheelbase_designation", "body_length_designation", "door_configuration", "side_door_arrangement"):
            d[key] = "example"
        d["body_code"] = {"namespace": "example", "token": "code"}
        c["factory_body"]["identity"]["semantic_digest"] = semantic_digest(c["factory_body"]["identity"]["preimage"])
        parse_candidate(seal(c))  # Unsupported additions are an evidence failure, not schema failure.
        self.assertTrue(validate_evidence(c).has_evidence_errors)

    def test_optional_retained_technical_shapes_are_closed(self):
        c = fixture("A")
        c["normalized_technical_details"] = {"engine": {"displacement": {"normalized_value": "4", "normalized_unit": "L"}},
            "transmission": {"speeds": 5}, "drivetrain_details": {"generic_classification": "4WD", "components": [
                {"component_type": "transfer_case", "name": "Example", "low_range_ratio": 2.72, "extra_properties": {"inert": [1]}}],
                "operating_modes": [{"mode_code": "low", "name": "Low", "low_range": True}]}}
        c["packages_and_options"] = [{"name": "Example", "is_distinct_trim_identity": False}]
        c["reconciliation_and_review"] = {"attribute_states": {"trim_name": {"reconciliation_state": "single_source", "review_disposition": "not_required"}}}
        parse_candidate(seal(c))
        c["normalized_technical_details"]["engine"]["body"] = "bad"
        self.assertContract(seal(c), "UNKNOWN_FIELD")

    def test_pending_equivalence_and_series_equivalence_not_allowed(self):
        c = fixture(); c["factory_body"]["support"]["equivalence_interpretation_ref"] = "id"
        self.assertContract(seal(c), "INVALID_TYPE")
        c = fixture("F"); c["factory_series"]["support"]["equivalence_interpretation_ref"] = "id"
        self.assertContract(seal(c), "INVALID_TYPE")

    def test_bad_paths_timestamps_uuid_and_locator(self):
        for path in ("../secret", "/absolute", "a//b", "a/./b", "a\\b", "https://example.com"):
            c = fixture(); c["evidence_documents"][0]["raw_artifact_reference"] = path
            with self.subTest(path=path): self.assertContract(seal(c), "INVALID_TYPE")
        c = fixture(); c["envelope"]["created_at"] = "2026-02-30T00:00:00Z"
        self.assertContract(seal(c), "INVALID_TYPE")
        c = fixture("D"); c["factory_body"]["parent_uuid"] = "00000000-0000-0000-0000-000000000000"
        self.assertContract(seal(c), "INVALID_TYPE")
        c = fixture(); c["reviewed_findings"] = [{"finding_id": "review", "artifact_type": "workflow_review", "artifact_version": "1.0",
            "artifact_reference": "review.txt", "artifact_hash": "sha256:" + "a" * 64,
            "locator": {"kind": "json_pointer", "pointer": "/~2"}, "applicability_ref": "app"}]
        self.assertContract(seal(c), "INVALID_TYPE")

    def test_relative_posix_path_can_have_colon_after_directory(self):
        c = fixture(); c["evidence_documents"][0]["raw_artifact_reference"] = "docs/data:record.json"
        parse_candidate(seal(c))

    def test_baseline_math_distinguishes_body_without_granting_evidence_acceptance(self):
        hashes = []
        for doors in ("two-door", "four-door"):
            c = fixture("A")
            pre = body_preimage(c["canonical_scope"], {"door_configuration": doors})
            c["factory_body"] = {"disposition": "pending", "identity": {"preimage": pre, "semantic_digest": semantic_digest(pre)},
                "support": {"applicability_ref": "app", "configuration_refs": c["configuration_refs"], "interpretation_refs": [], "equivalence_interpretation_ref": None}}
            seal(c)
            hashes.append(baseline_identity_digest(c))
            self.assertTrue(validate_evidence(c).has_evidence_errors)
        self.assertNotEqual(*hashes)


class CandidateV3EvidenceTests(SimpleTestCase):
    def codes(self, c):
        validate_structure(c)
        return {(d.stage, d.code) for d in validate_evidence(c).diagnostics}

    def test_error_free_reports_retain_dependencies_without_acceptance_or_authority(self):
        for letter in "ABCDEFGH":
            with self.subTest(letter=letter):
                report = validate_evidence(fixture(letter))
                self.assertFalse(report.has_evidence_errors)
                self.assertTrue(report.dependencies)
                for name in ("supplied_projection_supported", "supported", "validated",
                             "accepted", "eligible", "import_eligible", "authorized",
                             "evidence_accepted", "resolution_approved", "publication_eligible"):
                    self.assertFalse(hasattr(report, name), name)

    def test_correctly_hashed_unsupported_body_is_evidence_failure(self):
        c = fixture(); c["factory_body"]["identity"]["preimage"]["dimensions"]["roof_height_designation"] = "low"
        c["factory_body"]["identity"]["semantic_digest"] = semantic_digest(c["factory_body"]["identity"]["preimage"])
        codes = self.codes(seal(c))
        self.assertIn(("evidence", "PROJECTION_MISMATCH"), codes)
        self.assertFalse(any(stage == "contract" for stage, _ in codes))

    def test_wrong_applicability_does_not_change_schema_validity(self):
        c = fixture(); c["applicability"][0]["start_year"] = 2023; c["applicability"][0]["end_year"] = 2023
        self.assertIn(("evidence", "APPLICABILITY_MISMATCH"), self.codes(seal(c)))

    def test_findings_scope_is_not_accepted_from_a_reference(self):
        c = fixture(); other = deepcopy(c["applicability"][0]); other["applicability_id"] = "other"
        other["start_year"] = other["end_year"] = 2023; c["applicability"].append(other)
        c["reviewed_findings"] = [{"finding_id": "review", "artifact_type": "generation_correspondence_review", "artifact_version": "1.0",
            "artifact_reference": "not-supplied/review.json", "artifact_hash": "sha256:" + "a" * 64,
            "locator": {"kind": "json_pointer", "pointer": ""}, "applicability_ref": "other"}]
        c["normalized_assertions"][0]["finding_refs"] = ["review"]
        self.assertIn(("evidence", "FINDING_SCOPE_MISMATCH"), self.codes(seal(c)))

    def test_contradictory_interpretations_for_one_configuration(self):
        c = fixture(); i = deepcopy(next(i for i in c["normalized_assertions"] if i["target_attribute_key"] == "factory_body.roof_height_designation"))
        i["interpretation_id"] = "z-conflict"; i["normalized_concept"] = "low"
        c["normalized_assertions"].append(i)
        self.assertIn(("evidence", "SOURCE_CONFLICT"), self.codes(seal(c)))

    def test_same_document_scalars_do_not_create_coexistence(self):
        c = fixture(); doc = c["evidence_documents"][0]
        doc["assertions"].append({"assertion_id": "separate", "attribute_key": "roof", "raw_value": "high", "source_context": "A different configuration in the same table"})
        i = next(i for i in c["normalized_assertions"] if i["target_attribute_key"] == "factory_body.roof_height_designation")
        i["source_assertion_ref"] = c["configuration_refs"][0].rsplit("|", 1)[0] + "|separate"
        self.assertIn(("evidence", "COEXISTENCE_NOT_ESTABLISHED"), self.codes(seal(c)))

    def test_alternative_configurations_cannot_be_joined_by_shared_document(self):
        c = fixture(); doc = c["evidence_documents"][0]
        raw = deepcopy(doc["assertions"][0]["raw_value"]); raw["factory_body.roof_height_designation"] = "low"
        doc["assertions"].append({"assertion_id": "other", "attribute_key": "configuration", "raw_value": raw, "source_context": "Different alternative"})
        i = next(i for i in c["normalized_assertions"] if i["target_attribute_key"] == "factory_body.roof_height_designation")
        i["source_assertion_ref"] = c["configuration_refs"][0].rsplit("|", 1)[0] + "|other"
        self.assertIn(("evidence", "COEXISTENCE_NOT_ESTABLISHED"), self.codes(seal(c)))

    def test_legitimate_composite_grouping_supports_multiple_fields(self):
        self.assertFalse(validate_evidence(fixture("F")).has_evidence_errors)
        c = fixture("A")
        self.assertEqual(len({i["source_assertion_ref"] for i in c["normalized_assertions"]}), 1)
        self.assertFalse(validate_evidence(c).has_evidence_errors)

    def test_claimed_qualified_cross_source_linkage_is_a_decoder_dependency(self):
        c = fixture(); second = deepcopy(c["evidence_documents"][0]); second["source_id"] = "z_other_source"
        second["assertion_set_id"] = "other-set"; second["assertions"] = [{"assertion_id": "roof", "attribute_key": "roof", "raw_value": "high", "source_context": "Configuration with explicit source cross-reference"}]
        c["evidence_documents"].append(second)
        link = {"assertion_id": "link", "attribute_key": "configuration_cross_reference", "raw_value": "Explicit native configuration reference to the other source", "source_context": "Qualified cross-reference"}
        c["evidence_documents"][0]["assertions"].append(link)
        stem = c["configuration_refs"][0].rsplit("|", 1)[0]
        c["applicability"][0]["source_assertion_refs"].append(stem + "|link")
        ref = "|".join((second["source_id"], second["raw_artifact_hash"], second["assertion_set_id"], "roof"))
        i = next(i for i in c["normalized_assertions"] if i["target_attribute_key"] == "factory_body.roof_height_designation")
        i["source_assertion_ref"] = ref
        report = validate_evidence(seal(c))
        self.assertFalse(report.has_evidence_errors)
        self.assertTrue(any("cross-source grouping" in d.message for d in report.dependencies))
        # A declaration is NOT successful source linkage acceptance or permission to join.

    def test_missing_bytes_are_dependencies_not_source_contradictions(self):
        report = validate_evidence(fixture("A"))
        self.assertIn("UNAVAILABLE_ARTIFACT", {d.code for d in report.dependencies})
        self.assertFalse(report.has_evidence_errors)

    def test_supplied_wrong_bytes_do_not_count_as_verified_source(self):
        c = fixture("A"); d = c["evidence_documents"][0]
        result = validate_evidence(c, retained_artifacts={d["raw_artifact_reference"]: b"changed"})
        self.assertTrue(any("bytes changed" in d.message for d in result.dependencies))
        self.assertFalse(result.has_evidence_errors)

    def test_known_discriminator_cannot_be_omitted_from_projection(self):
        c = fixture("B"); c["factory_body"] = None
        self.assertIn(("evidence", "KNOWN_DISCRIMINATOR_OMITTED"), self.codes(seal(c)))
        c["normalized_assertions"] = [i for i in c["normalized_assertions"] if not i["target_attribute_key"].startswith("factory_body.")]
        self.assertIn(("evidence", "KNOWN_DISCRIMINATOR_OMITTED"), self.codes(seal(c)))

    def test_series_role_and_trim_are_independent(self):
        c = fixture("F"); role = next(i for i in c["normalized_assertions"] if i["target_attribute_key"] == "factory_series.identity_role")
        c["factory_series"]["support"]["interpretation_refs"].remove(role["interpretation_id"])
        self.assertIn(("evidence", "PROJECTION_MISMATCH"), self.codes(seal(c)))

    def test_existing_binding_is_always_a_later_dependency(self):
        c = fixture("D"); result = validate_evidence(c)
        self.assertTrue(any(d.path.endswith("binding_revision") for d in result.dependencies))
        self.assertFalse(hasattr(result, "parent_uuid"))

    def test_partial_peer_order_does_not_choose_a_parent(self):
        c = fixture("H"); pre = c["factory_body"]["identity"]["preimage"]
        peers = [body_preimage(pre["scope"], pre["dimensions"] | {"wheelbase_designation": v}) for v in ("long", "short")]
        a = resolve_body_observation(pre, peers); b = resolve_body_observation(pre, list(reversed(peers)))
        self.assertEqual(a, b); self.assertTrue(a.requires_review)
        self.assertEqual(c["factory_body"]["disposition"], "pending")

    def test_new_digest_does_not_prove_distinct_identity(self):
        c = fixture("G"); pre = c["factory_body"]["identity"]["preimage"]
        richer = body_preimage(pre["scope"], pre["dimensions"] | {"wheelbase_designation": "long"})
        self.assertNotEqual(semantic_digest(pre), semantic_digest(richer))
        self.assertEqual(compare_bodies(pre, richer).relation, "compatible")
        self.assertTrue(any("no create/reuse disposition" in d.message for d in validate_evidence(c).dependencies))

    def test_individually_positive_alternative_rows_do_not_establish_joint_tuple(self):
        c = fixture(); doc = c["evidence_documents"][0]
        other = deepcopy(doc["assertions"][0]["raw_value"])
        del other["factory_body.roof_height_designation"]
        other["engine_displacement_liters"] = "2"
        doc["assertions"].append({"assertion_id": "other", "attribute_key": "configuration", "raw_value": other, "source_context": "Alternative configuration"})
        ref = c["configuration_refs"][0].rsplit("|", 1)[0] + "|other"
        c["configuration_refs"].append(ref)
        c["applicability"][0]["configuration_refs"].append(ref)
        c["applicability"][0]["source_assertion_refs"].append(ref)
        i = deepcopy(c["normalized_assertions"][0])
        i.update(interpretation_id="z-engine", source_assertion_ref=ref,
                 target_attribute_key="engine_displacement_liters", normalized_concept="2")
        c["normalized_assertions"].append(i)
        c["canonical_powertrain"] = dict.fromkeys(("engine_displacement_liters", "engine_cylinders", "engine_aspiration", "fuel_type", "electrification_type"))
        c["canonical_powertrain"]["engine_displacement_liters"] = "2"
        self.assertIn(("evidence", "COEXISTENCE_NOT_ESTABLISHED"), self.codes(seal(c)))

    def test_complete_existing_equivalence_remains_dependency_not_missing_basis_error(self):
        c = fixture("D"); parent = c["factory_body"]
        parent["identity"]["preimage"]["dimensions"]["wheelbase_designation"] = "long"
        parent["identity"]["semantic_digest"] = semantic_digest(parent["identity"]["preimage"])
        i = deepcopy(c["normalized_assertions"][0])
        i.update(interpretation_id="z-equivalence", target_attribute_key="body_identity_equivalence",
                 normalized_concept=parent["identity"]["semantic_digest"], normalization={"id": "existing_body_equivalence", "version": "1.0.0"})
        c["normalized_assertions"].append(i)
        parent["support"]["equivalence_interpretation_ref"] = i["interpretation_id"]
        report = validate_evidence(seal(c))
        self.assertFalse(report.has_evidence_errors)
        self.assertTrue(any("immutable alias/binding" in d.message for d in report.dependencies))

    def test_generation_projection_is_preserved_not_source_code_inference(self):
        c = fixture("B"); c["generation_evidence"] = []
        self.assertIn(("evidence", "PROJECTION_MISMATCH"), self.codes(seal(c)))

    def test_null_source_generation_is_not_the_literal_identifier_none(self):
        c = fixture("B")
        next(a for a in c["evidence_documents"][0]["assertions"] if a["attribute_key"] == "source_model_code")["raw_value"] = None
        c["generation_evidence"][0]["native_identifier"] = "None"
        self.assertIn(("evidence", "PROJECTION_MISMATCH"), self.codes(seal(c)))

    def test_complete_qualified_cross_source_configurations_do_not_require_attribute_join(self):
        c = fixture("A")
        other = deepcopy(c["evidence_documents"][0]); other["source_id"] = "z_other_source"
        other["assertion_set_id"] = "other-set"; other["raw_artifact_reference"] = "other-source.json"
        c["evidence_documents"].append(other)
        q = "|".join((other["source_id"], other["raw_artifact_hash"], other["assertion_set_id"], "configuration"))
        c["configuration_refs"].append(q)
        c["applicability"][0]["configuration_refs"].append(q)
        c["applicability"][0]["source_assertion_refs"].append(q)
        for original in list(c["normalized_assertions"]):
            i = deepcopy(original); i["interpretation_id"] = "z-" + i["interpretation_id"]; i["source_assertion_ref"] = q
            c["normalized_assertions"].append(i)
        result = validate_evidence(seal(c))
        self.assertFalse(result.has_evidence_errors)
        # Each source independently asserts the COMPLETE positive tuple; attributes
        # are not combined across unrelated rows based on equality or shared files.
        self.assertFalse(any("cross-source grouping" in d.message for d in result.dependencies))

    def test_stale_historical_finding_cannot_approve_a_v3_base(self):
        c = fixture()
        content = json.dumps({"evidence_anchors": {"candidate_hash": "sha256:" + "0" * 64},
                              "adjudication_decision": "approved_classifications"}).encode()
        c["reviewed_findings"] = [{"finding_id": "review", "artifact_type": "canonical_import_adjudication", "artifact_version": "1.1",
            "artifact_reference": "review.json", "artifact_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
            "locator": {"kind": "json_pointer", "pointer": ""}, "applicability_ref": "app"}]
        seal(c)
        report = validate_evidence(c, retained_artifacts={"review.json": content})
        self.assertIn("FINDING_SCOPE_MISMATCH", {d.code for d in report.diagnostics})

    def test_unknown_review_decoders_are_dependencies_not_claimed_approval(self):
        c = fixture()
        content = b"Some historical workflow finding; not machine approval"
        c["reviewed_findings"] = [{"finding_id": "review", "artifact_type": "workflow_review", "artifact_version": "not-supported",
            "artifact_reference": "review.txt", "artifact_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
            "locator": {"kind": "utf8_lines", "start_line": 1, "end_line": 1}, "applicability_ref": "app"}]
        seal(c)
        report = validate_evidence(c, retained_artifacts={"review.txt": content})
        self.assertFalse(report.has_evidence_errors)
        self.assertIn("UNSUPPORTED_REVIEW_VERSION", {d.code for d in report.dependencies})

    def test_normalization_registry_rules_preserve_explicit_support(self):
        from reference.candidate_v3_evidence import _terms
        scope = fixture("B")["canonical_scope"]
        self.assertTrue(_terms("3.6L V6", "engine_displacement_liters", "3.6", scope))
        self.assertTrue(_terms("3.6L V6", "engine_cylinders", 6, scope))
        self.assertTrue(_terms("eTorque", "electrification_type", "mild_hybrid", scope))
        self.assertTrue(_terms("4xe", "electrification_type", "plug_in_hybrid", scope))
        self.assertFalse(_terms("ESS", "electrification_type", "none", scope))
        self.assertFalse(_terms("gas", "fuel_type", "gasoline", scope))

    def test_technical_contradiction_is_evidence_not_structural_failure(self):
        c = fixture("A"); c["normalized_technical_details"] = {"drivetrain_details": {"generic_classification": "AWD"}}
        self.assertIn(("evidence", "PROJECTION_MISMATCH"), self.codes(seal(c)))


class CandidateV3LegacyCompatibilityTests(SimpleTestCase):
    def test_direct_legacy_readers_and_writers_reject_v3(self):
        from reference.ingestion.serialization import candidate_config_doc_from_dict, candidate_config_doc_to_dict, deserialize_artifact
        from reference.ingestion.validation import IngestionValidationError
        with self.assertRaises(IngestionValidationError): candidate_config_doc_from_dict(fixture("B"))
        p = Path(__file__).parent / "fixtures/ingestion/historical_jl24_candidate_2_1_0.json"
        legacy = deserialize_artifact(p.read_text())
        legacy.envelope.schema_version = "3.0.0"
        with self.assertRaises(IngestionValidationError): candidate_config_doc_to_dict(legacy)

    def test_explicit_shared_serialization_dispatch(self):
        from reference.ingestion.serialization import deserialize_artifact, serialize_artifact
        from reference.ingestion.validation import validate_artifact
        c = fixture("B"); obj = deserialize_artifact(json.dumps(c))
        self.assertIsInstance(obj, CandidateV3Document)
        validate_artifact(obj)
        self.assertEqual(json.loads(serialize_artifact(obj)), c)
        text = (FIXTURES / "B.json").read_text().replace('"trim_name": "Sport"', '"trim_name": "Sport", "trim_name": "Sport"')
        with self.assertRaises(CandidateV3Error): deserialize_artifact(text)

    def test_pinned_historical_21_fixture_unchanged(self):
        from reference.ingestion.serialization import deserialize_artifact, serialize_artifact
        p = Path(__file__).parent / "fixtures/ingestion/historical_jl24_candidate_2_1_0.json"
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), "2f341d71c8cc7aee323ad5fadedbdf6422b409c87f06f068986f6f15716d7c6a")
        original = json.loads(p.read_text()); restored = deserialize_artifact(original)
        self.assertEqual(json.loads(serialize_artifact(restored)), original)

    def test_legacy_reader_does_not_treat_v3_as_legacy_candidate(self):
        from reference.ingestion.serialization import deserialize_artifact
        from reference.ingestion.validation import IngestionValidationError
        c = fixture(); c["envelope"]["artifact_type"] = "rigarchive.candidate_configuration.v2"
        with self.assertRaises(IngestionValidationError): deserialize_artifact(c)
