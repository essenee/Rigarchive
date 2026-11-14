"""RA-049 closed JSON contracts. Validation/hashes grant no execution authority."""
from copy import deepcopy
import hashlib
import json
import math
import re
from datetime import datetime

from django.core.exceptions import ValidationError

from reference import candidate_v3 as wire
from reference.body_identity import canonical_json, semantic_digest, validate_preimage, body_preimage, compare_bodies
from reference.powertrain import FIELDS, validate_powertrain

VERSION = "3.0.0"
PROFILE = "my2024-wrangler-jl-consumer/1"
ATTRIBUTES = ("body_style", "wheelbase_designation", "body_length_designation", "roof_height_designation",
              "door_configuration", "side_door_arrangement", "body_code", "body_code_namespace")


class ContractError(ValidationError):
    pass


def require(ok, message):
    if not ok:
        raise ContractError(message)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def content_hash(value, field):
    return digest({k: v for k, v in value.items() if k != field})


def seal(value, field):
    """Builder operation only: callers must validate the newly built complete object."""
    result = deepcopy(value)
    result[field] = content_hash(result, field)
    return result


def nullable(schema):
    return ("nullable", schema)


def array(schema, key, minimum=0):
    return ("array", schema, key, minimum)


def enum(*values):
    return ("enum", values)


def constant(value):
    return ("constant", value)


def _json(value):
    if type(value) is float:
        require(math.isfinite(value), "Nonfinite number.")
    elif type(value) is str:
        value.encode("utf-8")
    elif type(value) is list:
        for item in value:
            _json(item)
    elif type(value) is dict:
        require(all(type(k) is str for k in value), "JSON object keys must be strings.")
        for item in value.values():
            _json(item)
    else:
        require(value is None or type(value) in (int, bool), "Not a JSON value.")


def _scalar(name, value):
    validators = {"Text": wire.text, "Token": wire.token, "UUID": wire.uuid_value,
                  "Hash": wire.hash_value, "Int": wire.positive, "Year": wire.year,
                  "Timestamp": wire.timestamp, "RefPath": wire.retained_path}
    if name in validators:
        validators[name](value, "/")
        if name == "Timestamp":
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            require(value == parsed.isoformat(timespec="microseconds" if parsed.microsecond else "seconds").replace("+00:00", "Z"), "Noncanonical timestamp.")
    elif name == "Bool":
        require(type(value) is bool, "Expected boolean.")
    elif name in ("Powertrain", "DraftPowertrain"):
        require(type(value) is dict and set(value) == set(FIELDS), "Exact five-field powertrain required.")
        validate_powertrain(value, complete=name == "Powertrain")
        # Existing validator accepts Decimal for ORM use. The wire requires decimal strings.
        require(value[FIELDS[0]] is None or type(value[FIELDS[0]]) is str, "Decimal must be a canonical string.")
        require(value[FIELDS[1]] is None or type(value[FIELDS[1]]) is int, "Cylinder count must be integer.")
    elif name == "Candidate":
        wire.validate_structure(value)
    elif name in ("BodyPreimage", "Baseline"):
        validate_preimage(value)
        require(value["identity_contract"] == {"BodyPreimage": "factory-body-semantic/2", "Baseline": "vehicle-definition-body/2"}[name], "Wrong semantic contract.")
    elif name == "ReviewPayload":
        # Only known original readers are admitted by ReviewedArtifact's semantic check.
        require(type(value) is dict, "Expected original reviewed object.")
    elif name == "CorrespondenceReview":
        from reference.ingestion.generation_correspondence import validate_review_payload
        validate_review_payload(value)
    elif name == "StoredText":
        require(type(value) is str and len(value) <= 100, "Stored text exceeds 100 characters.")
    else:
        raise ContractError("Unknown schema: " + name)


