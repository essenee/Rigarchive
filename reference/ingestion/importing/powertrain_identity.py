"""Candidate 2.1 structured evidence and nonpersistent canonical peer assessment."""
import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError

from reference.powertrain import BASE_FIELDS, FIELDS, record_powertrain, validate_powertrain
from reference.ingestion.contracts import TechnicalValue
from reference.ingestion.generation_correspondence import digest, validate_documents


def _supports(raw, key, expected, *, jeep=False):
    """Check a structured claim or explicit source terminology, never code inference.

    A composite configuration assertion can establish multiple attributes. An
    unrelated qualified assertion cannot establish them merely by being retained.
    """
    if isinstance(raw, dict):
        return key in raw and _supports(raw[key], key, expected, jeep=jeep)
    if raw is None or isinstance(raw, bool):
        return False
    if key == "engine_displacement_liters":
        try:
            return Decimal(str(raw)) == Decimal(expected)
        except InvalidOperation:
            values = re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:L\b|liters?\b|litres?\b)", str(raw), re.I)
            return len(values) == 1 and Decimal(values[0]) == Decimal(expected)
    if key == "engine_cylinders":
        if str(raw).isdigit():
            return int(raw) == expected
        values = re.findall(r"\b[VI][- ]?([1-9]\d*)\b", str(raw), re.I)
        return len(values) == 1 and int(values[0]) == expected
    text = re.sub(r"[_-]+", " ", str(raw).lower()).strip()
    if key == "engine_aspiration":
        terms = {"naturally_aspirated": r"\bnaturally aspirated\b", "turbocharged": r"\bturbo(?:charged)?\b",
                 "supercharged": r"\bsupercharged\b", "twincharged": r"\btwincharged\b", "other": r"^other$"}
    elif key == "fuel_type":
        terms = {"gasoline": r"\b(?:gasoline|petrol)\b", "diesel": r"\bdiesel\b"}
    else:
        # Remove compound labels before examining the generic HEV term.
        found = set()
        for token, pattern in (("plug_in_hybrid", r"\b(?:plug in hybrid|phev|4xe)\b"),
                               ("mild_hybrid", r"\b(?:mild hybrid|mhev)\b")):
            if re.search(pattern, text):
                found.add(token)
                text = re.sub(pattern, "", text)
        if jeep and re.search(r"\betorque\b", text):
            found.add("mild_hybrid")
        terms = {"none": r"^(?:none|nonhybrid|non hybrid)$", "hybrid": r"\b(?:hybrid|hev)\b"}
        found.update(token for token, pattern in terms.items() if re.search(pattern, text))
        return found == {expected}
    return {token for token, pattern in terms.items() if re.search(pattern, text)} == {expected}


def project_powertrain(interpretations):
    """Project reviewed normalized evidence; never infer absent classifications."""
    result = {}
    for key in FIELDS:
        values = []
        for item in interpretations:
            if item.target_attribute_key != key or item.mapping_status != "mapped":
                continue
            value = item.normalized_concept
            if isinstance(value, TechnicalValue):
                if key != FIELDS[0] or value.normalized_unit != "L":
                    raise ValidationError("Invalid structured powertrain evidence unit.")
                value = value.normalized_value
            if value is not None:
                values.append(value)
        if values and any(v != values[0] for v in values):
            raise ValidationError(f"Conflicting powertrain evidence: {key}.")
        result[key] = values[0] if values else None
    validate_powertrain(result)
    return result


def candidate_powertrain(candidate, *, complete=False, verify_bytes=False):
    from reference.ingestion.classification_adjudication import SOURCE_ID, validate_classification_candidate
    validate_classification_candidate(candidate)
    values = candidate.canonical_powertrain
    validate_powertrain(values, complete=complete)
    if project_powertrain(candidate.normalized_assertions) != values:
        raise ValidationError("Powertrain projection contradicts normalized evidence.")
    # One qualified assertion can support any number of explicit interpretations.
    refs = {"|".join((doc["source_id"], doc["raw_artifact_hash"], doc["assertion_set_id"], a["assertion_id"])): a
            for doc in candidate.evidence_documents for a in doc["assertions"]}
    # Only the exact approved projection checked above may supply human conclusions.
    # Its structured declaration is deliberately not accepted by the direct-source parser.
    human_refs = {"|".join((doc["source_id"], doc["raw_artifact_hash"], doc["assertion_set_id"], a["assertion_id"]))
                  for doc in candidate.evidence_documents if doc["source_id"] == SOURCE_ID for a in doc["assertions"]}
    for item in candidate.normalized_assertions:
        key = item.target_attribute_key
        if key in FIELDS and item.mapping_status == "mapped" and values[key] is not None:
            assertion = refs.get(item.source_assertion_ref)
            if assertion is None or (item.source_assertion_ref not in human_refs and not _supports(
                    assertion["raw_value"], key, values[key],
                    jeep=candidate.candidate_identity.manufacturer_name.lower() == "jeep")):
                raise ValidationError("Powertrain interpretation is not supported by its qualified source claim.")
    for doc in candidate.evidence_documents:
        scope = doc.get("source_applicability") or {}
        if scope.get("market") not in (None, candidate.candidate_identity.market):
            raise ValidationError("Powertrain source market contradicts candidate applicability.")
    validate_documents(candidate.evidence_documents, verify_bytes=verify_bytes)
    return dict(values)


