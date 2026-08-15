"""
Canonical Import Review Manifest contracts and serialization logic.

Provides pure-Python data structures for serializing, validating, hashing, and reconstructing
operator-reviewed CanonicalImportPlan artifacts prior to execution dispatch.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from reference.ingestion.importing import (
    CanonicalImportPlan,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportPlannedAction,
)

MANIFEST_VERSION = "1.0"
SHA256_REGEX = re.compile(r"^sha256:[0-9a-f]{64}$")


class ManifestValidationError(Exception):
    """Raised when a review manifest is malformed, corrupted, or fails validation."""
    pass


@dataclass
class CanonicalImportReviewPlan:
    """
    Serializable review artifact representation of a single CanonicalImportPlan.
    Contains all 13 fields required for exact plan reconstruction plus source identity metadata.
    """
    candidate_reference: str
    source_identity_type: str
    native_identifier: str
    eligibility_status: str
    planned_action: str
    create_basis: Optional[str] = None
    namespace_snapshot_count: Optional[int] = None
    mechanical_basis_existing_id: Optional[int] = None
    resolved_manufacturer_id: Optional[int] = None
    resolved_vehicle_model_id: Optional[int] = None
    resolved_generation_id: Optional[int] = None
    target_vehicle_definition_fields: Dict[str, Any] = field(default_factory=dict)
    target_slug: Optional[str] = None
    existing_vehicle_definition_id: Optional[int] = None
    reasons: List[str] = field(default_factory=list)


@dataclass
class CanonicalImportReviewManifest:
    """
    Top-level immutable review manifest snapshot capturing source evidence provenance,
    extraction metadata, and a list of reviewed candidate import plans.
    """
    manifest_version: str
    created_at: str
    source_id: str
    raw_artifact_hash: str
    raw_artifact_reference: str
    extraction_provenance: Dict[str, Any]
    plans: List[CanonicalImportReviewPlan]
    manifest_hash: str


def canonicalize_manifest_dict(d: Dict[str, Any]) -> bytes:
    """
    Serializes a dictionary into canonical UTF-8 bytes for SHA-256 hash computation.
    Enforces key sorting, UTF-8 encoding, and compact separators (",", ":").
    """
    return json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def compute_manifest_hash(manifest_dict_without_hash: Dict[str, Any]) -> str:
    """
    Computes a deterministic sha256:<64_lowercase_hex> content digest over canonicalized JSON bytes.
    """
    canonical_bytes = canonicalize_manifest_dict(manifest_dict_without_hash)
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


def build_review_manifest(
    source_id: str,
    raw_artifact_hash: str,
    raw_artifact_reference: str,
    extraction_provenance: Dict[str, Any],
    plans: List[CanonicalImportPlan],
    native_identifiers: Optional[Dict[str, str]] = None,
    source_identity_type: str = "record_id",
) -> CanonicalImportReviewManifest:
    """
    Constructs a CanonicalImportReviewManifest from in-memory planning results and evidence metadata.
    Automatically computes the canonical manifest_hash digest.
    """
    native_map = native_identifiers or {}
    review_plans: List[CanonicalImportReviewPlan] = []

    for plan in plans:
        native_id = native_map.get(plan.candidate_reference, "")
        rp = CanonicalImportReviewPlan(
            candidate_reference=plan.candidate_reference,
            source_identity_type=source_identity_type,
            native_identifier=native_id,
            eligibility_status=plan.eligibility_status.value,
            planned_action=plan.planned_action.value,
            create_basis=plan.create_basis.value if plan.create_basis else None,
            namespace_snapshot_count=plan.namespace_snapshot_count,
            mechanical_basis_existing_id=plan.mechanical_basis_existing_id,
            resolved_manufacturer_id=plan.resolved_manufacturer_id,
            resolved_vehicle_model_id=plan.resolved_vehicle_model_id,
            resolved_generation_id=plan.resolved_generation_id,
            target_vehicle_definition_fields=dict(plan.target_vehicle_definition_fields),
            target_slug=plan.target_slug,
            existing_vehicle_definition_id=plan.existing_vehicle_definition_id,
            reasons=list(plan.reasons),
        )
        review_plans.append(rp)

    manifest_dict_no_hash = {
        "manifest_version": MANIFEST_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_id": source_id,
        "raw_artifact_hash": raw_artifact_hash,
        "raw_artifact_reference": raw_artifact_reference,
        "extraction_provenance": extraction_provenance,
        "plans": [asdict(p) for p in review_plans],
    }

    manifest_hash = compute_manifest_hash(manifest_dict_no_hash)

    return CanonicalImportReviewManifest(
        manifest_version=manifest_dict_no_hash["manifest_version"],
        created_at=manifest_dict_no_hash["created_at"],
        source_id=source_id,
        raw_artifact_hash=raw_artifact_hash,
        raw_artifact_reference=raw_artifact_reference,
        extraction_provenance=extraction_provenance,
        plans=review_plans,
        manifest_hash=manifest_hash,
    )


def manifest_to_dict(manifest: CanonicalImportReviewManifest) -> Dict[str, Any]:
    """Converts a CanonicalImportReviewManifest object to a serializable dictionary."""
    return asdict(manifest)


def dict_to_manifest(d: Dict[str, Any]) -> CanonicalImportReviewManifest:
    """
    Parses and strictly validates a manifest dictionary.
    Re-computes and verifies manifest_hash content digest.
    Raises ManifestValidationError on any validation failure.
    """
    if not isinstance(d, dict):
        raise ManifestValidationError("Manifest root must be a JSON object.")

    # Strict top-level key check
    allowed_top_level = {
        "manifest_version",
        "created_at",
        "source_id",
        "raw_artifact_hash",
        "raw_artifact_reference",
        "extraction_provenance",
        "plans",
        "manifest_hash",
    }
    extra_keys = set(d.keys()) - allowed_top_level
    if extra_keys:
        raise ManifestValidationError(f"Unknown top-level fields in manifest: {sorted(list(extra_keys))}")

    missing_keys = allowed_top_level - set(d.keys())
    if missing_keys:
        raise ManifestValidationError(f"Missing required top-level fields: {sorted(list(missing_keys))}")

    if d["manifest_version"] != MANIFEST_VERSION:
        raise ManifestValidationError(
            f"Unsupported manifest version '{d['manifest_version']}'. Expected '{MANIFEST_VERSION}'."
        )

    if not SHA256_REGEX.match(str(d["raw_artifact_hash"])):
        raise ManifestValidationError(f"Invalid raw_artifact_hash format: '{d['raw_artifact_hash']}'.")

    if not SHA256_REGEX.match(str(d["manifest_hash"])):
        raise ManifestValidationError(f"Invalid manifest_hash format: '{d['manifest_hash']}'.")

    if not isinstance(d["plans"], list):
        raise ManifestValidationError("Manifest 'plans' must be a list.")

    # Verify manifest hash equality
    d_copy = dict(d)
    supplied_hash = d_copy.pop("manifest_hash")
    computed_hash = compute_manifest_hash(d_copy)

    if computed_hash != supplied_hash:
        raise ManifestValidationError(
            f"Manifest hash mismatch: computed '{computed_hash}', supplied '{supplied_hash}'."
        )

    allowed_plan_keys = {
        "candidate_reference",
        "source_identity_type",
        "native_identifier",
        "eligibility_status",
        "planned_action",
        "create_basis",
        "namespace_snapshot_count",
        "mechanical_basis_existing_id",
        "resolved_manufacturer_id",
        "resolved_vehicle_model_id",
        "resolved_generation_id",
        "target_vehicle_definition_fields",
        "target_slug",
        "existing_vehicle_definition_id",
        "reasons",
    }

    seen_refs = set()
    review_plans: List[CanonicalImportReviewPlan] = []

    valid_eligibility = {e.value for e in ImportEligibilityStatus}
    valid_actions = {a.value for a in ImportPlannedAction}
    valid_bases = {b.value for b in ImportCreateBasis}

    for idx, p_dict in enumerate(d["plans"]):
        if not isinstance(p_dict, dict):
            raise ManifestValidationError(f"Plan entry at index {idx} must be a dictionary.")

        extra_p_keys = set(p_dict.keys()) - allowed_plan_keys
        if extra_p_keys:
            raise ManifestValidationError(
                f"Unknown plan fields in plan index {idx}: {sorted(list(extra_p_keys))}"
            )

        missing_p_keys = allowed_plan_keys - set(p_dict.keys())
        if missing_p_keys:
            raise ManifestValidationError(
                f"Missing required plan fields in plan index {idx}: {sorted(list(missing_p_keys))}"
            )

        ref = p_dict["candidate_reference"]
        if not ref or not isinstance(ref, str):
            raise ManifestValidationError(f"Plan index {idx} missing valid candidate_reference string.")

        if ref in seen_refs:
            raise ManifestValidationError(f"Duplicate candidate_reference '{ref}' found in manifest.")
        seen_refs.add(ref)

        if p_dict["eligibility_status"] not in valid_eligibility:
            raise ManifestValidationError(
                f"Invalid eligibility_status '{p_dict['eligibility_status']}' in plan '{ref}'."
            )

        if p_dict["planned_action"] not in valid_actions:
            raise ManifestValidationError(
                f"Invalid planned_action '{p_dict['planned_action']}' in plan '{ref}'."
            )

        cb = p_dict["create_basis"]
        if cb is not None and cb not in valid_bases:
            raise ManifestValidationError(
                f"Invalid create_basis '{cb}' in plan '{ref}'."
            )

        target_fields = p_dict["target_vehicle_definition_fields"]
        if not isinstance(target_fields, dict):
            raise ManifestValidationError(
                f"target_vehicle_definition_fields must be a dictionary in plan '{ref}'."
            )

        int_fields = (
            "namespace_snapshot_count",
            "mechanical_basis_existing_id",
            "resolved_manufacturer_id",
            "resolved_vehicle_model_id",
            "resolved_generation_id",
            "existing_vehicle_definition_id",
        )
        for f_name in int_fields:
            val = p_dict[f_name]
            if val is not None and (not isinstance(val, int) or isinstance(val, bool)):
                raise ManifestValidationError(
                    f"Field '{f_name}' in plan '{ref}' must be a strict integer or null, got '{type(val).__name__}'."
                )

        if p_dict["target_slug"] is not None and not isinstance(p_dict["target_slug"], str):
            raise ManifestValidationError(f"target_slug in plan '{ref}' must be a string or null.")

        if not isinstance(p_dict["reasons"], list):
            raise ManifestValidationError(f"reasons in plan '{ref}' must be a list.")


        rp = CanonicalImportReviewPlan(
            candidate_reference=ref,
            source_identity_type=str(p_dict["source_identity_type"]),
            native_identifier=str(p_dict["native_identifier"]),
            eligibility_status=str(p_dict["eligibility_status"]),
            planned_action=str(p_dict["planned_action"]),
            create_basis=cb,
            namespace_snapshot_count=p_dict["namespace_snapshot_count"],
            mechanical_basis_existing_id=p_dict["mechanical_basis_existing_id"],
            resolved_manufacturer_id=p_dict["resolved_manufacturer_id"],
            resolved_vehicle_model_id=p_dict["resolved_vehicle_model_id"],
            resolved_generation_id=p_dict["resolved_generation_id"],
            target_vehicle_definition_fields=target_fields,
            target_slug=p_dict["target_slug"],
            existing_vehicle_definition_id=p_dict["existing_vehicle_definition_id"],
            reasons=list(p_dict["reasons"]),
        )
        review_plans.append(rp)

    return CanonicalImportReviewManifest(
        manifest_version=d["manifest_version"],
        created_at=d["created_at"],
        source_id=d["source_id"],
        raw_artifact_hash=d["raw_artifact_hash"],
        raw_artifact_reference=d["raw_artifact_reference"],
        extraction_provenance=dict(d["extraction_provenance"]),
        plans=review_plans,
        manifest_hash=supplied_hash,
    )


def reconstruct_plan_from_manifest(review_plan: CanonicalImportReviewPlan) -> CanonicalImportPlan:
    """
    Reconstructs an exact executable CanonicalImportPlan object from a reviewed CanonicalImportReviewPlan.
    Performs zero dynamic re-planning calls to plan_candidate_import().
    """
    return CanonicalImportPlan(
        candidate_reference=review_plan.candidate_reference,
        eligibility_status=ImportEligibilityStatus(review_plan.eligibility_status),
        planned_action=ImportPlannedAction(review_plan.planned_action),
        create_basis=ImportCreateBasis(review_plan.create_basis) if review_plan.create_basis else None,
        namespace_snapshot_count=review_plan.namespace_snapshot_count,
        mechanical_basis_existing_id=review_plan.mechanical_basis_existing_id,
        resolved_manufacturer_id=review_plan.resolved_manufacturer_id,
        resolved_vehicle_model_id=review_plan.resolved_vehicle_model_id,
        resolved_generation_id=review_plan.resolved_generation_id,
        target_vehicle_definition_fields=dict(review_plan.target_vehicle_definition_fields),
        target_slug=review_plan.target_slug,
        existing_vehicle_definition_id=review_plan.existing_vehicle_definition_id,
        reasons=list(review_plan.reasons),
    )
