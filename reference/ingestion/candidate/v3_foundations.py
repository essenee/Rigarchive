"""Non-executable Candidate 3.0.0 identity-field contract foundations.

This is NOT the complete Candidate v3 wire schema or an importable candidate.
RA-045 leaves parent binding/pending-parent shapes and full envelope details for
contract review. Non-null parent payloads fail explicitly until those are approved.
Existing serializers, Candidate 2.1 and adjudication dispatch are untouched.
"""
import hashlib
import json

from django.core.exceptions import ValidationError

from reference.body_identity import BASELINE_CONTRACT, canonical_json
from reference.powertrain import validate_powertrain

SCHEMA_VERSION = "3.0.0"
IDENTITY_FIELDS = frozenset({
    "factory_body", "factory_series", "canonical_powertrain", "canonical_identity_contract",
})


class UnresolvedV3Contract(ValidationError):
    """An approved direction still needs an exact wire contract before use."""


def validate_identity_fields(schema_version, fields):
    """Closed optional-field projection, not candidate eligibility or evidence proof."""
    if schema_version != SCHEMA_VERSION:
        raise ValidationError("Identity-field foundations require explicit Candidate schema 3.0.0 dispatch.")
    if type(fields) is not dict or not set(fields) <= IDENTITY_FIELDS:
        raise ValidationError("Unsupported Candidate v3 identity field.")
    if fields.get("canonical_identity_contract") not in (None, BASELINE_CONTRACT):
        raise ValidationError("Unsupported successor baseline contract.")
    if fields.get("canonical_powertrain") is not None:
        validate_powertrain(fields["canonical_powertrain"])
    for key in ("factory_body", "factory_series"):
        if fields.get(key) is not None:
            raise UnresolvedV3Contract(
                f"{key}: exact existing/pending-parent binding and qualified evidence wire shape needs approval."
            )


def serialize_identity_fields(schema_version, fields):
    """Canonical projection JSON only; never a full candidate artifact serialization."""
    validate_identity_fields(schema_version, fields)
    return canonical_json(fields)


def deserialize_identity_fields(schema_version, text):
    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    def closed_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError("Duplicate JSON field.")
            result[key] = value
        return result

    try:
        fields = json.loads(text, object_pairs_hook=closed_pairs, parse_constant=reject_constant)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Invalid identity-field JSON.") from exc
    validate_identity_fields(schema_version, fields)
    return fields


def identity_fields_digest(schema_version, fields):
    """Projection checksum, NOT a Candidate artifact hash, proof or authorization."""
    serialized = serialize_identity_fields(schema_version, fields)
    return "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_qualified_interpretations(interpretations, evidence_documents):
    """Reuse retained document qualification without bytes/ORM access or approval.

    This validates lineage only. It does not assert raw semantic support or permit
    a parent assignment. Full v3 evidence projection/approval awaits contract review.
    """
    from reference.ingestion.generation_correspondence import validate_documents

    validate_documents(evidence_documents, verify_bytes=False)
    refs = {
        "|".join((doc["source_id"], doc["raw_artifact_hash"], doc["assertion_set_id"], ast["assertion_id"]))
        for doc in evidence_documents for ast in doc["assertions"]
    }
    for interpretation in interpretations:
        if interpretation.source_assertion_ref not in refs:
            raise ValidationError("Broken document-qualified interpretation lineage.")