def nonidentity_variation(candidate, peer, binding):
    """Keep evidenced layout/tuning differences in review, outside the five-tuple."""
    labels = [i.normalized_concept for i in candidate.normalized_assertions
              if i.target_attribute_key == "engine_name" and i.mapping_status == "mapped"]
    proposed = set(re.findall(r"\b([VI])[- ]?[1-9]\d*\b", str(labels[0]) if labels else "", re.I))
    existing = set(re.findall(r"\b([VI])[- ]?[1-9]\d*\b", peer.engine_name, re.I))
    if proposed and existing and proposed != existing:
        raise ValidationError("Cylinder-layout difference requires review outside the five-field identity.")
    from reference.models import ImportExecutionReceipt
    receipt = ImportExecutionReceipt.objects.get(uuid=binding["receipt_uuid"])
    old_docs = receipt.resolution_snapshot_json["generation_resolution"]["documents"]
    for key in ("horsepower", "torque"):
        old = [a["raw_value"] for doc in old_docs for a in doc["assertions"] if a["attribute_key"] == key]
        new = [a["raw_value"] for doc in candidate.evidence_documents for a in doc["assertions"] if a["attribute_key"] == key]
        if old and new and {digest(v) for v in old} != {digest(v) for v in new}:
            raise ValidationError("Sourced output alternatives require tuning/applicability review under JL-D20.")


def target_values(record):
    return {key: getattr(record, key) for key in BASE_FIELDS} | record_powertrain(record)


def assess_peer(record):
    """Use a verified creation receipt; partial legacy evidence never proves identity."""
    from reference.models import ImportExecutionReceipt
    receipts = list(ImportExecutionReceipt.objects.filter(
        operation_type="vehicle_definition_import", execution_outcome="created",
        created_vehicle_definition=record,
    )[:2])
    if len(receipts) != 1:
        raise ValidationError("Canonical peer lacks a unique successful creation receipt.")
    receipt = receipts[0]
    fields = target_values(record)
    recorded = receipt.target_fields_json
    if (receipt.created_vehicle_definition_pk_snapshot != record.pk
            or receipt.created_vehicle_definition_uuid_snapshot != str(record.uuid)
            or receipt.created_vehicle_definition_slug_snapshot != record.slug
            or receipt.resolved_generation_id != record.generation_id
            or set(recorded) not in (set(BASE_FIELDS), set(BASE_FIELDS + FIELDS))
            or any(recorded[k] != fields[k] for k in BASE_FIELDS)):
        raise ValidationError("Canonical peer receipt does not bind current identity.")
    resolution = receipt.resolution_snapshot_json.get("generation_resolution", {})
    if (resolution.get("parents", {}).get("generation_id") != record.generation_id
            or resolution.get("model_year") != record.model_year or resolution.get("market") != record.market):
        raise ValidationError("Canonical peer receipt scope changed.")
    documents = resolution.get("documents", [])
    validate_documents(documents, verify_bytes=True)
    from reference.ingestion.classification_adjudication import validate_classification_documents
    validate_classification_documents(documents)
    if not any(doc["source_id"] == receipt.source_id and doc["raw_artifact_hash"] == receipt.raw_artifact_hash
               for doc in documents):
        raise ValidationError("Canonical peer source binding changed.")
    if resolution.get("resolution_version") == "1.1":
        values = {k: recorded.get(k) for k in FIELDS}
        proof = resolution.get("engine_distinction", {})
        if proof.get("version") != "2.0" or proof.get("canonical_powertrain") != values:
            raise ValidationError("Canonical peer structured proof changed.")
        if resolution.get("fields") != recorded:
            raise ValidationError("Canonical peer target projection changed.")
    else:
        # Only explicit retained normalized-value assertions can establish legacy
        # premises. Engine labels, engine codes and absent hybrid words cannot.
        values = {}
        for key in FIELDS:
            claims = [a["raw_value"] for doc in documents for a in doc["assertions"] if a["attribute_key"] == key]
            if not claims or any(v != claims[0] for v in claims):
                raise ValidationError("Legacy peer lacks complete unambiguous structured evidence.")
            values[key] = claims[0]
        scope = resolution.get("fields", {})
        if any(scope.get(k) != fields[k] for k in ("engine_name", "trim_name", "drivetrain")):
            raise ValidationError("Legacy receipt does not describe this canonical configuration.")
    validate_powertrain(values, complete=True)
    if any(fields[k] is not None and fields[k] != values[k] for k in FIELDS):
        raise ValidationError("Canonical peer structured state contradicts retained evidence.")
    state = {"record_pk": record.pk, "record_uuid": str(record.uuid), "record_slug": record.slug,
             "is_active": record.is_active, "canonical_state": fields,
             "receipt_uuid": str(receipt.uuid), "receipt_evidence_digest": digest(receipt.resolution_snapshot_json),
             "document_hashes": [digest(doc) for doc in documents], "canonical_powertrain": values}
    state["projection_digest"] = digest(state)
    return values, state