def _check(schema, value, path="/"):
    if isinstance(schema, str):
        if schema in SCHEMAS:
            _check(SCHEMAS[schema], value, path)
            _semantic(schema, value)
        else:
            _scalar(schema, value)
    elif type(schema) is dict:
        require(type(value) is dict and set(value) == set(schema), f"{path}: unexpected or missing fields.")
        for name, child in schema.items():
            _check(child, value[name], path.rstrip("/") + "/" + name)
    elif schema[0] == "nullable":
        if value is not None:
            _check(schema[1], value, path)
    elif schema[0] == "constant":
        require(type(value) is type(schema[1]) and value == schema[1], path + ": wrong constant.")
    elif schema[0] == "enum":
        require(type(value) is str and value in schema[1], path + ": unsupported value.")
    elif schema[0] == "array":
        require(type(value) is list and len(value) >= schema[3], path + ": invalid array.")
        for item in value:
            _check(schema[1], item, path)
        keys = [schema[2](item) for item in value]
        require(keys == sorted(keys) and len(keys) == len(set(keys)), path + ": noncanonical order or duplicate identity.")
    else:
        raise ContractError("Invalid schema definition.")


PARENT = {"pk": "Int", "uuid": "UUID"}
SCOPE = {key: "Token" for key in ("manufacturer_key", "model_key", "generation_key")}
STORED = {"model_year": "Year", "trim_name": "StoredText", "engine_name": "StoredText",
          "drivetrain": enum("2WD", "4WD", "AWD", "UNK"), "market": enum("US", "CA", "OT"), "canonical_powertrain": "DraftPowertrain"}
TARGET = {**STORED, "model_year": constant(2024), "trim_name": "Text", "engine_name": "Text",
          "drivetrain": constant("4WD"), "market": constant("US"), "canonical_powertrain": "Powertrain",
          "factory_body_configuration_uuid": nullable("UUID")}
