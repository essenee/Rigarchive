"""Retained human classifications using CanonicalImportAdjudication 1.1.

These declarations are human conclusions, never manufacturer source assertions.
The current consumer fills unknown controlled powertrain classifications only.
No approval, planning, execution or database write occurs in this module.
"""
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from reference.ingestion.generation_correspondence import digest, require, validate_documents

SOURCE_ID = "human_classification_adjudication"
EXTRACTOR = "approved_human_classification"


def retained_path(reference):
    root = Path(settings.BASE_DIR).resolve()
    require(isinstance(reference, str) and bool(reference), "Retained reference required.")
    path = (root / reference).resolve()
    require(path.is_relative_to(root) and path.is_file(), "Retained reference unavailable or outside BASE_DIR.")
    return path


def _base(adj):
    from reference.ingestion.serialization import deserialize_artifact, candidate_config_doc_to_dict
    from reference.ingestion.validation import validate_candidate_configuration
    anchors = adj.evidence_anchors
    raw = json.loads(retained_path(anchors["candidate_artifact_reference"]).read_text())
    require(isinstance(raw, dict) and isinstance(raw.get("envelope"), dict) and
            raw["envelope"].get("schema_version") == "2.1.0",
            "Classification consumer requires Candidate 2.1.0.")
    documents = raw.get("evidence_documents")
    require(isinstance(documents, list) and all(isinstance(d, dict) for d in documents), "Invalid base evidence.")
    # Reject chaining before deserialization invokes candidate validation, avoiding
    # recursive evaluation of a cyclic or already-adjudicated base artifact.
    require(not any(d.get("source_id") == SOURCE_ID or d.get("extractor_id") == EXTRACTOR
                    for d in documents), "Chained classification adjudications require separate review.")
    base = deserialize_artifact(raw)
    validate_candidate_configuration(base)
    require(digest(candidate_config_doc_to_dict(base)) == anchors["candidate_hash"], "Adjudication candidate became stale.")
    require(base.candidate_reference == adj.candidate_reference and
            base.candidate_identity.trim_name == adj.adjudicated_trim_name,
            "Adjudication candidate/trim scope mismatch.")
    validate_documents(base.evidence_documents, verify_bytes=True)
    return base


def validate_classification_adjudication(adj, *, require_approved=False):
    from reference.ingestion.serialization import adjudication_to_dict, compute_adjudication_hash
    from reference.powertrain import TAXONOMIES
    require(adj.adjudication_version == "1.1" and not adj.unknown_fields,
            "Unsupported classification adjudication version or fields.")
    require(adj.adjudication_category == "evidence_backed_classification" and
            adj.original_review_category == "missing_classification",
            "Unsupported classification review category.")
    require(adj.adjudication_decision in {"proposed_classifications", "approved_classifications"},
            "Unsupported classification decision.")
    require(isinstance(adj.candidate_reference, str) and bool(adj.candidate_reference) and
            isinstance(adj.adjudication_notes, str) and bool(adj.adjudication_notes.strip()),
            "Classification scope/reasoning required.")
    require(isinstance(adj.operator_label, str) and bool(adj.operator_label.strip()), "Reviewer attribution required.")
    try:
        require(datetime.fromisoformat(adj.created_at.replace("Z", "+00:00")).tzinfo is not None,
                "Aware classification review timestamp required.")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Invalid classification timestamp.") from exc
    require(adj.adjudication_hash == compute_adjudication_hash(adjudication_to_dict(adj)), "Classification adjudication hash mismatch.")
    a = adj.evidence_anchors
    require(isinstance(a, dict) and set(a) == {
        "candidate_artifact_reference", "candidate_hash", "supporting_documents", "classifications"},
        "Classification anchors require exact candidate, evidence and decisions.")
    require(adj.source_identity == {"source_id": SOURCE_ID, "source_identity_type": "candidate_digest",
                                    "native_identifier": a["candidate_hash"]}, "Classification source binding mismatch.")
    require(not adj.original_manifest_hash, "Classification review precedes separate import manifest authorization.")
    base = _base(adj)
    validate_documents(a["supporting_documents"], verify_bytes=True)
    validate_documents(base.evidence_documents + [d for d in a["supporting_documents"]
                                                  if d not in base.evidence_documents], verify_bytes=True)
    require(not any(d["source_id"] == SOURCE_ID or d["extractor_id"] == EXTRACTOR
                    for d in a["supporting_documents"]), "Human conclusions cannot be their own supporting evidence.")
    refs = {"|".join((d["source_id"], d["raw_artifact_hash"], d["assertion_set_id"], s["assertion_id"]))
            for d in base.evidence_documents + a["supporting_documents"] for s in d["assertions"]}
    claims = a["classifications"]
    require(isinstance(claims, dict) and bool(claims), "Explicit classification decisions required.")
    for key, claim in claims.items():
        require(key in TAXONOMIES, "Unsupported classification attribute.")
        require(isinstance(claim, dict) and set(claim) == {
            "value", "reasoning", "applicability", "limitations", "confidence", "source_assertion_refs", "evidence_status"},
            "Classification requires value, reasoning, scope, limitations, confidence and evidence.")
        require(isinstance(claim["value"], str) and claim["value"] in TAXONOMIES[key], "Unsupported classification value.")
        require(base.canonical_powertrain[key] is None, "Adjudication may only fill an unknown; corrections need separate review.")
        require(all(isinstance(claim[k], str) and bool(claim[k].strip()) for k in
                    ("reasoning", "applicability", "limitations")), "Classification rationale/scope/limitations required.")
        require(claim["confidence"] in {"low", "moderate", "high"} and
                claim["evidence_status"] in {"supported", "unsupported", "materially_contradictory"},
                "Explicit confidence and contradiction status required.")
        require(isinstance(claim["source_assertion_refs"], list) and bool(claim["source_assertion_refs"]) and
                all(isinstance(r, str) and r in refs for r in claim["source_assertion_refs"]),
                "Classification source reference is missing or unresolved.")
    if require_approved:
        require(adj.adjudication_decision == "approved_classifications" and
                adj.operator_label != "pending_human_signoff", "Explicit human classification approval required.")
        require(all(c["evidence_status"] == "supported" for c in claims.values()),
                "Unsupported or materially contradictory classification remains blocked.")
    return base


