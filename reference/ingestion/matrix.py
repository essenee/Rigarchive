"""Stage 6B Generation Trim Matrix v1: pure, immutable authorization scope.

This module validates and hashes *proposed* scope. It does not grant approval,
query the database, or execute imports. Approval and live-state checks are separate.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping
from uuid import UUID

MATRIX_VERSION = "1.0"
MATRIX_RESOLUTION_VERSION = "2.0"
MATRIX_POWERTRAIN_VERSION = "2.1"
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CREATE_BASES = frozenset({
    "first_representation", "mechanical_dimension",
    "source_established_grade", "adjudicated_distinct_grade",
})
_FIELDS = frozenset({"model_year", "trim_name", "engine_name", "drivetrain", "market"})
_PARENT_KEYS = ("manufacturer", "vehicle_model", "generation")
_ROW_KEYS = frozenset({
    "row_id", "model_year", "target_fields", "target_slug", "action",
    "permitted_create_bases", "candidate_reference", "candidate_digest",
    "evidence", "correspondence", "existing_record",
})
_MATRIX_KEYS = frozenset({"matrix_version", "parents", "market", "model_years", "rows"})


class MatrixValidationError(ValueError):
    """Malformed or ambiguous proposed matrix scope."""


def _fail(message: str) -> None:
    raise MatrixValidationError(message)


def _keys(value: Any, expected: frozenset[str] | set[str], path: str) -> None:
    if not isinstance(value, dict) or set(value) != set(expected):
        _fail(f"{path}: expected exactly {sorted(expected)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "*" in value:
        _fail(f"{path}: expected a nonempty, trimmed, explicit string")
    return value


def _slug(value: Any, path: str) -> str:
    value = _string(value, path)
    if not _SLUG.fullmatch(value):
        _fail(f"{path}: invalid slug")
    return value


def _digest(value: Any, path: str) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        _fail(f"{path}: expected sha256 lowercase digest")


def _identity(value: Any, path: str) -> None:
    _keys(value, {"pk", "uuid", "slug"}, path)
    if type(value["pk"]) is not int or value["pk"] <= 0:
        _fail(f"{path}.pk: expected positive integer")
    try:
        canonical_uuid = str(UUID(value["uuid"]))
    except (ValueError, TypeError, AttributeError):
        _fail(f"{path}.uuid: invalid UUID")
    if value["uuid"] != canonical_uuid:
        _fail(f"{path}.uuid: expected canonical lowercase UUID")
    _slug(value["slug"], f"{path}.slug")


def _references(value: Any, path: str) -> None:
    """References are unordered by ID; evidence within each reference remains ordered."""
    if not isinstance(value, list):
        _fail(f"{path}: expected list")
    seen = set()
    for i, ref in enumerate(value):
        name = f"{path}[{i}]"
        _keys(ref, {"reference", "digest"}, name)
        key = _string(ref["reference"], f"{name}.reference")
        _digest(ref["digest"], f"{name}.digest")
        if key in seen:
            _fail(f"{path}: duplicate reference {key}")
        seen.add(key)


def validate_matrix(matrix: Mapping[str, Any]) -> None:
    """Validate exact v1 schema; reject execution/approval fields in scope."""
    _keys(matrix, _MATRIX_KEYS, "matrix")
    version = matrix["matrix_version"]
    if version not in (MATRIX_VERSION, MATRIX_RESOLUTION_VERSION, MATRIX_POWERTRAIN_VERSION):
        _fail("Unsupported matrix version")
    _keys(matrix["parents"], set(_PARENT_KEYS), "parents")
    for key in _PARENT_KEYS:
        _identity(matrix["parents"][key], f"parents.{key}")
    market = _string(matrix["market"], "market")
    years = matrix["model_years"]
    if not isinstance(years, list) or not years or any(type(y) is not int or not 1886 <= y <= 2200 for y in years):
        _fail("model_years: expected explicit model-year integers")
    if years != sorted(set(years)):
        _fail("model_years: expected sorted unique years")
    rows = matrix["rows"]
    if not isinstance(rows, list) or not rows:
        _fail("rows: expected nonempty list")
    ids, slugs, identities = set(), set(), set()
    for i, row in enumerate(rows):
        path = f"rows[{i}]"
        _keys(row, _ROW_KEYS | ({"generation_binding"} if version != MATRIX_VERSION else set()), path)
        row_id = _string(row["row_id"], f"{path}.row_id")
        if row_id in ids:
            _fail(f"Duplicate row_id: {row_id}")
        ids.add(row_id)
        year = row["model_year"]
        if type(year) is not int or year not in years:
            _fail(f"{path}.model_year: outside matrix scope")
        from reference.powertrain import FIELDS, validate_powertrain
        target_keys = _FIELDS | set(FIELDS) if version == MATRIX_POWERTRAIN_VERSION else _FIELDS
        _keys(row["target_fields"], target_keys, f"{path}.target_fields")
        if version == MATRIX_POWERTRAIN_VERSION:
            from django.core.exceptions import ValidationError
            try:
                validate_powertrain({k: row["target_fields"][k] for k in FIELDS}, complete=True)
            except ValidationError as exc:
                _fail(str(exc))
        fields = row["target_fields"]
        if fields["model_year"] != year or type(fields["model_year"]) is not int or fields["market"] != market:
            _fail(f"{path}: target year/market mismatch")
        for field in _FIELDS - {"model_year"}:
            _string(fields[field], f"{path}.target_fields.{field}")
        slug = _slug(row["target_slug"], f"{path}.target_slug")
        if slug in slugs:
            _fail(f"Duplicate target slug: {slug}")
        slugs.add(slug)
        identity_keys = (target_keys - {"engine_name"}) if version == MATRIX_POWERTRAIN_VERSION else _FIELDS
        identity = tuple(fields[k] for k in sorted(identity_keys))
        if identity in identities:
            _fail(f"Duplicate canonical identity in {path}")
        identities.add(identity)
        if row["action"] not in ("create", "reviewed_existing"):
            _fail(f"{path}.action: unsupported action")
        bases = row["permitted_create_bases"]
        if not isinstance(bases, list) or len(bases) != len(set(bases)) or any(b not in _CREATE_BASES for b in bases):
            _fail(f"{path}: invalid create bases")
        if row["action"] == "create" and not bases:
            _fail(f"{path}: create requires permitted bases")
        if row["action"] == "reviewed_existing" and (bases or row["existing_record"] is None):
            _fail(f"{path}: reviewed existing requires pinned record and no create bases")
        if row["action"] == "create" and row["existing_record"] is not None:
            _fail(f"{path}: create cannot pin existing record")
        if row["existing_record"] is not None:
            _identity(row["existing_record"], f"{path}.existing_record")
            if row["existing_record"]["slug"] != slug:
                _fail(f"{path}: existing slug differs from target")
        _string(row["candidate_reference"], f"{path}.candidate_reference")
        _digest(row["candidate_digest"], f"{path}.candidate_digest")
        _references(row["evidence"], f"{path}.evidence")
        _references(row["correspondence"], f"{path}.correspondence")
        if not row["evidence"]:
            _fail(f"{path}: evidence must be explicitly pinned")
        if version == MATRIX_VERSION:
            if not row["correspondence"]:
                _fail(f"{path}: evidence and correspondence must be explicitly pinned")
        else:
            binding = row["generation_binding"]
            _keys(binding, {"mode", "strategy", "resolution_version"}, f"{path}.generation_binding")
            expected = ("explicit_correspondence", "reviewed_source_correspondence") if row["correspondence"] else (
                "unique_deterministic", "unique_year_range",
            )
            if (binding["mode"], binding["strategy"]) != expected or binding["resolution_version"] != ("1.1" if version == MATRIX_POWERTRAIN_VERSION else "1.0"):
                _fail(f"{path}: incompatible Generation binding mode, strategy or correspondence pins")


def canonical_matrix_payload(matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalized, detached scope; never include mutable progress metadata."""
    validate_matrix(matrix)
    result = deepcopy(matrix)
    result["rows"].sort(key=lambda r: (r["model_year"], r["row_id"]))
    for row in result["rows"]:
        row["permitted_create_bases"].sort()
        row["evidence"].sort(key=lambda r: r["reference"])
        row["correspondence"].sort(key=lambda r: r["reference"])
    return result


def compute_matrix_digest(matrix: Mapping[str, Any]) -> str:
    """Content hash; not an approval or authorization to import."""
    payload = canonical_matrix_payload(matrix)
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MatrixValidationError(f"Matrix is not canonical JSON: {exc}") from exc
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