SCHEMAS = {
    "Parent": PARENT,
    "ScopeResolution": {"manufacturer": "Parent", "vehicle_model": "Parent", "generation": "Parent", "canonical_scope": SCOPE, "model_year": constant(2024), "market": constant("US")},
    "BodyTuple": {key: nullable("Token") for key in ATTRIBUTES},
    "BodyState": {"pk": "Int", "uuid": "UUID", "generation_uuid": "UUID", "attributes": "BodyTuple", "updated_at": "Timestamp", "semantic_preimage": "BodyPreimage", "semantic_digest": "Hash"},
    "TargetFields": TARGET,
    "ArtifactPin": {"reference": "RefPath", "byte_hash": "Hash"},
    "ReviewedArtifact": {"reference": "RefPath", "byte_hash": "Hash", "reader": "Token", "reader_version": "Text", "snapshot": "ReviewPayload"},
    "EvidenceState": {"artifact_pins": array("ArtifactPin", lambda x: (x["reference"], x["byte_hash"])), "reviewed_artifacts": array("ReviewedArtifact", lambda x: x["reference"])},
    "CorrespondenceState": {"revision_uuid": "UUID", "review_payload": "CorrespondenceReview", "content_hash": "Hash", "successor_uuid": nullable("UUID")},
    "ParentState": {"manufacturer_id": "Int", "manufacturer_uuid": "UUID", "manufacturer_name": "Text", "manufacturer_active": "Bool",
                    "vehicle_model_id": "Int", "vehicle_model_uuid": "UUID", "vehicle_model_name": "Text", "vehicle_model_active": "Bool",
                    "generation_id": "Int", "generation_uuid": "UUID", "generation_active": "Bool", "generation_model_id": "Int", "start_year": "Year", "end_year": nullable("Year")},
    "GenerationState": {"scope": "ScopeResolution", "parent_state": "ParentState", "correspondences": array("CorrespondenceState", lambda x: x["revision_uuid"], 1)},
    "FamilyMember": {"candidate_reference": "Text", "candidate_hash": "Hash", "baseline_preimage": "Baseline", "baseline_digest": "Hash", "body_attributes": "BodyTuple", "target_fields": "TargetFields", "legacy_base_slug": "Text"},
    "FamilyState": {"profile": constant(PROFILE), "release_members": array("FamilyMember", lambda x: x["candidate_reference"], 31), "release_evidence": "EvidenceState"},
    "VehicleState": {"pk": "Int", "uuid": "UUID", "generation_uuid": "UUID", "is_active": "Bool", "slug": "Text", "fields": STORED, "body": nullable("BodyState")},
    "PeerAssessment": {"vehicle": "VehicleState", "body_basis": nullable("BodyPreimage"), "powertrain_basis": nullable("Powertrain"), "relation": enum("equal", "distinct", "unresolved", "irrelevant"), "receipt_uuid": nullable("UUID"), "receipt_snapshot_hash": nullable("Hash"), "supporting_candidates": array("Candidate", lambda x: x["candidate_reference"]), "evidence": "EvidenceState"},
    "SlugOccupancy": {"slug": "Text", "owners": array("VehicleState", lambda x: x["uuid"])},
    "SlugOwner": {"slug": "Text", "uuid": "UUID", "is_active": "Bool"},
    "Diagnostic": {"stage": enum("contract", "evidence", "dependency", "resolution"), "code": "Text", "path": "Text", "message": "Text"},
    "AuthorizationRow": {"candidate_reference": "Text", "candidate_hash": "Hash", "plan_hash": "Hash", "action": enum("create", "no_op"), "existing_vehicle_uuid": nullable("UUID"), "target_slug": "Text", "baseline_digest": "Hash", "body_uuid": "UUID"},
    "RevalidatedRow": {"candidate_reference": "Text", "plan_hash": "Hash", "proof_hash": "Hash", "baseline_digest": "Hash", "body_state_hash": "Hash"},
    "Approval1": {"approval_version": constant("1.0"), "matrix_digest": "Hash", "decision": constant("approved"), "operator": "Text", "approved_at_utc": "Timestamp"},
}
DIAGNOSTICS = array("Diagnostic", lambda x: (x["stage"], x["code"], x["path"]))
SCHEMAS.update({
    "Proof3": {"proof_version": constant(VERSION), "profile": constant(PROFILE), "candidate_hash": "Hash", "generation_state_hash": "Hash", "body_state_hash": "Hash", "body_namespace": array("BodyState", lambda x: x["uuid"]), "evidence_state_hash": "Hash", "baseline_preimage": "Baseline", "baseline_digest": "Hash", "family": "FamilyState", "peers": array("PeerAssessment", lambda x: x["vehicle"]["uuid"]), "slug_occupancy": array("SlugOccupancy", lambda x: x["slug"]), "generation_slugs": array("SlugOwner", lambda x: (x["slug"], x["uuid"])), "conclusion": enum("create", "no_op", "blocked"), "existing_vehicle_uuid": nullable("UUID"), "proof_hash": "Hash"},
    "Plan3": {"plan_version": constant(VERSION), "profile": constant(PROFILE), "candidate_reference": "Text", "candidate_snapshot": "Candidate", "candidate_hash": "Hash", "generation": "GenerationState", "body": "BodyState", "body_action": constant("reuse"), "evidence": "EvidenceState", "target_fields": "TargetFields", "target_slug": "Text", "action": enum("create", "no_op", "blocked"), "existing_vehicle_uuid": nullable("UUID"), "proof": "Proof3", "diagnostics": DIAGNOSTICS, "plan_hash": "Hash"},
    "Assessment3": {"assessment_version": constant(VERSION), "candidate_reference": "Text", "candidate_hash": nullable("Hash"), "diagnostics": array("Diagnostic", lambda x: (x["stage"], x["code"], x["path"]), 1)},
    "Matrix3": {"matrix_version": constant(VERSION), "profile": constant(PROFILE), "scope": "ScopeResolution", "family_hash": "Hash", "body_writes": constant(False), "rows": array("AuthorizationRow", lambda x: x["candidate_reference"], 1)},
    "Manifest3": {"manifest_version": constant(VERSION), "matrix": "Matrix3", "matrix_digest": "Hash", "approval": "Approval1", "approval_hash": "Hash", "manifest_hash": "Hash"},
    "Revalidation3": {"revalidation_version": constant(VERSION), "manifest_hash": "Hash", "matrix_digest": "Hash", "approval_hash": "Hash", "family_hash": "Hash", "rows": array("RevalidatedRow", lambda x: x["candidate_reference"], 1), "result": enum("valid", "stale"), "diagnostics": DIAGNOSTICS, "revalidation_hash": "Hash"},
    "Receipt3": {"receipt_version": constant(VERSION), "profile": constant(PROFILE), "manifest": "Manifest3", "plan": "Plan3", "revalidation": "Revalidation3", "outcome": enum("created", "no_op"), "vehicle": {"pk": "Int", "uuid": "UUID", "slug": "Text"}, "persisted_fields": "TargetFields", "execution_agent": "Text", "executed_at_utc": "Timestamp", "snapshot_hash": "Hash"},
})
HASH_FIELDS = {"Proof3": "proof_hash", "Plan3": "plan_hash", "Manifest3": "manifest_hash", "Revalidation3": "revalidation_hash", "Receipt3": "snapshot_hash"}


