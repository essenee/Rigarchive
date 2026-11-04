"""Preserve explicit source generation identities; never guess a canonical Generation."""
from dataclasses import asdict

from reference.ingestion.generation_correspondence import require

GENERATION_KEYS = {"generation_designation", "generation_code", "source_model_code", "generation_section"}


def generation_evidence_from_sets(assertion_sets):
    documents = []
    for sas in assertion_sets:
        provenance = sas.provenance
        ep = provenance.extraction_provenance
        require(ep is not None, "Candidate v2 requires retained extraction provenance.")
        set_id = provenance.native_record_id
        require(bool(set_id), "Candidate v2 requires a source-local assertion-set identity.")
        documents.append({
            "source_id": provenance.source_id, "raw_artifact_hash": ep.raw_artifact_hash,
            "raw_artifact_reference": ep.raw_artifact_reference, "extractor_id": ep.extractor_id,
            "extractor_version": ep.extractor_version, "extraction_mode": ep.extraction_mode,
            "assertion_set_id": set_id,
            "source_locator": provenance.source_locator, "retrieved_at": provenance.retrieved_at,
            "source_applicability": asdict(provenance.source_applicability) if provenance.source_applicability else None,
            "publication_revision": provenance.unknown_fields.get("publication_revision"),
            "generation_normalizer": {"id": "explicit_generation_identity", "version": "1.0.0"},
            "assertions": [{"assertion_id": a.assertion_id, "attribute_key": a.attribute_key,
                            "raw_value": a.raw_value, "source_context": a.source_context or ""}
                           for a in sas.source_assertions],
        })
    return generation_evidence_from_documents(documents), documents


def generation_evidence_from_documents(documents):
    """Expected projection of retained assertions, not a canonical Generation mapping.

    Callers validating an existing candidate compare this result with its submitted
    projection; they must never replace missing entries to make it executable.
    Unknown values and contradictory assertions retain their own source identity.
    """
    identities = []
    for doc in documents:
        for ast in doc["assertions"]:
            key = ast["attribute_key"]
            if key in GENERATION_KEYS:
                value = ast["raw_value"]
                require(value is not None and bool(str(value).strip()), "Empty explicit generation identity.")
                identities.append({
                    "source_id": doc["source_id"], "source_namespace": key,
                    "identity_type": "model_code" if key == "source_model_code" else "generation_designation",
                    "native_identifier": str(value).strip(), "document_hash": doc["raw_artifact_hash"],
                    "assertion_set_id": doc["assertion_set_id"], "assertion_id": ast["assertion_id"],
                    "normalizer_id": "explicit_generation_identity", "normalizer_version": "1.0.0",
                })
    return identities