def _document(adj, reference, raw_hash):
    return {"source_id": SOURCE_ID, "raw_artifact_hash": raw_hash,
            "raw_artifact_reference": reference, "extractor_id": EXTRACTOR,
            "extractor_version": "1.1", "extraction_mode": "manually_verified_transcription",
            "assertion_set_id": adj.adjudication_hash, "source_locator": reference,
            "retrieved_at": adj.created_at,
            "source_applicability": {"market": _base(adj).candidate_identity.market,
                                     "applicability_scope": "configuration",
                                     "applicability_basis": "Exact candidate digest; approved human conclusion"},
            "publication_revision": "Human classification adjudication 1.1; not manufacturer assertions",
            "assertions": [{"assertion_id": k, "attribute_key": k,
                            "raw_value": {"classification": k, "value": c["value"], "provenance": "human_adjudicated"},
                            "source_context": "Human-adjudicated conclusion by " + adj.operator_label + ": " + c["reasoning"]}
                           for k, c in sorted(adj.evidence_anchors["classifications"].items())]}


def _project(base, adj, doc):
    from reference.ingestion.contracts import NormalizedInterpretation
    from reference.ingestion.normalization.generation import generation_evidence_from_documents
    result = copy.deepcopy(base)
    result.envelope.created_at = adj.created_at
    for supporting in adj.evidence_anchors["supporting_documents"]:
        if supporting not in result.evidence_documents:
            result.evidence_documents.append(copy.deepcopy(supporting))
    result.evidence_documents.append(doc)
    result.generation_evidence = generation_evidence_from_documents(result.evidence_documents)
    prefix = "|".join((SOURCE_ID, doc["raw_artifact_hash"], doc["assertion_set_id"])) + "|"
    for key, claim in sorted(adj.evidence_anchors["classifications"].items()):
        ref = prefix + key
        result.normalized_assertions.append(NormalizedInterpretation(
            ref, ref, key, claim["value"],
            raw_source_value={"classification": key, "value": claim["value"], "provenance": "human_adjudicated"},
            normalization_notes="Approved human-derived classification; not a direct manufacturer assertion. " + claim["reasoning"]))
        result.attribute_provenance.setdefault(key, []).append(ref)
        result.canonical_powertrain[key] = claim["value"]
    result.evidence_raw_hashes = sorted({d["raw_artifact_hash"] for d in result.evidence_documents})
    return result


def apply_classification_adjudication(reference):
    """Return a separate candidate revision only from a retained approved artifact."""
    from reference.ingestion.serialization import adjudication_from_dict
    path = retained_path(reference)
    raw = path.read_bytes()
    adj = adjudication_from_dict(json.loads(raw))
    base = validate_classification_adjudication(adj, require_approved=True)
    doc = _document(adj, str(path.relative_to(Path(settings.BASE_DIR).resolve())),
                    "sha256:" + hashlib.sha256(raw).hexdigest())
    return _project(base, adj, doc)


def validate_classification_candidate(candidate):
    """Validate the entire approved projection again at validation/execution time."""
    from reference.ingestion.serialization import candidate_config_doc_to_dict
    docs = [d for d in candidate.evidence_documents if d["source_id"] == SOURCE_ID or d["extractor_id"] == EXTRACTOR]
    if not docs:
        return
    require(len(docs) == 1, "Exactly one bound classification adjudication is supported.")
    validate_documents(docs, verify_bytes=True)
    expected = apply_classification_adjudication(docs[0]["raw_artifact_reference"])
    require(candidate_config_doc_to_dict(expected) == candidate_config_doc_to_dict(candidate),
            "Candidate differs from its approved human classification projection.")


def validate_classification_documents(documents):
    """Retained peer receipts must still reference the exact approved declaration."""
    from reference.ingestion.serialization import adjudication_from_dict
    for doc in documents:
        if doc["source_id"] != SOURCE_ID and doc["extractor_id"] != EXTRACTOR:
            continue
        validate_documents([doc], verify_bytes=True)
        adj = adjudication_from_dict(json.loads(retained_path(doc["raw_artifact_reference"]).read_text()))
        validate_classification_adjudication(adj, require_approved=True)
        require(doc == _document(adj, doc["raw_artifact_reference"], doc["raw_artifact_hash"]),
                "Peer classification declaration binding changed.")
