"""RA-049 exact authorization and atomic SQLite batch executor; no parent writes."""
from copy import deepcopy
from datetime import datetime, timezone

from django.core.exceptions import ValidationError
from django.db import transaction

from reference import candidate_v3 as wire
from reference.ingestion import body_import_contracts as c
from reference.ingestion.matrix_approval import validate_matrix_approval
from reference.ingestion.importing.body_identity import plan_resolved, stamp, vehicle_state
from reference.models import VehicleDefinition, ImportExecutionReceipt


def build_matrix(plans):
    if plans and plans[0].get("plan_version") == "3.1.0":
        from .registry_body_import import build_matrix as build
        return build(plans)
    plans = sorted(plans, key=lambda p: p["candidate_reference"])
    c.require(bool(plans), "No selected plans.")
    for plan in plans:
        c.validate("Plan3", plan)
    first = plans[0]
    family_hash = c.digest(first["proof"]["family"])
    for plan in plans:
        c.require(plan["generation"]["scope"] == first["generation"]["scope"] and c.digest(plan["proof"]["family"]) == family_hash, "Different family/scope in selected batch.")
        c.require(plan["generation"]["parent_state"] == first["generation"]["parent_state"], "Generation parent states differ.")
        for key in ("body_namespace", "peers", "generation_slugs"):
            # Peer relations depend on the subject; compare the underlying states.
            if key == "peers":
                a = [p["vehicle"] for p in plan["proof"][key]]
                b = [p["vehicle"] for p in first["proof"][key]]
            else:
                a, b = plan["proof"][key], first["proof"][key]
            c.require(a == b, "Plans do not share the common pre-batch state.")
    result = {"matrix_version": c.VERSION, "profile": c.PROFILE, "scope": first["generation"]["scope"], "family_hash": family_hash, "body_writes": False, "rows": [c.authorization_row(p) for p in plans]}
    return c.validate("Matrix3", result)


def build_manifest(matrix, approval):
    if matrix.get("matrix_version") == "3.1.0":
        from .registry_body_import import build_manifest as build
        return build(matrix, approval)
    c.validate("Matrix3", matrix)
    validate_matrix_approval(matrix, approval)
    result = c.seal({"manifest_version": c.VERSION, "matrix": deepcopy(matrix), "matrix_digest": c.digest(matrix), "approval": deepcopy(approval), "approval_hash": c.digest(approval)}, "manifest_hash")
    return c.validate("Manifest3", result)


def validate_selection(manifest, plans):
    if manifest.get("manifest_version") == "3.1.0":
        from .registry_body_import import validate_selection as validate
        return validate(manifest, plans)
    c.validate("Manifest3", manifest)
    validate_matrix_approval(manifest["matrix"], manifest["approval"])
    c.require(type(plans) is list and [p["candidate_reference"] for p in plans] == [r["candidate_reference"] for r in manifest["matrix"]["rows"]], "Execution plan order/membership differs from authorized Matrix.")
    rebuilt = build_matrix(plans)
    c.require(rebuilt == manifest["matrix"], "Exact selected plans differ from authorized Matrix.")


def revalidate(manifest, plans, release):
    if manifest.get("manifest_version") == "3.1.0":
        from .registry_body_import import revalidate as validate
        return validate(manifest, plans, release)
    validate_selection(manifest, plans)
    diagnostics = []
    try:
        candidates, contexts, family = release.load()
        for old in plans:
            key = old["candidate_reference"]
            fresh = plan_resolved(candidates[key], *contexts[key], family, release)
            c.require(fresh == old, "Candidate/evidence/body/peer/family/slug state changed.")
    except (ValidationError, OSError, ValueError, KeyError) as exc:
        diagnostics.append({"stage": "resolution", "code": "STALE_PLAN", "path": "/", "message": str(exc)})
    report = c.seal({"revalidation_version": c.VERSION, "manifest_hash": manifest["manifest_hash"], "matrix_digest": manifest["matrix_digest"], "approval_hash": manifest["approval_hash"], "family_hash": manifest["matrix"]["family_hash"],
        "rows": [{"candidate_reference": p["candidate_reference"], "plan_hash": p["plan_hash"], "proof_hash": p["proof"]["proof_hash"], "baseline_digest": p["proof"]["baseline_digest"], "body_state_hash": p["proof"]["body_state_hash"]} for p in sorted(plans, key=lambda p: p["candidate_reference"])],
        "result": "stale" if diagnostics else "valid", "diagnostics": diagnostics}, "revalidation_hash")
    return c.validate("Revalidation3", report)


