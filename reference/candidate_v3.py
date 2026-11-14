"""RA-046 Candidate 3.0.0 pure wire contract. No ORM, files, or import authority."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from uuid import UUID

from django.core.exceptions import ValidationError

from reference.body_identity import (
    BASELINE_CONTRACT, BODY_CONTRACT, DIMENSIONS, HASH, TOKEN, baseline_preimage,
    canonical_json, semantic_digest,
)
from reference.powertrain import FIELDS, decimal_string, validate_powertrain

ARTIFACT_TYPE = "rigarchive.candidate_configuration.v3"
SCHEMA_VERSION = "3.0.0"
SCHEMA_ID = "urn:rigarchive:contract:candidate_configuration:3.0.0"
NORMALIZERS = frozenset({"source_literal", "decimal_liters", "powertrain_terminology",
    "wrangler_selector_heading", "wrangler_door_taxonomy", "reviewed_alias",
    "reviewed_classification", "existing_body_equivalence"})
TARGETS = frozenset({"make", "model", "model_year", "market", "trim_name",
    "generic_drive_classification", "body_identity_equivalence",
    "factory_series.namespace", "factory_series.designation", "factory_series.identity_role",
    *("canonical_scope." + k for k in ("manufacturer_key", "model_key", "generation_key")),
    *("factory_body." + k for k in DIMENSIONS), *FIELDS})


@dataclass(frozen=True)
class Diagnostic:
    stage: str
    code: str
    path: str
    message: str


class CandidateV3Error(ValidationError):
    def __init__(self, code, path, message):
        self.diagnostic = Diagnostic("contract", code, path, message)
        super().__init__(f"contract/{code} {path}: {message}")


def fail(code, path, message):
    raise CandidateV3Error(code, path, message)


def path_at(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def text(v, p):
    if type(v) is not str or not v.strip():
        fail("INVALID_TYPE", p, "Expected nonempty text.")
    try:
        v.encode("utf-8")
    except UnicodeError:
        fail("INVALID_TYPE", p, "Lone surrogate is forbidden.")


def local_id(v, p):
    text(v, p)
    if "|" in v:
        fail("INVALID_TYPE", p, "Reserved qualifier separator in local identifier.")


def token(v, p):
    if type(v) is not str or len(v) > 128 or not TOKEN.fullmatch(v):
        fail("INVALID_TOKEN", p, "Expected reviewed canonical Token.")


def hash_value(v, p):
    if type(v) is not str or not HASH.fullmatch(v):
        fail("INVALID_HASH", p, "Expected sha256: and 64 lowercase hex digits.")


def uuid_value(v, p):
    try:
        valid = type(v) is str and str(UUID(v)) == v and UUID(v).int != 0
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        fail("INVALID_TYPE", p, "Expected canonical non-nil UUID.")


def year(v, p):
    if type(v) is not int or not 1 <= v <= 32767:
        fail("INVALID_TYPE", p, "Expected Year integer.")


def positive(v, p):
    if type(v) is not int or v < 1:
        fail("INVALID_TYPE", p, "Expected positive integer.")


def integer(v, p):
    if type(v) is not int:
        fail("INVALID_TYPE", p, "Expected integer.")


def boolean(v, p):
    if type(v) is not bool:
        fail("INVALID_TYPE", p, "Expected boolean.")


def enum(*choices):
    def check(v, p):
        if type(v) is not str or v not in choices:
            fail("INVALID_TYPE", p, "Unsupported enumeration value.")
    return check


def nullable(check):
    return lambda v, p: None if v is None else check(v, p)


def obj(v, p, required, optional=None):
    if type(v) is not dict:
        fail("INVALID_TYPE", p, "Expected object.")
    optional = optional or {}
    for key in v:
        if key not in required and key not in optional:
            fail("UNKNOWN_FIELD", path_at(p, key), "Unknown contract member.")
    for key in required:
        if key not in v:
            fail("MISSING_FIELD", path_at(p, key), "Required contract member.")
    for key, item in v.items():
        (required | optional)[key](item, path_at(p, key))


def array(check, *, nonempty=False, key=None):
    def validate(v, p):
        if type(v) is not list or (nonempty and not v):
            fail("INVALID_TYPE", p, "Expected array" + (" with members." if nonempty else "."))
        for i, item in enumerate(v):
            check(item, path_at(p, i))
        if key is not None:
            keys = [key(item) for item in v]
            if len(set(keys)) != len(keys):
                fail("DUPLICATE_ID", p, "Duplicate member identity/reference.")
            if keys != sorted(keys):
                fail("NONCANONICAL_ORDER", p, "Set-like array is not canonically ordered.")
    return validate


def raw_json(v, p):
    if v is None or type(v) in (bool, int):
        return
    if type(v) is float:
        if not math.isfinite(v):
            fail("INVALID_TYPE", p, "Nonfinite JSON number.")
    elif type(v) is str:
        try:
            v.encode("utf-8")
        except UnicodeError:
            fail("INVALID_TYPE", p, "Lone surrogate is forbidden.")
    elif type(v) is list:
        for i, item in enumerate(v):
            raw_json(item, path_at(p, i))
    elif type(v) is dict:
        for k, item in v.items():
            if type(k) is not str:
                fail("INVALID_TYPE", p, "JSON keys must be strings.")
            raw_json(k, p)
            raw_json(item, path_at(p, k))
    else:
        fail("INVALID_TYPE", p, "Not a JSON value.")


def json_object(v, p):
    if type(v) is not dict:
        fail("INVALID_TYPE", p, "Expected inert JSON object.")
    raw_json(v, p)


def timestamp(v, p):
    if type(v) is not str or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z", v):
        fail("INVALID_TYPE", p, "Expected UTC RFC3339 timestamp.")
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        fail("INVALID_TYPE", p, "Invalid calendar timestamp.")


def retained_path(v, p):
    text(v, p)
    if "\\" in v or "\0" in v or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", v) or any(x in ("", ".", "..") for x in v.split("/")):
        fail("INVALID_TYPE", p, "Expected repository-relative retained POSIX path.")


def qref(v, p):
    text(v, p)
    parts = v.split("|")
    if len(parts) != 4:
        fail("INVALID_TYPE", p, "Expected four-part qualified assertion reference.")
    local_id(parts[0], p); hash_value(parts[1], p)
    local_id(parts[2], p); local_id(parts[3], p)


MARKET = enum("US", "CA", "OT")
DRIVE = enum("2WD", "4WD", "AWD", "UNK")
SCOPE_FIELDS = {"manufacturer_key": token, "model_key": token, "generation_key": token}

def scope(v, p): obj(v, p, SCOPE_FIELDS)
def model_scope(v, p): obj(v, p, {k: token for k in ("manufacturer_key", "model_key")})
def refs(v, p): array(qref, key=lambda x: x)(v, p)
def ids(v, p): array(local_id, key=lambda x: x)(v, p)
def qualified_refs(v, p): array(qref, nonempty=True, key=lambda x: x)(v, p)
def interpretation_refs(v, p): array(text, key=lambda x: x)(v, p)


def powertrain(v, p):
    try:
        validate_powertrain(v)
    except ValidationError as exc:
        code = "INVALID_DECIMAL" if type(v) is dict and "displacement" in str(exc).lower() else "INVALID_TYPE"
        fail(code, p, str(exc))


def dimensions(v, p):
    if type(v) is not dict or not v:
        fail("INVALID_PREIMAGE", p, "Body basis must be nonempty.")
    checks = {k: token for k in DIMENSIONS}
    checks["body_code"] = lambda x, q: obj(x, q, {"namespace": token, "token": token})
    obj(v, p, {}, checks)


def identity(v, p, kind):
    def preimage(pre, q):
        if kind == "body":
            obj(pre, q, {"identity_contract": enum(BODY_CONTRACT), "profile_family": enum("factory-body"),
                         "scope": scope, "dimensions": dimensions})
            expected = semantic_digest(pre)
        else:
            obj(pre, q, {"identity_contract": enum("factory-series-semantic/1"), "scope": model_scope,
                         "namespace": token, "designation": token})
            expected = _digest(pre)
        if v["semantic_digest"] != expected:
            fail("SEMANTIC_DIGEST_MISMATCH", p, "Frozen preimage digest differs.")
    # Validate digest syntax before the dependent preimage check, independent of key order.
    obj(v, p, {"semantic_digest": hash_value, "preimage": lambda x, q: None})
    preimage(v["preimage"], path_at(p, "preimage"))


def parent(v, p, kind):
    if type(v) is not dict or v.get("disposition") not in ("existing", "pending"):
        fail("INVALID_TYPE", p, "Expected existing/pending parent union.")
    fields = {"disposition": enum("existing", "pending"),
              "identity": lambda x, q: identity(x, q, kind), "support": parent_support}
    if v["disposition"] == "existing":
        fields |= {"parent_uuid": uuid_value, "binding_revision": binding}
    obj(v, p, fields)
    if (kind == "series" or v["disposition"] == "pending") and v["support"]["equivalence_interpretation_ref"] is not None:
        fail("INVALID_TYPE", p + "/support/equivalence_interpretation_ref", "Equivalence not permitted in this union branch.")


def parent_support(v, p):
    obj(v, p, {"applicability_ref": local_id, "configuration_refs": qualified_refs,
               "interpretation_refs": interpretation_refs, "equivalence_interpretation_ref": nullable(text)})


def binding(v, p):
    obj(v, p, {"revision_uuid": uuid_value, "content_hash": hash_value, "applicability_ref": local_id})


def applicability(v, p):
    obj(v, p, {"applicability_id": local_id, "scope": nullable(scope), "market": nullable(MARKET),
               "start_year": nullable(year), "end_year": nullable(year), "configuration_refs": qualified_refs,
               "source_assertion_refs": qualified_refs, "finding_refs": ids})
    a, b = v["start_year"], v["end_year"]
    if (a is None) != (b is None) or (a is not None and a > b):
        fail("INVALID_TYPE", p, "Coverage requires a valid paired range or two nulls.")


def assertion(v, p):
    obj(v, p, {"assertion_id": local_id, "attribute_key": text, "raw_value": raw_json,
               "source_context": text}, {"extracted_at": nullable(timestamp)})


def document(v, p):
    obj(v, p, {"source_id": local_id, "raw_artifact_hash": hash_value, "raw_artifact_reference": retained_path,
               "extractor_id": text, "extractor_version": text, "extraction_mode": text,
               "assertion_set_id": local_id, "assertions": array(assertion, nonempty=True, key=lambda x: x["assertion_id"])},
        {"source_locator": nullable(text), "retrieved_at": nullable(timestamp),
         "source_applicability": nullable(lambda x, q: obj(x, q, {}, {
             "market": nullable(MARKET), "applicability_basis": nullable(text), "publisher_jurisdiction": nullable(text),
             "applicability_scope": nullable(enum("configuration", "model_year"))})),
         "publication_revision": nullable(text), "generation_normalizer": lambda x, q: obj(x, q, {"id": text, "version": text})})


def generation(v, p):
    obj(v, p, {"source_id": local_id, "source_namespace": enum("generation_designation", "generation_code", "source_model_code", "generation_section"),
        "identity_type": enum("model_code", "generation_designation"), "native_identifier": text, "document_hash": hash_value,
        "assertion_set_id": local_id, "assertion_id": local_id, "normalizer_id": enum("explicit_generation_identity"),
        "normalizer_version": enum("1.0.0")})


def interpretation(v, p):
    obj(v, p, {"interpretation_id": text, "source_assertion_ref": qref, "target_attribute_key": enum(*TARGETS),
        "normalized_concept": raw_json, "mapping_status": enum("mapped", "unresolved", "conflicting"),
        "applicability_ref": local_id, "normalization": lambda x, q: obj(x, q, {"id": enum(*NORMALIZERS), "version": enum("1.0.0")}),
        "finding_refs": ids}, {"raw_source_value": raw_json, "manufacturer_term": nullable(text), "normalization_notes": nullable(text)})
    target, value = v["target_attribute_key"], v["normalized_concept"]
    if value is None:
        return
    check = token
    if target in ("make", "model", "trim_name"): check = text
    elif target == "model_year": check = year
    elif target == "market": check = MARKET
    elif target == "generic_drive_classification": check = DRIVE
    elif target == "body_identity_equivalence": check = hash_value
    elif target == "factory_body.body_code": check = lambda x, q: obj(x, q, {"namespace": token, "token": token})
    elif target == "factory_series.identity_role": check = enum("independent_series")
    elif target in FIELDS:
        projected = dict.fromkeys(FIELDS); projected[target] = value
        check = lambda x, q: powertrain(projected, q)
    check(value, path_at(p, "normalized_concept"))


def locator(v, p):
    if type(v) is not dict:
        fail("INVALID_TYPE", p, "Expected finding locator.")
    if v.get("kind") == "json_pointer":
        def pointer(x, q):
            if type(x) is not str or (x and not x.startswith("/")) or re.search(r"~(?![01])", x):
                fail("INVALID_TYPE", q, "Invalid RFC6901 pointer.")
        obj(v, p, {"kind": enum("json_pointer"), "pointer": pointer})
    elif v.get("kind") == "utf8_lines":
        obj(v, p, {"kind": enum("utf8_lines"), "start_line": positive, "end_line": positive})
        if v["start_line"] > v["end_line"]: fail("INVALID_TYPE", p, "Invalid inclusive line range.")
    else:
        fail("INVALID_TYPE", p, "Unsupported locator union.")


def finding(v, p):
    obj(v, p, {"finding_id": local_id, "artifact_type": enum("workflow_review", "canonical_import_adjudication", "generation_correspondence_review"),
        "artifact_version": text, "artifact_reference": retained_path, "artifact_hash": hash_value,
        "locator": locator, "applicability_ref": local_id})


def text_map(check):
    def validate(v, p):
        if type(v) is not dict: fail("INVALID_TYPE", p, "Expected attribute map.")
        for k, item in v.items():
            text(k, p); check(item, path_at(p, k))
    return validate


# Retained RA-011 nonidentity types, with RA-046's explicitly closed field sets.
def technical_value(v, p):
    def number_or_string(x, q):
        if type(x) not in (int, float, str): fail("INVALID_TYPE", q, "Expected number or string.")
        raw_json(x, q)
    obj(v, p, {}, {"normalized_value": nullable(number_or_string), "normalized_unit": nullable(text),
        "raw_source_string": nullable(text), "rpm_normalized": nullable(integer), "extra_context": json_object})


def engine(v, p):
    obj(v, p, {}, {"code": nullable(text), "cylinders": nullable(positive), "displacement": nullable(technical_value), "horsepower": nullable(technical_value)})


def transmission(v, p):
    obj(v, p, {}, {"code": nullable(text), "type": nullable(text), "speeds": nullable(positive)})


def component(v, p):
    def number(x, q):
        if type(x) not in (int, float): fail("INVALID_TYPE", q, "Expected finite JSON number.")
        raw_json(x, q)
    obj(v, p, {"component_type": text, "name": text}, {"low_range_ratio": nullable(number), "has_locking_feature": nullable(boolean), "extra_properties": json_object})


def mode(v, p):
    obj(v, p, {"mode_code": text, "name": text}, {"center_coupling": nullable(text), "center_differential_state": nullable(text), "low_range": nullable(boolean), "torque_split_default": nullable(text)})


def rich_drive(v, p):
    obj(v, p, {}, {"generic_classification": nullable(DRIVE), "architecture": nullable(text), "components": array(component),
        "operating_modes": array(mode), "capabilities": array(text), "manufacturer_terminology": nullable(text)})


def technical(v, p):
    obj(v, p, {}, {"engine": nullable(engine), "transmission": nullable(transmission), "drivetrain_details": nullable(rich_drive)})


def feature(v, p):
    obj(v, p, {"feature_name": text}, {"source_classification": nullable(text), "normalized_classification_status": nullable(text),
        "source_assertion_ref": nullable(qref), "category_status": nullable(text), "notes": nullable(text)})


def package(v, p):
    obj(v, p, {"name": text}, {"source_classification": nullable(text), "normalized_classification_status": nullable(text),
        "is_distinct_trim_identity": boolean, "availability": nullable(text)})


REVIEW = enum("not_required", "pending_review", "under_review", "resolved", "rejected_excluded")

def review(v, p):
    def state(x, q):
        obj(x, q, {"reconciliation_state": enum("single_source", "corroborated", "conflicting", "ambiguous", "incomplete"),
            "review_disposition": REVIEW}, {"conflict_details": nullable(text)})
    obj(v, p, {}, {"requires_human_review": boolean, "review_workflow_disposition": REVIEW,
        "attribute_states": text_map(state), "reconciliation_notes": nullable(text)})


def _digest(value):
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def candidate_hash(value):
    """Mathematical artifact hash, not schema/evidence validity or approval."""
    if isinstance(value, CandidateV3Document): value = value.to_dict()
    if type(value) is not dict: fail("INVALID_TYPE", "", "Expected candidate object.")
    raw_json(value, "")
    return _digest({k: v for k, v in value.items() if k != "candidate_hash"})


def validate_structure(value):
    """Fail on structural/cryptographic defects only; no evidence acceptance."""
    if isinstance(value, CandidateV3Document): value = value.to_dict()
    raw_json(value, "")
    if type(value) is not dict: fail("INVALID_TYPE", "", "Expected candidate object.")
    envelope = value.get("envelope")
    if type(envelope) is dict and any(k in envelope and envelope[k] != expected for k, expected in (
            ("artifact_type", ARTIFACT_TYPE), ("schema_version", SCHEMA_VERSION), ("$schema", SCHEMA_ID))):
        fail("UNSUPPORTED_VERSION", "/envelope", "Exact v3 dispatch triple required.")
    def env(x, q): obj(x, q, {"artifact_type": enum(ARTIFACT_TYPE), "schema_version": enum(SCHEMA_VERSION), "$schema": enum(SCHEMA_ID)}, {"created_at": timestamp, "generator": text})
    def ident(x, q):
        obj(x, q, {"manufacturer_name": text, "vehicle_model_name": text, "model_year": nullable(year), "market": nullable(MARKET), "trim_name": nullable(text)}, {"generation_name": nullable(text)})
        if x["trim_name"] is not None and len(x["trim_name"]) > 100: fail("INVALID_TYPE", path_at(q, "trim_name"), "Canonical trim exceeds 100 characters.")
    def source_ident(x, q): obj(x, q, {"source_id": local_id, "identity_type": text, "native_identifier": text}, {"source_description": nullable(text)})
    obj(value, "", {"envelope": env, "candidate_reference": text, "candidate_identity": ident, "canonical_scope": nullable(scope),
        "canonical_identity_contract": enum(BASELINE_CONTRACT), "drivetrain": nullable(DRIVE), "configuration_refs": qualified_refs,
        "applicability": array(applicability, nonempty=True, key=lambda x: x["applicability_id"]),
        "evidence_documents": array(document, nonempty=True, key=lambda x: (x["source_id"], x["raw_artifact_hash"], x["assertion_set_id"])),
        "evidence_raw_hashes": array(hash_value, nonempty=True, key=lambda x: x),
        "generation_evidence": array(generation, key=lambda x: (x["source_id"], x["document_hash"], x["assertion_set_id"], x["assertion_id"])),
        "normalized_assertions": array(interpretation, key=lambda x: x["interpretation_id"]), "candidate_hash": hash_value},
        {"source_configuration_identities": array(source_ident, key=lambda x: (x["source_id"], x["identity_type"], x["native_identifier"])),
        "canonical_powertrain": nullable(powertrain), "factory_body": nullable(lambda x, q: parent(x, q, "body")),
        "factory_series": nullable(lambda x, q: parent(x, q, "series")),
        "reviewed_findings": array(finding, key=lambda x: x["finding_id"]), "attribute_provenance": text_map(qualified_refs),
        "normalized_technical_details": nullable(technical), "factory_technical_features": array(feature), "packages_and_options": array(package),
        "reconciliation_and_review": nullable(review), "revision_lineage": lambda x, q: obj(x, q, {"base_artifact_reference": retained_path,
            "base_artifact_hash": hash_value, "base_schema_version": text, "change_reason": text})})
    _local_references(value)
    if candidate_hash(value) != value["candidate_hash"]:
        fail("ARTIFACT_HASH_MISMATCH", "/candidate_hash", "Whole-candidate hash differs.")


def evidence_index(value):
    return {"|".join((d["source_id"], d["raw_artifact_hash"], d["assertion_set_id"], a["assertion_id"])): (d, a)
            for d in value["evidence_documents"] for a in d["assertions"]}


def _local_references(c):
    assertions = evidence_index(c)
    apps = {a["applicability_id"] for a in c["applicability"]}
    findings = {f["finding_id"] for f in c.get("reviewed_findings", [])}
    interpretations = {i["interpretation_id"] for i in c["normalized_assertions"]}
    def require(ref, known, path):
        if ref not in known: fail("BROKEN_REFERENCE", path, f"Unresolved local reference: {ref}")
    def many(refs, known, path):
        for n, ref in enumerate(refs): require(ref, known, path_at(path, n))
    many(c["configuration_refs"], assertions, "/configuration_refs")
    for n, a in enumerate(c["applicability"]):
        p = f"/applicability/{n}"
        many(a["configuration_refs"], assertions, p + "/configuration_refs")
        many(a["source_assertion_refs"], assertions, p + "/source_assertion_refs")
        many(a["finding_refs"], findings, p + "/finding_refs")
    for n, i in enumerate(c["normalized_assertions"]):
        p = f"/normalized_assertions/{n}"
        require(i["source_assertion_ref"], assertions, p + "/source_assertion_ref")
        require(i["applicability_ref"], apps, p + "/applicability_ref")
        many(i["finding_refs"], findings, p + "/finding_refs")
    for n, f in enumerate(c.get("reviewed_findings", [])): require(f["applicability_ref"], apps, f"/reviewed_findings/{n}/applicability_ref")
    for kind in ("factory_body", "factory_series"):
        par = c.get(kind)
        if par is None: continue
        require(par["support"]["applicability_ref"], apps, f"/{kind}/support/applicability_ref")
        many(par["support"]["configuration_refs"], assertions, f"/{kind}/support/configuration_refs")
        many(par["support"]["interpretation_refs"], interpretations, f"/{kind}/support/interpretation_refs")
        if par["support"]["equivalence_interpretation_ref"] is not None:
            require(par["support"]["equivalence_interpretation_ref"], interpretations, f"/{kind}/support/equivalence_interpretation_ref")
        if par["disposition"] == "existing": require(par["binding_revision"]["applicability_ref"], apps, f"/{kind}/binding_revision/applicability_ref")
    for n, g in enumerate(c["generation_evidence"]):
        require("|".join((g["source_id"], g["document_hash"], g["assertion_set_id"], g["assertion_id"])), assertions, f"/generation_evidence/{n}")
    for key, refs_ in c.get("attribute_provenance", {}).items(): many(refs_, assertions, path_at("/attribute_provenance", key))
    for n, f in enumerate(c.get("factory_technical_features", [])):
        if f.get("source_assertion_ref") is not None: require(f["source_assertion_ref"], assertions, f"/factory_technical_features/{n}/source_assertion_ref")
    source_ids = {d["source_id"] for d in c["evidence_documents"]}
    for n, i in enumerate(c.get("source_configuration_identities", [])): require(i["source_id"], source_ids, f"/source_configuration_identities/{n}/source_id")
    if c["evidence_raw_hashes"] != sorted({d["raw_artifact_hash"] for d in c["evidence_documents"]}):
        fail("BROKEN_REFERENCE", "/evidence_raw_hashes", "Hash inventory differs from retained documents.")


@dataclass(frozen=True, init=False)
class CandidateV3Document:
    _value: dict

    def __init__(self, value):
        validate_structure(value)
        object.__setattr__(self, "_value", deepcopy(value))

    def to_dict(self):
        return deepcopy(self._value)


def parse_candidate(data):
    """Duplicate-aware parsing; no repair, bytes access, evidence acceptance or resolution."""
    if isinstance(data, CandidateV3Document): return CandidateV3Document(data.to_dict())
    if type(data) is str:
        class Pairs(list): pass
        try:
            parsed = json.loads(data, object_pairs_hook=Pairs)
        except (ValueError, RecursionError) as exc:
            fail("INVALID_TYPE", "", f"Invalid JSON: {exc}")
        def unpack(v, p):
            if isinstance(v, Pairs):
                d = {}
                for key, val in v:
                    if key in d: fail("DUPLICATE_KEY", path_at(p, key), "Duplicate JSON key.")
                    d[key] = unpack(val, path_at(p, key))
                return d
            if type(v) is list: return [unpack(x, path_at(p, i)) for i, x in enumerate(v)]
            return v
        try:
            data = unpack(parsed, "")
        except RecursionError:
            fail("INVALID_TYPE", "", "JSON nesting exceeds the parser's supported depth.")
    return CandidateV3Document(data)


def serialize_candidate(value):
    if not isinstance(value, CandidateV3Document): value = parse_candidate(value)
    raw = value.to_dict()
    validate_structure(raw)
    return canonical_json(raw)


def pending_parent_checksum(value, *, kind="body", expected=None):
    """Derived checksum only; no checksum member is admitted to the wire union."""
    if kind not in ("body", "series"): fail("INVALID_TYPE", "", "Unknown parent kind.")
    raw_json(value, "")
    parent(value, "", kind)
    if value["disposition"] != "pending": fail("INVALID_TYPE", "", "Expected pending descriptor.")
    result = _digest(value)
    if expected is not None:
        hash_value(expected, "")
        if expected != result: fail("INVALID_HASH", "", "Pending descriptor checksum differs.")
    return result


def baseline_identity_digest(value):
    """Reconstruct proposed meaning only; incomplete draft returns None, never eligibility."""
    if isinstance(value, CandidateV3Document): value = value.to_dict()
    validate_structure(value)
    ci, pt = value["candidate_identity"], value.get("canonical_powertrain")
    if value["canonical_scope"] is None or pt is None or any(v is None for v in pt.values()) or any(ci[k] is None for k in ("model_year", "trim_name", "market")) or value["drivetrain"] in (None, "UNK"):
        return None
    def parent_digest(kind):
        return value[kind]["identity"]["semantic_digest"] if value.get(kind) is not None else None
    try:
        pre = baseline_preimage(scope=value["canonical_scope"], model_year=ci["model_year"], trim_name=ci["trim_name"],
            drivetrain=value["drivetrain"], market=ci["market"], canonical_powertrain=pt,
            body_digest=parent_digest("factory_body"), series_digest=parent_digest("factory_series"))
        return semantic_digest(pre)
    except ValidationError:
        return None  # Existing complete-powertrain eligibility guards, e.g. other aspiration.
