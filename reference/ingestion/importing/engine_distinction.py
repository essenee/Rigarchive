"""Conservative engine proof for same-trim, same-drive Candidate v2 creates."""
import re

from django.core.exceptions import ValidationError

from reference.ingestion.generation_correspondence import digest, validate_documents
from reference.models import ImportExecutionReceipt


def _descriptor_engine(value):
    if not isinstance(value, str):
        return None
    displacements = re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*L\b", value, re.I)
    layouts = re.findall(r"\b([VI])[- ]?([1-9]\d*)\b", value, re.I)
    if len(displacements) == len(layouts) == 1:
        layout, cylinders = layouts[0]
        return float(displacements[0]), int(cylinders), layout.upper()


def _document_engine(documents):
    descriptors = [a["raw_value"] for doc in documents for a in doc["assertions"]
                   if a["attribute_key"] == "engine_descriptor"]
    if not descriptors:
        return None
    values = {_descriptor_engine(value) for value in descriptors}
    if len(values) == 1 and None not in values:
        return values.pop()


def _candidate_engine(candidate):
    documents = candidate.evidence_documents
    engine = _document_engine(documents)
    if engine is None:
        return None
    refs = {
        "|".join((doc["source_id"], doc["raw_artifact_hash"], doc["assertion_set_id"], a["assertion_id"]))
        for doc in documents for a in doc["assertions"] if a["attribute_key"] == "engine_descriptor"
    }
    for key, expected in zip(("engine_displacement_liters", "engine_cylinders"), engine[:2]):
        interpretations = [i for i in candidate.normalized_assertions if i.target_attribute_key == key]
        if not interpretations:
            return None
        for item in interpretations:
            value = item.normalized_concept
            if (item.mapping_status != "mapped" or item.source_assertion_ref not in refs
                    or getattr(value, "normalized_value", value) != expected):
                return None
            if key == "engine_displacement_liters" and getattr(value, "normalized_unit", "L") != "L":
                return None
    return engine


def _existing_engine(record):
    receipts = list(ImportExecutionReceipt.objects.filter(
        operation_type="vehicle_definition_import", execution_outcome="created",
        created_vehicle_definition=record,
    )[:2])
    if len(receipts) != 1:
        return None
    receipt = receipts[0]
    fields = {key: getattr(record, key) for key in ("model_year", "market", "trim_name", "drivetrain", "engine_name")}
    if (receipt.created_vehicle_definition_pk_snapshot != record.pk
            or receipt.created_vehicle_definition_uuid_snapshot != str(record.uuid)
            or receipt.created_vehicle_definition_slug_snapshot != record.slug
            or receipt.target_fields_json != fields
            or receipt.resolved_generation_id != record.generation_id):
        return None
    resolution = receipt.resolution_snapshot_json.get("generation_resolution", {})
    if resolution.get("parents", {}).get("generation_id") != record.generation_id:
        return None
    if resolution.get("fields") != {key: fields[key] for key in ("trim_name", "drivetrain", "engine_name")}:
        return None
    documents = resolution.get("documents", [])
    if not any(doc.get("source_id") == receipt.source_id and doc.get("raw_artifact_hash") == receipt.raw_artifact_hash
               for doc in documents):
        return None
    validate_documents(documents, verify_bytes=True)
    engine = _document_engine(documents)
    # The receipt must describe the engine represented by the canonical row.
    if engine is None or _descriptor_engine(record.engine_name) != engine:
        return None
    return engine, {"record_pk": record.pk, "record_uuid": str(record.uuid), "receipt_uuid": str(receipt.uuid),
                    "receipt_evidence_digest": digest(resolution), "engine": list(engine)}


def engine_distinction_proof(candidate, peers):
    """Require a different displacement or cylinder count from every same-drive peer.

    Equal dimensions leave identity unresolved. Labels, layout alone, boost and
    identifier spellings cannot establish an engine-based create under this rule.
    """
    if candidate.envelope.schema_version != "2.0.0" or not peers:
        return None
    try:
        validate_documents(candidate.evidence_documents, verify_bytes=True)
        engine = _candidate_engine(candidate)
        if engine is None:
            return None
        bindings = []
        for record in sorted(peers, key=lambda item: item.pk):
            existing = _existing_engine(record)
            if existing is None or existing[0][:2] == engine[:2]:
                return None
            bindings.append(existing[1])
        return {"version": "1.0", "candidate_engine": list(engine), "peers": bindings}
    except (ValidationError, OSError, KeyError, TypeError, ValueError):
        return None