def _persist(plan, manifest, report, agent, *, registry_plan=None):
    fields = plan["target_fields"]
    if plan["action"] == "create":
        vd = VehicleDefinition(generation_id=plan["generation"]["scope"]["generation"]["pk"],
            factory_body_configuration_id=plan["body"]["pk"], slug=plan["target_slug"],
            **({"engine_id": next(e["binding"]["engine"]["pk"] for e in registry_plan["engine_bindings"] if e["candidate_reference"] == plan["candidate_reference"])} if registry_plan else {}),
            **{k: fields[k] for k in ("model_year", "trim_name", "engine_name", "drivetrain", "market")}, **fields["canonical_powertrain"])
        vd.full_clean()
        vd.save()
    else:
        vd = VehicleDefinition.objects.get(uuid=plan["existing_vehicle_uuid"])
    actual = vehicle_state(vd)
    persisted = actual["fields"] | {"factory_body_configuration_uuid": actual["body"]["uuid"] if actual["body"] else None}
    c.require(persisted == fields and vd.slug == plan["target_slug"], "Persisted state differs from exact plan.")
    if registry_plan is not None:
        from .registry_body_import import receipt_snapshot
        snapshot = receipt_snapshot(registry_plan, manifest, report, vd, persisted, agent)
    else:
        snapshot = c.seal({"receipt_version": c.VERSION, "profile": c.PROFILE, "manifest": deepcopy(manifest), "plan": deepcopy(plan), "revalidation": deepcopy(report),
        "outcome": "created" if plan["action"] == "create" else "no_op", "vehicle": {"pk": vd.pk, "uuid": str(vd.uuid), "slug": vd.slug}, "persisted_fields": persisted,
        "execution_agent": agent, "executed_at_utc": stamp(datetime.now(timezone.utc))}, "snapshot_hash")
        c.validate("Receipt3", snapshot)
    candidate = plan["candidate_snapshot"]
    first_ref = candidate["configuration_refs"][0]
    doc, _ = wire.evidence_index(candidate)[first_ref]
    source = [g for g in candidate["generation_evidence"] if g["source_id"] == doc["source_id"] and g["document_hash"] == doc["raw_artifact_hash"] and g["assertion_set_id"] == doc["assertion_set_id"]]
    c.require(bool(source), "Source identity for primary attribution is unavailable.")
    source.sort(key=lambda g: (g["source_id"], g["document_hash"], g["assertion_set_id"], g["assertion_id"]))
    created = plan["action"] == "create"
    return ImportExecutionReceipt.objects.create(
        operation_type="vehicle_definition_import", execution_channel="cli", operator_label=manifest["approval"]["operator"],
        manifest_hash=manifest["manifest_hash"], candidate_reference=plan["candidate_reference"], planned_action="create" if created else "no_op_exact_match",
        create_basis="body_aware_identity" if created else "", source_id=doc["source_id"], raw_artifact_hash=doc["raw_artifact_hash"], raw_artifact_reference=doc["raw_artifact_reference"],
        source_identity_type=source[0]["identity_type"], native_identifier=source[0]["native_identifier"], resolved_generation_id=vd.generation_id,
        target_slug=vd.slug, target_model_year=vd.model_year, target_trim_name=vd.trim_name, target_engine_name=vd.engine_name, target_drivetrain=vd.drivetrain, target_market=vd.market,
        target_fields_json=fields, resolution_snapshot_json={"body_import": snapshot}, execution_outcome="created" if created else "no_op_exact_match", messages_json=[],
        created_vehicle_definition=vd if created else None, created_vehicle_definition_pk_snapshot=vd.pk if created else None,
        created_vehicle_definition_uuid_snapshot=str(vd.uuid) if created else "", created_vehicle_definition_slug_snapshot=vd.slug if created else "",
        existing_vehicle_definition=vd if not created else None, existing_vehicle_definition_pk_snapshot=vd.pk if not created else None,
        existing_vehicle_definition_uuid_snapshot=str(vd.uuid) if not created else "", existing_vehicle_definition_slug_snapshot=vd.slug if not created else "",
    )


def execute_body_import_batch(manifest, plans, release, *, operator, execution_agent, confirmed=False, review_only=False):
    """Caller must have obtained actual affirmative human confirmation, as approval1.

    A supplied manifest/approval object alone is not execution permission. This method
    never retries SQLite conflicts and never catches an error inside the transaction.
    The caller handles rolled-back failures separately from post-commit reporting.
    """
    protocol = None
    if isinstance(manifest, dict) and manifest.get("manifest_version") == "3.1.0":
        from . import registry_body_import as protocol
    c.require(bool(getattr(release, "registry_aware", False)) == bool(protocol), "Registry-aware releases require the exact 3.1.0 authorization envelope.")
    c.require(confirmed is True and review_only is False, "Explicit human confirmation required; review-only cannot execute.")
    from reference.ingestion.attribution import resolve_attribution
    attribution = resolve_attribution(operator=operator, agent=execution_agent)
    c.require(attribution.director == operator and attribution.agent == execution_agent, "Attribution mismatch.")
    c.validate("Text", execution_agent)
    (protocol.validate("Manifest", manifest) if protocol else c.validate("Manifest3", manifest))
    c.require(operator == manifest.get("approval", {}).get("operator"), "Execution operator differs from affirmative approval.")
    (protocol.validate_selection(manifest, plans) if protocol else validate_selection(manifest, plans))
    with transaction.atomic():
        if protocol:
            protocol.lock_engines(plans)
        report = protocol.revalidate(manifest, plans, release) if protocol else revalidate(manifest, plans, release)
        c.require(report["result"] == "valid", "STALE_PLAN: complete independent revalidation failed.")
        # Every selected row was revalidated against the same pre-batch database state.
        receipts = [(protocol.persist(p, manifest, report, execution_agent) if protocol else _persist(p, manifest, report, execution_agent)) for p in sorted(plans, key=lambda p: p.get("candidate_reference", p.get("body_plan", {}).get("candidate_reference")))]
    return receipts