def tuple_preimage(scope, attributes):
    dimensions = {k: v for k, v in attributes.items() if v is not None and k != "body_code_namespace"}
    if "body_code" in dimensions:
        dimensions["body_code"] = {"namespace": attributes["body_code_namespace"], "token": attributes["body_code"]}
    return body_preimage(scope, dimensions)


def _semantic(kind, v):
    if kind in HASH_FIELDS:
        field = HASH_FIELDS[kind]
        require(v[field] == content_hash(v, field), kind + ": self hash mismatch.")
    if kind == "ScopeResolution":
        require(v["canonical_scope"] == {"manufacturer_key": "jeep", "model_key": "wrangler", "generation_key": "jl"}, "Unsupported canonical profile Scope.")
    elif kind == "Approval1":
        require(v["operator"] == v["operator"].strip() and "*" not in v["operator"], "Explicit operator required.")
    elif kind == "EvidenceState":
        refs = [p["reference"] for p in v["artifact_pins"]]
        require(len(refs) == len(set(refs)), "Conflicting artifact path hashes.")
    elif kind == "BodyTuple":
        require(any(v[k] is not None for k in ATTRIBUTES if k != "body_code_namespace"), "Body dimension required.")
        require((v["body_code"] is None) == (v["body_code_namespace"] is None), "Code namespace pair required.")
    elif kind == "BodyState":
        require(v["semantic_preimage"] == tuple_preimage(v["semantic_preimage"]["scope"], v["attributes"]), "Body tuple/preimage mismatch.")
        require(v["semantic_digest"] == semantic_digest(v["semantic_preimage"]), "Body digest mismatch.")
    elif kind == "TargetFields":
        require(len(v["trim_name"]) <= 100 and len(v["engine_name"]) <= 100, "Canonical descriptor exceeds column size.")
    elif kind == "ReviewedArtifact":
        if (v["reader"], v["reader_version"]) == ("generation-correspondence", "1.0"):
            _check("CorrespondenceReview", v["snapshot"])
        elif (v["reader"], v["reader_version"]) == ("body-import-receipt", VERSION):
            _check("Receipt3", v["snapshot"])
        else:
            raise ContractError("UNSUPPORTED_REVIEW_VERSION")
    elif kind == "CorrespondenceState":
        require(v["revision_uuid"] == v["review_payload"]["revision_uuid"] and v["content_hash"] == digest(v["review_payload"]), "Correspondence binding mismatch.")
    elif kind == "GenerationState":
        s, p = v["scope"], v["parent_state"]
        for name in ("manufacturer", "vehicle_model", "generation"):
            require(s[name] == {"pk": p[name + "_id"], "uuid": p[name + "_uuid"]}, "Parent chain mismatch.")
        require(p["generation_model_id"] == p["vehicle_model_id"], "Generation/model chain mismatch.")
        require((p["manufacturer_name"], p["vehicle_model_name"], p["generation_name"] if "generation_name" in p else "JL") == ("Jeep", "Wrangler", "JL"), "Unsupported parent profile.")
        require(all(p[x + "_active"] for x in ("manufacturer", "vehicle_model", "generation")), "Inactive parent.")
        require(p["start_year"] <= 2024 and (p["end_year"] is None or 2024 <= p["end_year"]), "Year outside Generation.")
        for r in v["correspondences"]:
            q = r["review_payload"]
            require(q["market"] == s["market"] and q["start_year"] <= s["model_year"] <= q["end_year"], "Correspondence applicability differs from candidate scope.")
            require(q["generation_uuid"] == s["generation"]["uuid"] and q["vehicle_model_uuid"] == s["vehicle_model"]["uuid"] and q["finding"] == "established" and r["successor_uuid"] is None, "Unestablished/superseded correspondence.")
    elif kind == "FamilyMember":
        require(v["baseline_digest"] == semantic_digest(v["baseline_preimage"]), "Baseline mismatch.")
        f, b = v["target_fields"], v["baseline_preimage"]
        require(f["factory_body_configuration_uuid"] is not None and b["series"] is None, "Family body/series unsupported.")
        require(all(f[k] == b[k] for k in ("model_year", "trim_name", "drivetrain", "market", "canonical_powertrain")), "Family projection mismatch.")
        require(semantic_digest(tuple_preimage(b["scope"], v["body_attributes"])) == b["body_digest"], "Family body mismatch.")
    elif kind == "FamilyState":
        require(len(v["release_members"]) == 31, "Exactly 31 release members required.")
        ids = [x["baseline_digest"] for x in v["release_members"]]
        require(len(set(ids)) == 31, "Duplicate release baseline.")
    elif kind == "VehicleState":
        require(v["body"] is None or v["body"]["generation_uuid"] == v["generation_uuid"], "Cross-Generation stored body.")
    elif kind == "PeerAssessment":
        require((v["receipt_uuid"] is None) == (v["receipt_snapshot_hash"] is None), "Receipt hash/UUID pairing mismatch.")
        if v["body_basis"] is not None and v["vehicle"]["body"] is not None:
            require(v["body_basis"] == v["vehicle"]["body"]["semantic_preimage"], "Peer body basis contradicts stored body.")
        if v["powertrain_basis"] is not None:
            require(all(value is None or value == v["powertrain_basis"][key] for key, value in v["vehicle"]["fields"]["canonical_powertrain"].items()), "Peer powertrain basis contradicts stored fields.")
        if v["relation"] == "equal":
            require(v["body_basis"] is not None and v["powertrain_basis"] is not None and v["receipt_uuid"] is not None, "Equality needs evidence.")
    elif kind in ("Proof3", "Plan3", "AuthorizationRow"):
        action = v.get("action", v.get("conclusion"))
        require((action == "no_op") == (v["existing_vehicle_uuid"] is not None), "Action/existing UUID mismatch.")
        if kind == "Proof3":
            require(v["baseline_digest"] == semantic_digest(v["baseline_preimage"]), "Proof baseline mismatch.")
            require(v["body_state_hash"] in {digest(x) for x in v["body_namespace"]}, "Selected body missing from namespace.")
            members = [m for m in v["family"]["release_members"] if m["candidate_hash"] == v["candidate_hash"]]
            require(len(members) == 1 and members[0]["baseline_preimage"] == v["baseline_preimage"], "Proof family subject mismatch.")
            selected_body = next(b for b in v["body_namespace"] if digest(b) == v["body_state_hash"])
            baseline = v["baseline_preimage"]
            for peer in v["peers"]:
                fields = peer["vehicle"]["fields"]
                relevant = all(fields[k] == baseline[k] for k in ("model_year", "market", "trim_name", "drivetrain"))
                require((peer["relation"] == "irrelevant") == (not relevant), "Peer relevance contradicts the semantic namespace.")
                if peer["relation"] == "equal":
                    require(peer["powertrain_basis"] == baseline["canonical_powertrain"] and semantic_digest(peer["body_basis"]) == baseline["body_digest"], "Equal peer has different body/powertrain semantics.")
                elif peer["relation"] == "distinct":
                    engine_distinct = peer["powertrain_basis"] is not None and peer["powertrain_basis"] != baseline["canonical_powertrain"]
                    body_distinct = peer["body_basis"] is not None and compare_bodies(peer["body_basis"], selected_body["semantic_preimage"]).relation == "distinct"
                    require(engine_distinct or body_distinct, "Distinct peer lacks an established discriminator.")
            equal = [p for p in v["peers"] if p["relation"] == "equal"]
            if v["conclusion"] == "create":
                require(not equal and not any(p["relation"] == "unresolved" for p in v["peers"]), "Unsafe create proof.")
            if v["conclusion"] == "no_op":
                require(not any(p["relation"] == "unresolved" for p in v["peers"]), "No-op has unresolved overlapping peers.")
                require(len(equal) == 1 and equal[0]["vehicle"]["is_active"] and equal[0]["vehicle"]["uuid"] == v["existing_vehicle_uuid"], "Unsafe no-op proof.")
        elif kind == "Plan3":
            p, c, f = v["proof"], v["candidate_snapshot"], v["target_fields"]
            require(v["candidate_hash"] == c["candidate_hash"] == p["candidate_hash"] and v["candidate_reference"] == c["candidate_reference"], "Candidate binding mismatch.")
            require(p["generation_state_hash"] == digest(v["generation"]) and p["body_state_hash"] == digest(v["body"]) and p["evidence_state_hash"] == digest(v["evidence"]), "Snapshot hash mismatch.")
            require(v["action"] == p["conclusion"] and v["existing_vehicle_uuid"] == p["existing_vehicle_uuid"], "Proof action mismatch.")
            require(v["body"]["generation_uuid"] == v["generation"]["scope"]["generation"]["uuid"], "Cross Generation body.")
            require(all(b["generation_uuid"] == v["body"]["generation_uuid"] for b in p["body_namespace"]), "Cross-Generation body namespace.")
            require(all(peer["vehicle"]["generation_uuid"] == v["body"]["generation_uuid"] and peer["vehicle"]["fields"]["model_year"] == 2024 and peer["vehicle"]["fields"]["market"] == "US" for peer in p["peers"]), "Cross-scope peer namespace.")
            member = next(m for m in p["family"]["release_members"] if m["candidate_hash"] == v["candidate_hash"])
            for revision in v["generation"]["correspondences"]:
                require(all(member["target_fields"].get(k) == value for k, value in revision["review_payload"]["restrictions"].items()), "Correspondence restriction differs from candidate projection.")
            require(c["canonical_scope"] == v["generation"]["scope"]["canonical_scope"] and c["candidate_identity"]["model_year"] == 2024 and c["candidate_identity"]["market"] == "US", "Candidate/Generation scope differs.")
            require(all(f[k] == p["baseline_preimage"][k] for k in ("model_year", "trim_name", "drivetrain", "market", "canonical_powertrain")), "Canonical target/baseline differs.")
            require(p["baseline_preimage"] == wire.baseline_preimage(scope=c["canonical_scope"], model_year=2024, trim_name=c["candidate_identity"]["trim_name"], drivetrain=c["drivetrain"], market="US", canonical_powertrain=c["canonical_powertrain"], body_digest=c["factory_body"]["identity"]["semantic_digest"]), "Candidate baseline mismatch.")
            require(c.get("factory_series") is None and c["factory_body"]["disposition"] == "pending", "Unsupported parent mode.")
            require(v["body"]["semantic_preimage"] == c["factory_body"]["identity"]["preimage"], "Resolved body mismatch.")
            require(v["action"] == "blocked" or not v["diagnostics"], "Executable plan has diagnostics.")
            if v["action"] == "create":
                require(f["factory_body_configuration_uuid"] == v["body"]["uuid"], "Create body mismatch.")
            elif v["action"] == "no_op":
                existing = next(peer["vehicle"] for peer in p["peers"] if peer["vehicle"]["uuid"] == v["existing_vehicle_uuid"])
                expected = existing["fields"] | {"factory_body_configuration_uuid": existing["body"]["uuid"] if existing["body"] else None}
                require(f == expected and v["target_slug"] == existing["slug"], "No-op target must preserve the exact existing row.")
            require(0 < len(v["target_slug"]) <= 180, "Slug length invalid.")
            require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", v["target_slug"])), "Invalid target slug.")
    elif kind == "Matrix3":
        require(len({r["plan_hash"] for r in v["rows"]}) == len(v["rows"]), "Repeated authorization plan.")
        require(all(len(r["target_slug"]) <= 180 and "*" not in r["target_slug"] for r in v["rows"]), "Invalid authorized slug.")
    elif kind == "Revalidation3":
        require(v["result"] != "valid" or not v["diagnostics"], "Valid revalidation has diagnostics.")
        require(v["result"] != "stale" or bool(v["diagnostics"]), "Stale revalidation needs diagnostics.")
    elif kind == "Manifest3":
        require(v["matrix_digest"] == digest(v["matrix"]) == v["approval"]["matrix_digest"] and v["approval_hash"] == digest(v["approval"]), "Exact approval binding mismatch.")
    elif kind == "Receipt3":
        plan, report, manifest = v["plan"], v["revalidation"], v["manifest"]
        require(report["result"] == "valid" and report["manifest_hash"] == manifest["manifest_hash"], "Receipt revalidation mismatch.")
        require(report["matrix_digest"] == manifest["matrix_digest"] and report["approval_hash"] == manifest["approval_hash"] and report["family_hash"] == manifest["matrix"]["family_hash"], "Receipt revalidation scope mismatch.")
        matrix_rows = manifest["matrix"]["rows"]
        require([r["candidate_reference"] for r in report["rows"]] == [r["candidate_reference"] for r in matrix_rows], "Receipt revalidation does not cover the complete Matrix.")
        bodies = {b["uuid"]: b for b in plan["proof"]["body_namespace"]}
        for row, checked in zip(matrix_rows, report["rows"]):
            require(checked["plan_hash"] == row["plan_hash"] and checked["baseline_digest"] == row["baseline_digest"] and row["body_uuid"] in bodies and checked["body_state_hash"] == digest(bodies[row["body_uuid"]]), "Receipt revalidation row differs from authorized state.")
        expected = {"candidate_reference": plan["candidate_reference"], "plan_hash": plan["plan_hash"], "proof_hash": plan["proof"]["proof_hash"], "baseline_digest": plan["proof"]["baseline_digest"], "body_state_hash": plan["proof"]["body_state_hash"]}
        require(expected in report["rows"], "Receipt plan missing from revalidation.")
        require(plan["generation"]["scope"] == manifest["matrix"]["scope"] and digest(plan["proof"]["family"]) == manifest["matrix"]["family_hash"], "Receipt family/scope mismatch.")
        row = authorization_row(plan)
        require(row in manifest["matrix"]["rows"], "Receipt plan not authorized.")
        require(v["persisted_fields"] == plan["target_fields"] and v["vehicle"]["slug"] == plan["target_slug"], "Receipt persisted projection mismatch.")
        require((v["outcome"] == "created" and plan["action"] == "create") or (v["outcome"] == "no_op" and plan["action"] == "no_op" and v["vehicle"]["uuid"] == plan["existing_vehicle_uuid"]), "Receipt outcome mismatch.")


def validate(kind, value):
    try:
        _json(value)
        _check(kind, value)
    except (ValidationError, ValueError, TypeError, KeyError, UnicodeError, AttributeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(str(exc)) from exc
    return value


def _pairs(items):
    result = {}
    for k, v in items:
        require(k not in result, "Duplicate JSON key: " + k)
        result[k] = v
    return result


def parse(kind, text):
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ContractError("Nonfinite JSON.")))
        validate(kind, value)
        return value
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ContractError(str(exc)) from exc


def serialize(kind, value):
    validate(kind, value)
    return canonical_json(value).encode("utf-8")


def authorization_row(plan):
    require(plan["action"] in ("create", "no_op"), "Blocked plan cannot be authorized.")
    return {"candidate_reference": plan["candidate_reference"], "candidate_hash": plan["candidate_hash"], "plan_hash": plan["plan_hash"], "action": plan["action"], "existing_vehicle_uuid": plan["existing_vehicle_uuid"], "target_slug": plan["target_slug"], "baseline_digest": plan["proof"]["baseline_digest"], "body_uuid": plan["body"]["uuid"]}