def identity_proof(candidate, peers):
    values = candidate_powertrain(candidate, complete=True, verify_bytes=True)
    bindings = [assess_peer(peer)[1] for peer in sorted(peers, key=lambda p: p.pk)]
    return {"version": "2.0", "canonical_powertrain": values, "peers": bindings}


def peers_for(plan):
    from reference.models import VehicleDefinition
    f = plan.target_vehicle_definition_fields
    return list(VehicleDefinition.objects.filter(
        generation_id=plan.resolved_generation_id, model_year=f["model_year"], market=f["market"],
        trim_name=f["trim_name"], drivetrain=f["drivetrain"],
    ).order_by("pk"))


def revalidate_identity(plan, candidate):
    peers = peers_for(plan)
    proof = identity_proof(candidate, peers)
    if proof != plan.generation_resolution.get("engine_distinction"):
        raise ValidationError("Structured engine evidence or canonical peer state became stale.")
    equal = [(p, b) for p, b in zip(peers, proof["peers"])
             if b["canonical_powertrain"] == proof["canonical_powertrain"]]
    if plan.planned_action == "create" and (equal or any(not p.is_active for p in peers)):
        raise ValidationError("Create does not establish a distinct active factory configuration.")
    if plan.planned_action == "no_op_exact_match":
        if len(equal) != 1 or not equal[0][0].is_active or equal[0][0].pk != plan.existing_vehicle_definition_id:
            raise ValidationError("Existing identity is duplicate, inactive or no longer equal.")
        nonidentity_variation(candidate, *equal[0])


def plan_structured_identity(candidate, generation, fields, base_slug, manufacturer, model):
    """Versioned planner branch. Semantic assessment precedes locator lookup."""
    from reference.models import VehicleDefinition
    from reference.powertrain import qualified_slug
    from reference.ingestion.importing import (
        CanonicalImportPlan, ImportCreateBasis as Basis, ImportEligibilityStatus as Status,
        ImportPlannedAction as Action, ImportReviewCategory as Category,
    )
    common = dict(candidate_reference=candidate.candidate_reference,
                  resolved_manufacturer_id=manufacturer.pk, resolved_vehicle_model_id=model.pk,
                  resolved_generation_id=generation.pk, target_vehicle_definition_fields=fields)
    try:
        values = candidate_powertrain(candidate, complete=True, verify_bytes=True)
        fields.update(values)
        slug = qualified_slug(base_slug, values, fields["engine_name"])
        common["target_slug"] = slug
        namespace = list(VehicleDefinition.objects.filter(
            generation=generation, model_year=fields["model_year"], market=fields["market"],
        ).order_by("pk"))
        peers = [p for p in namespace if p.trim_name == fields["trim_name"] and p.drivetrain == fields["drivetrain"]]
        proof = identity_proof(candidate, peers)
        common["generation_resolution"] = {"engine_distinction": proof}
        equal = [p for p, binding in zip(peers, proof["peers"]) if binding["canonical_powertrain"] == values]
        if equal:
            if len(equal) != 1 or not equal[0].is_active:
                raise ValidationError("Duplicate or inactive assessed identity requires lifecycle review.")
            existing = equal[0]
            binding = next(p for p in proof["peers"] if p["record_pk"] == existing.pk)
            nonidentity_variation(candidate, existing, binding)
            fields["engine_name"] = existing.engine_name
            return CanonicalImportPlan(**(common | {"target_slug": existing.slug}),
                eligibility_status=Status.ELIGIBLE, planned_action=Action.NO_OP_EXACT_MATCH,
                existing_vehicle_definition_id=existing.pk, reasons=["Complete assessed engine identity already exists."])
        if VehicleDefinition.objects.filter(generation=generation, slug=slug).exists():
            return CanonicalImportPlan(**common, eligibility_status=Status.REQUIRES_REVIEW,
                planned_action=Action.FLAG_REVIEW, review_category=Category.SLUG_CONFLICT,
                reasons=["Structured target slug is occupied across active/historical records."])
        if any(not p.is_active for p in peers):
            raise ValidationError("Historical same-trim engine overlap requires review.")
        active = [p for p in namespace if p.is_active]
        same_trim = [p for p in active if p.trim_name == fields["trim_name"]]
        basis = (Basis.FIRST_REPRESENTATION if not active else Basis.MECHANICAL_DIMENSION if same_trim
                 else Basis.SOURCE_ESTABLISHED_GRADE)
        return CanonicalImportPlan(**common, eligibility_status=Status.ELIGIBLE, planned_action=Action.CREATE,
            create_basis=basis, namespace_snapshot_count=len(active),
            mechanical_basis_existing_id=same_trim[0].pk if same_trim else None,
            reasons=["Qualified five-attribute factory engine identity established."])
    except (ValidationError, OSError, ValueError, KeyError, TypeError) as exc:
        return CanonicalImportPlan(**common, eligibility_status=Status.REQUIRES_REVIEW,
            planned_action=Action.FLAG_REVIEW, review_category=Category.MISSING_EVIDENCE, reasons=[str(exc)])
