"""ADR-0010: bounded reviewed correspondence publication and deterministic resolution.

Publication and import are separate authorizations. All filesystem references are
confined to BASE_DIR; acquired evidence must be retained before using this module.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, transaction

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
RESTRICTIONS = {"trim_name", "engine_name", "drivetrain"}
REVIEW_KEYS = {
    "review_version", "revision_uuid", "correspondence_uuid", "revision_number",
    "supersedes_uuid", "vehicle_model_uuid", "generation_uuid", "source_id",
    "source_namespace", "identity_type", "native_identifier", "market", "start_year",
    "end_year", "restrictions", "evidence", "finding", "reviewer", "reviewed_at", "review_notes",
}


class CorrespondenceReceiptError(RuntimeError):
    """Infrastructure failure: the enclosing publication transaction must roll back."""


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_documents(documents, verify_bytes=False):
    require(isinstance(documents, list) and bool(documents), "Retained document evidence is required.")
    seen = set()
    for doc in documents:
        require(isinstance(doc, dict), "Evidence must be a document object.")
        for key in ("source_id", "raw_artifact_hash", "raw_artifact_reference", "extractor_id",
                    "extractor_version", "extraction_mode", "assertion_set_id"):
            require(isinstance(doc.get(key), str) and bool(doc[key]), f"Missing document {key}.")
        require(bool(SHA256.fullmatch(doc["raw_artifact_hash"])), "Invalid evidence hash.")
        require("|" not in doc["source_id"] and "|" not in doc["assertion_set_id"],
                "Reserved qualifier separator in document identity.")
        key = (doc["source_id"], doc["raw_artifact_hash"], doc["assertion_set_id"])
        require(key not in seen, "Duplicate document/assertion-set evidence.")
        seen.add(key)
        assertions = doc.get("assertions")
        require(isinstance(assertions, list) and bool(assertions), "Source assertions must be retained.")
        ids = set()
        for ast in assertions:
            require(isinstance(ast, dict) and isinstance(ast.get("assertion_id"), str)
                    and ast["assertion_id"] and ast["assertion_id"] not in ids,
                    "Invalid/duplicate document-local assertion ID.")
            ids.add(ast["assertion_id"])
            require("|" not in ast["assertion_id"], "Reserved qualifier separator in local assertion ID.")
            require(isinstance(ast.get("attribute_key"), str) and ast["attribute_key"], "Missing assertion key.")
            require("raw_value" in ast and isinstance(ast.get("source_context"), str)
                    and bool(ast["source_context"]), "Assertion value/location required.")
        if verify_bytes:
            root = Path(settings.BASE_DIR).resolve()
            path = (root / doc["raw_artifact_reference"]).resolve()
            require(path.is_relative_to(root) and path.is_file(), "Evidence reference is unavailable or outside BASE_DIR.")
            actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            require(actual == doc["raw_artifact_hash"], "Retained source bytes changed.")


def validate_review_payload(payload):
    require(isinstance(payload, dict) and set(payload) == REVIEW_KEYS, "Unsupported correspondence review fields.")
    require(payload["review_version"] == "1.0", "Unsupported correspondence review version.")
    for key in ("revision_uuid", "correspondence_uuid", "vehicle_model_uuid"):
        try:
            UUID(payload[key])
        except (ValueError, TypeError, AttributeError):
            raise ValidationError(f"Invalid {key}.")
    for key in ("generation_uuid", "supersedes_uuid"):
        if payload[key] is not None:
            try:
                UUID(payload[key])
            except (ValueError, TypeError, AttributeError):
                raise ValidationError(f"Invalid {key}.")
    for key in ("revision_number", "start_year", "end_year"):
        require(type(payload[key]) is int, f"{key} must be an integer.")
    require(payload["revision_number"] >= 1 and 1886 <= payload["start_year"] <= payload["end_year"] <= 2100,
            "Invalid revision/year scope.")
    require(payload["market"] in ("US", "CA", "OT"), "Invalid commercial market.")
    require(payload["finding"] in ("established", "ambiguous", "rejected", "withdrawn"), "Invalid review finding.")
    require(payload["finding"] != "established" or bool(payload["generation_uuid"]), "Established finding needs a target.")
    for key in ("source_id", "source_namespace", "identity_type", "native_identifier", "reviewer", "review_notes"):
        require(isinstance(payload[key], str) and bool(payload[key].strip()), f"Missing {key}.")
    try:
        reviewed = datetime.fromisoformat(payload["reviewed_at"])
        require(reviewed.tzinfo is not None, "Review time must include timezone.")
        require(payload["reviewed_at"] == reviewed.astimezone(timezone.utc).isoformat(),
                "Review time must use canonical UTC ISO format with +00:00.")
    except (ValueError, TypeError):
        raise ValidationError("Invalid review time.")
    restrictions = payload["restrictions"]
    require(isinstance(restrictions, dict) and set(restrictions) <= RESTRICTIONS,
            "Unrepresented configuration restriction.")
    require(all(isinstance(v, str) and bool(v) for v in restrictions.values()), "Invalid restriction value.")
    validate_documents(payload["evidence"])
    require(any(
        doc["source_id"] == payload["source_id"] and
        doc.get("generation_normalizer") == {"id": "explicit_generation_identity", "version": "1.0.0"} and any(
            ast["attribute_key"] == payload["source_namespace"] and
            str(ast["raw_value"]).strip() == payload["native_identifier"]
            for ast in doc["assertions"]
        ) for doc in payload["evidence"]
    ), "Reviewed source selector is not established by retained assertions.")


def publish_correspondence(payload, content_hash, *, authorized=False, operator_label=""):
    """Insert immutable revision + receipt, or persist a stale/rejected attempt only.

    Unique chain/revision and predecessor constraints arbitrate concurrent writers.
    Failed insert transactions are rolled back before the failure receipt is saved.
    Storage failures propagate: no success is returned if receipt persistence fails.
    """
    from reference.models import GenerationCorrespondenceRevision as Revision, VehicleModel, Generation, ImportExecutionReceipt
    require(authorized, "Correspondence publication requires explicit authorization.")
    validate_review_payload(payload)
    require(content_hash == digest(payload), "Review content hash mismatch.")

    def _receipt(outcome, revision=None, message=""):
        first = payload["evidence"][0]
        return ImportExecutionReceipt.objects.create(
            operation_type="correspondence_publication", operator_label=operator_label or payload["reviewer"],
            manifest_hash=content_hash, candidate_reference=payload["revision_uuid"], planned_action="publish",
            source_id=payload["source_id"], raw_artifact_hash=first["raw_artifact_hash"],
            raw_artifact_reference=first["raw_artifact_reference"], native_identifier=payload["native_identifier"],
            source_identity_type=payload["identity_type"], target_slug="",
            execution_outcome=outcome, messages_json=[message] if message else [],
            correspondence_revision=revision,
            resolution_snapshot_json={"review": payload, "content_hash": content_hash},
        )

    def receipt(outcome, revision=None, message=""):
        try:
            return _receipt(outcome, revision, message)
        except Exception as exc:
            raise CorrespondenceReceiptError("Publication receipt failed; no success committed.") from exc

    # Verification failures are domain rejection; receipt/infrastructure errors are not.
    try:
        validate_documents(payload["evidence"], verify_bytes=True)
    except (ValidationError, OSError) as exc:
        return None, receipt("rejected", message=str(exc))

    try:
        with transaction.atomic():
            existing = Revision.objects.filter(uuid=payload["revision_uuid"]).first()
            if existing:
                if existing.content_hash == content_hash:
                    existing.clean()
                    require(existing.content_hash == digest(existing.review_payload()), "Published revision integrity changed.")
                    return existing, receipt("no_op_exact_match", existing)
                return None, receipt("aborted_stale_plan", message="Revision UUID already has different content.")
            previous = None
            if payload["supersedes_uuid"]:
                previous = Revision.objects.get(uuid=payload["supersedes_uuid"])
                if Revision.objects.filter(supersedes=previous).exists():
                    return None, receipt("aborted_stale_plan", message="Predecessor already superseded.")
            vm = VehicleModel.objects.get(uuid=payload["vehicle_model_uuid"])
            gen = Generation.objects.get(uuid=payload["generation_uuid"]) if payload["generation_uuid"] else None
            revision = Revision(
                uuid=payload["revision_uuid"], correspondence_uuid=payload["correspondence_uuid"],
                revision_number=payload["revision_number"], supersedes=previous, vehicle_model=vm, generation=gen,
                **{k: payload[k] for k in ("source_id", "source_namespace", "identity_type", "native_identifier",
                                          "market", "start_year", "end_year", "restrictions", "evidence",
                                          "finding", "reviewer", "review_notes")},
                reviewed_at=datetime.fromisoformat(payload["reviewed_at"]), content_hash=content_hash,
            )
            revision.save()
            return revision, receipt("created", revision)
    except (IntegrityError, ValidationError, Revision.DoesNotExist, VehicleModel.DoesNotExist, Generation.DoesNotExist) as exc:
        # Outside the rolled-back atomic block; no partial canonical publication survives.
        return None, receipt("aborted_stale_plan", message=str(exc))
    except OperationalError as exc:
        # SQLite may reject a competing read-to-write upgrade rather than wait.
        if "locked" not in str(exc).lower():
            raise
        return None, receipt("aborted_stale_plan", message="Concurrent publication; fresh review required.")


def parent_snapshot(vm, generation):
    return {
        "manufacturer_id": vm.manufacturer_id, "manufacturer_uuid": str(vm.manufacturer.uuid),
        "manufacturer_name": vm.manufacturer.name, "manufacturer_active": vm.manufacturer.is_active,
        "vehicle_model_id": vm.pk, "vehicle_model_uuid": str(vm.uuid), "vehicle_model_name": vm.name,
        "vehicle_model_active": vm.is_active, "generation_id": generation.pk,
        "generation_uuid": str(generation.uuid), "generation_active": generation.is_active,
        "generation_model_id": generation.vehicle_model_id,
        "start_year": generation.start_year, "end_year": generation.end_year,
    }


def _applicable_revisions(vm, year, market, identities):
    from reference.models import GenerationCorrespondenceRevision as Revision
    rows = Revision.objects.filter(vehicle_model=vm, market=market, start_year__lte=year,
                                   end_year__gte=year, successor__isnull=True).select_related("generation")
    keys = {(i["source_id"], i["source_namespace"], i["identity_type"], i["native_identifier"]) for i in identities}
    return [r for r in rows if (r.source_id, r.source_namespace, r.identity_type, r.native_identifier) in keys]


def resolve_generation(vm, year, market, generation_evidence, documents, fields=None):
    """Read-only resolution. Failure of explicit evidence never uses year fallback."""
    # Validate absence as well as presence before looking up any canonical parent.
    validate_generation_evidence(generation_evidence, documents)
    return _resolve_generation(vm, year, market, generation_evidence, documents, fields)


def _legacy_unique_year_resolution(vm, year, market, fields=None):
    """Original v1 compatibility only; never a claim of verified v2 evidence absence."""
    return _resolve_generation(vm, year, market, [], [], fields)


def _resolve_generation(vm, year, market, generation_evidence, documents, fields=None):
    from reference.models import Generation
    fields = fields or {}
    require(vm.is_active and vm.manufacturer.is_active, "Inactive parent.")
    matches = list(Generation.objects.filter(vehicle_model=vm, is_active=True, start_year__lte=year))
    matches = [g for g in matches if g.end_year is None or year <= g.end_year]
    revisions = []
    if generation_evidence:
        revisions = _applicable_revisions(vm, year, market, generation_evidence)
        keys = {(r.source_id, r.source_namespace, r.identity_type, r.native_identifier) for r in revisions}
        require(all((i["source_id"], i["source_namespace"], i["identity_type"], i["native_identifier"]) in keys
                    for i in generation_evidence), "Missing reviewed generation correspondence.")
        for row in revisions:
            require(row.finding == "established", "Unresolved or withdrawn correspondence.")
            require(row.content_hash == digest(row.review_payload()), "Correspondence integrity failure.")
            require(all(fields.get(k) == v for k, v in row.restrictions.items()), "Unresolved/mismatched correspondence restriction.")
            require(all(doc in documents for doc in row.evidence), "Correspondence source revision does not match candidate evidence.")
            require(row.generation in matches, "Inactive, mismatched or out-of-range generation.")
        targets = {r.generation_id for r in revisions}
        require(len(targets) == 1, "Conflicting generation correspondences.")
        target = next(g for g in matches if g.pk in targets)
        basis = "reviewed_source_correspondence"
    else:
        require(len(matches) == 1, "Missing or overlapping generations; reviewed correspondence required.")
        target = matches[0]
        basis = "unique_year_range"
    return {
        "resolution_version": "1.0", "basis": basis, "parents": parent_snapshot(vm, target),
        "model_year": year, "market": market, "fields": fields,
        "generation_evidence": generation_evidence, "documents": documents,
        "target_identity": {},
        "correspondences": sorted([{"uuid": str(r.uuid), "hash": r.content_hash} for r in revisions], key=lambda r: r["uuid"]),
    }


def validate_generation_evidence(identities, documents):
    require(isinstance(identities, list), "Invalid generation evidence.")
    validate_documents(documents)
    from reference.ingestion.normalization.generation import generation_evidence_from_documents

    def qualified_identity(item):
        return (item["source_id"], item["document_hash"], item["assertion_set_id"], item["assertion_id"])

    expected = {qualified_identity(i): i for i in generation_evidence_from_documents(documents)}
    actual = {}
    for item in identities:
        require(isinstance(item, dict) and set(item) == {
            "source_id", "source_namespace", "identity_type", "native_identifier", "document_hash",
            "assertion_set_id", "assertion_id", "normalizer_id", "normalizer_version",
        }, "Invalid generation identity evidence fields.")
        require(all(isinstance(v, str) and bool(v) for v in item.values()), "Empty generation evidence.")
        identity = qualified_identity(item)
        require(identity not in actual, "Duplicate document-qualified generation identity.")
        actual[identity] = item
        docs = [d for d in documents if d["source_id"] == item["source_id"] and
                d["raw_artifact_hash"] == item["document_hash"] and d["assertion_set_id"] == item["assertion_set_id"]]
        require(len(docs) == 1, "Unresolved document-qualified generation identity.")
        assertions = [a for a in docs[0]["assertions"] if a["assertion_id"] == item["assertion_id"]]
        require(len(assertions) == 1 and str(assertions[0]["raw_value"]).strip() == item["native_identifier"],
                "Generation identity contradicts retained assertion.")
        require(assertions[0]["attribute_key"] == item["source_namespace"] and
                item["source_namespace"] in {"generation_designation", "generation_code", "source_model_code", "generation_section"},
                "Unrecognized generation evidence namespace.")
        require(item["identity_type"] == ("model_code" if item["source_namespace"] == "source_model_code" else "generation_designation")
                and item["normalizer_id"] == "explicit_generation_identity" and item["normalizer_version"] == "1.0.0",
                "Unsupported generation normalization semantics.")
    require(actual == expected,
            "Generation evidence projection is incomplete or contradicts retained assertions.")


def revalidate_resolution(plan):
    """Check reviewed premises without constructing a replacement import plan."""
    from reference.models import Generation, VehicleModel
    snapshot = plan.generation_resolution
    if snapshot:
        validate_bound_plan(plan)
    if not snapshot:
        # Legacy plans authorize only the original unique year path, never new correspondence.
        require(not plan.candidate_snapshot and not plan.candidate_hash,
                "Generation-aware authorization cannot fall back to legacy resolution.")
        vm = VehicleModel.objects.get(pk=plan.resolved_vehicle_model_id)
        result = _legacy_unique_year_resolution(vm, plan.target_vehicle_definition_fields["model_year"],
                                               plan.target_vehicle_definition_fields["market"])
        require(result["parents"]["manufacturer_id"] == plan.resolved_manufacturer_id and
                result["parents"]["generation_id"] == plan.resolved_generation_id, "Legacy resolution changed.")
        require(not vm.generationcorrespondencerevision_set.exists(), "Legacy plan lacks correspondence semantics; re-plan.")
        return
    parents = snapshot["parents"]
    require(parents["manufacturer_id"] == plan.resolved_manufacturer_id and
            parents["vehicle_model_id"] == plan.resolved_vehicle_model_id and
            parents["generation_id"] == plan.resolved_generation_id, "Plan parent binding mismatch.")
    require(snapshot["model_year"] == plan.target_vehicle_definition_fields["model_year"] and
            snapshot["market"] == plan.target_vehicle_definition_fields["market"], "Plan scope binding mismatch.")
    if snapshot["documents"]:
        validate_documents(snapshot["documents"], verify_bytes=True)
    vm = VehicleModel.objects.get(pk=parents["vehicle_model_id"], uuid=parents["vehicle_model_uuid"])
    generation = Generation.objects.get(pk=parents["generation_id"], uuid=parents["generation_uuid"])
    require(parent_snapshot(vm, generation) == parents, "Reviewed parent state changed.")
    current = resolve_generation(vm, snapshot["model_year"], snapshot["market"],
                                 snapshot["generation_evidence"], snapshot["documents"], snapshot["fields"])
    if plan.existing_vehicle_definition_id:
        from reference.models import VehicleDefinition
        existing = VehicleDefinition.objects.get(pk=plan.existing_vehicle_definition_id)
        current["target_identity"] = {"uuid": str(existing.uuid), "slug": existing.slug}
    require(current == snapshot, "Generation correspondence/resolution became stale.")


def validate_bound_plan(plan):
    """Validate the authorized candidate/target relation, without re-planning or DB writes."""
    from reference.ingestion.serialization import candidate_config_doc_from_dict
    from reference.ingestion.validation import validate_candidate_configuration
    from reference.ingestion.importing.planner import _format_engine_name
    require(plan.candidate_hash == digest(plan.candidate_snapshot), "Candidate content hash mismatch.")
    candidate = candidate_config_doc_from_dict(plan.candidate_snapshot)
    require(candidate.envelope.schema_version == "2.0.0", "Unsupported execution candidate version.")
    validate_candidate_configuration(candidate)
    require(candidate.candidate_reference == plan.candidate_reference, "Candidate reference binding mismatch.")
    snapshot = plan.generation_resolution
    require(isinstance(snapshot, dict) and set(snapshot) == {
        "resolution_version", "basis", "parents", "model_year", "market", "fields",
        "generation_evidence", "documents", "correspondences", "target_identity",
    }, "Invalid generation resolution contract.")
    require(snapshot["resolution_version"] == "1.0" and snapshot["basis"] in (
        "unique_year_range", "reviewed_source_correspondence"), "Unsupported resolution semantics.")
    parents = snapshot["parents"]
    require(isinstance(parents, dict) and set(parents) == {
        "manufacturer_id", "manufacturer_uuid", "manufacturer_name", "manufacturer_active",
        "vehicle_model_id", "vehicle_model_uuid", "vehicle_model_name", "vehicle_model_active",
        "generation_id", "generation_uuid", "generation_active", "generation_model_id", "start_year", "end_year",
    }, "Invalid parent snapshot contract.")
    require(all(type(parents[k]) is int for k in (
        "manufacturer_id", "vehicle_model_id", "generation_id", "generation_model_id", "start_year")),
        "Parent IDs and years must be strict integers.")
    require(parents["end_year"] is None or type(parents["end_year"]) is int, "Invalid parent end year.")
    require(all(type(parents[k]) is bool for k in (
        "manufacturer_active", "vehicle_model_active", "generation_active")), "Invalid parent activity snapshot.")
    require(snapshot["generation_evidence"] == candidate.generation_evidence and
            snapshot["documents"] == candidate.evidence_documents, "Resolution evidence binding mismatch.")
    require(bool(snapshot["generation_evidence"]) == (snapshot["basis"] == "reviewed_source_correspondence"),
            "Resolution basis contradicts explicit evidence.")
    def value(key):
        values = [i.normalized_concept for i in candidate.normalized_assertions
                  if i.target_attribute_key == key and i.mapping_status == "mapped" and i.normalized_concept is not None]
        require(bool(values), f"Candidate lacks {key} evidence.")
        require(all(v == values[0] for v in values), f"Candidate has conflicting {key} evidence.")
        return values[0]
    fields = plan.target_vehicle_definition_fields
    require(set(fields) == {"model_year", "trim_name", "engine_name", "drivetrain", "market"},
            "Unsupported canonical target fields.")
    require(snapshot["fields"] == {k: fields[k] for k in ("trim_name", "engine_name", "drivetrain")},
            "Resolution restriction fields contradict target.")
    for field, concept in (("model_year", "model_year"), ("trim_name", "trim"),
                           ("drivetrain", "generic_drive_classification"), ("market", "market")):
        require(fields[field] == value(concept), "Target contradicts candidate evidence.")
    labels = [i.normalized_concept for i in candidate.normalized_assertions
              if i.target_attribute_key == "engine_name" and i.mapping_status == "mapped"]
    engine = value("engine_name") if labels else _format_engine_name(value("engine_displacement_liters"), value("engine_cylinders"))
    require(fields["engine_name"] == engine, "Engine target binding mismatch.")
    require(snapshot["parents"]["manufacturer_name"].lower() == str(value("make")).lower() and
            snapshot["parents"]["vehicle_model_name"].lower() == str(value("model")).lower(),
            "Parent identity contradicts candidate.")
    from django.utils.text import slugify
    require(plan.target_slug == slugify("-".join(str(fields[k]) for k in (
        "model_year", "trim_name", "engine_name", "drivetrain", "market") if str(fields[k]).strip())),
        "Target slug binding mismatch.")


def guard_legacy_scope(make, model, start_year=None, end_year=None, candidates=()):
    """Preflight the whole legacy invocation before any mutation. Not batch authorization repair."""
    from reference.models import Generation, GenerationCorrespondenceRevision
    require(not any(c.envelope.schema_version.startswith("2.") or getattr(c, "generation_evidence", [])
                    for c in candidates), "Use the exact single-plan workflow for v2/correspondence candidates.")
    rows = list(Generation.objects.filter(vehicle_model__manufacturer__name__iexact=make,
                                         vehicle_model__name__iexact=model, is_active=True))
    require(not GenerationCorrespondenceRevision.objects.filter(vehicle_model__manufacturer__name__iexact=make,
                                                                vehicle_model__name__iexact=model).exists(),
            "Legacy workflow cannot authorize correspondence scope.")
    for index, a in enumerate(rows):
        for b in rows[index + 1:]:
            low = max(a.start_year, b.start_year, start_year or 1886)
            high = min(a.end_year or 2100, b.end_year or 2100, end_year or 2100)
            require(low > high, "Legacy workflow cannot authorize overlapping generations.")


def guard_legacy_taxonomies(taxonomies, start_year=1886, end_year=2100, existing_generations=()):
    """Check proposed bootstrap ranges too, before any parent is created."""
    ranges = list(existing_generations)
    slugs = {g.slug for g in ranges}
    ranges.extend(g for g in taxonomies if g.slug not in slugs)
    for index, a in enumerate(ranges):
        for b in ranges[index + 1:]:
            low = max(a.start_year, b.start_year, start_year)
            high = min(a.end_year or 2100, b.end_year or 2100, end_year)
            require(low > high, "Legacy bootstrap taxonomy contains overlapping generations.")
