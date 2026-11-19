"""RA-049 Wrangler-only read-only family, evidence and live identity resolution."""
from copy import deepcopy
import csv
from dataclasses import asdict
from datetime import timezone
import hashlib
import io
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from reference import candidate_v3 as wire
from reference.body_identity import baseline_preimage, compare_bodies, semantic_digest, canonical_json
from reference.candidate_v3_evidence import validate_evidence, HEADING
from reference.ingestion import body_import_contracts as c
from reference.ingestion.generation_correspondence import resolve_generation, parent_snapshot
from reference.models import FactoryBodyConfiguration, Generation, GenerationCorrespondenceRevision, ImportExecutionReceipt, VehicleDefinition, VehicleModel
from reference.powertrain import FIELDS, record_powertrain

INVENTORY_ROOT = "docs/implementation/handoffs/MY2024_JL/lightweight_ingestion_review_20261113/"
INVENTORIES = {"candidate_inventory.csv": "sha256:3dd67950ed426a9e5c575af68d3b4ce4807f879d95c0eed5f945a309aa03c6fb",
               "trim_normalization_audit.csv": "sha256:50e131316f054efaf760b59b81f70f19481a14268e90ed720427a7df194e4dbb"}
SCOPE = {"manufacturer_key": "jeep", "model_key": "wrangler", "generation_key": "jl"}
ENGINE_LABELS = {"EC1": "2.0L I4 Turbo", "ERC": "3.6L V6 ESS", "ECX": "2.0L I4 Turbo PHEV", "ESG": "6.4L V8 HEMI"}


class ResolutionError(ValidationError):
    def __init__(self, code, message, path="/", stage="resolution"):
        self.diagnostic = {"stage": stage, "code": code, "path": path, "message": message}
        super().__init__(message)


def need(condition, code, message, path="/", stage="resolution"):
    if not condition:
        raise ResolutionError(code, message, path, stage)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def byte_hash(content):
    return "sha256:" + hashlib.sha256(content).hexdigest()


def read_retained(root, reference, expected=None):
    wire.retained_path(reference, "/reference")
    root = Path(root).resolve()
    path = root / reference
    need(not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent), "UNAVAILABLE_ARTIFACT", "Symlink retained paths are unsupported.", stage="dependency")
    path = path.resolve()
    need(path.is_relative_to(root) and path.is_file(), "UNAVAILABLE_ARTIFACT", "Retained artifact unavailable: " + reference, stage="dependency")
    content = path.read_bytes()
    need(expected is None or byte_hash(content) == expected, "ARTIFACT_CHANGED", "Retained bytes changed: " + reference, stage="dependency")
    return content


def body_state(body):
    need(not body.cab_configuration and not body.bed_length_id,
         'UNSUPPORTED_BODY_DIMENSION', 'This historical body contract does not represent pickup cab/bed properties.')
    attrs = {k: getattr(body, k) for k in c.ATTRIBUTES}
    pre = c.tuple_preimage(SCOPE, attrs)
    return c.validate("BodyState", {"pk": body.pk, "uuid": str(body.uuid), "generation_uuid": str(body.generation.uuid), "attributes": attrs,
                                   "updated_at": stamp(body.updated_at), "semantic_preimage": pre, "semantic_digest": semantic_digest(pre)})


def vehicle_state(vehicle):
    powertrain = record_powertrain(vehicle)
    return c.validate("VehicleState", {"pk": vehicle.pk, "uuid": str(vehicle.uuid), "generation_uuid": str(vehicle.generation.uuid), "is_active": vehicle.is_active,
        "slug": vehicle.slug, "fields": {k: getattr(vehicle, k) for k in ("model_year", "trim_name", "engine_name", "drivetrain", "market")} | {"canonical_powertrain": powertrain},
        "body": body_state(vehicle.factory_body_configuration) if vehicle.factory_body_configuration_id else None})


def target_fields(candidate, body):
    ci = candidate["candidate_identity"]
    labels = [i["normalized_concept"] for i in candidate["normalized_assertions"] if i["target_attribute_key"] == "engine_name" and i["mapping_status"] == "mapped"]
    # engine_name is not a v3 identity interpretation Target; use retained engine description.
    details = (candidate.get("normalized_technical_details") or {}).get("engine") or {}
    label = details.get("engine_name") or details.get("description")
    if labels:
        label = labels[0]
    if not label:
        pt = candidate["canonical_powertrain"]
        liters = pt["engine_displacement_liters"]
        liters += ".0" if "." not in liters else ""
        label = f"{liters}L {'I' if pt['engine_cylinders'] == 4 else 'V'}{pt['engine_cylinders']}"
    return {"model_year": 2024, "trim_name": ci["trim_name"], "engine_name": label, "drivetrain": candidate["drivetrain"], "market": "US",
            "canonical_powertrain": deepcopy(candidate["canonical_powertrain"]), "factory_body_configuration_uuid": body["uuid"]}


def structured_base(fields):
    vd = VehicleDefinition(uuid=None, **{k: fields[k] for k in ("model_year", "trim_name", "engine_name", "drivetrain", "market")}, **fields["canonical_powertrain"])
    return vd.build_slug()


def family_slugs(members):
    """Whole-family algorithm; pure and independent of input order or selected rows."""
    groups = {}
    for member in members:
        groups.setdefault(member["legacy_base_slug"], []).append(member)
    result = {}
    for base, group in groups.items():
        doors = {m["body_attributes"]["door_configuration"] for m in group}
        qualify = len(group) > 1 and doors == {"two-door", "four-door"}
        for member in group:
            suffix = {"two-door": "2-door", "four-door": "4-door"}.get(member["body_attributes"]["door_configuration"])
            slug = base + ("-" + suffix if qualify else "")
            need(0 < len(slug) <= 180, "SLUG_TOO_LONG", "Slug must fit 180 characters.")
            need(slug not in result.values(), "SLUG_COLLISION", "Residual complete-family slug collision.")
            result[member["candidate_reference"]] = slug
    return result


class Release:
    """Explicit retained candidate locations. Every plan reloads all bytes and live state.

    root is an authorized repository/test-fixture root, not an evidence trust override.
    The independent inventory bytes and profile membership are fixed below.
    """
    def __init__(self, candidate_paths, *, root=None):
        self.root = Path(root or settings.BASE_DIR).resolve()
        self.candidate_paths = tuple(candidate_paths)

    def _inventories(self):
        data, pins = {}, []
        for name, expected in INVENTORIES.items():
            reference = INVENTORY_ROOT + name
            content = read_retained(self.root, reference, expected)
            data[name] = {r["candidate_id"]: r for r in csv.DictReader(io.StringIO(content.decode("utf-8")))}
            pins.append({"reference": reference, "byte_hash": expected})
        active = {k: v for k, v in data["candidate_inventory.csv"].items() if v["status"] == "ACTIVE_CONSUMER"}
        need(len(active) == 31, "FAMILY_INCOMPLETE", "Reviewed active inventory must contain 31 offerings.")
        return active, data["trim_normalization_audit.csv"], pins

    def _read_candidate(self, reference):
        return wire.parse_candidate(read_retained(self.root, reference).decode("utf-8")).to_dict()

    def _source_claims(self, doc):
        return doc["assertions"]

    def _requires_source_reader(self, doc):
        return True

    def _evidence_projection(self, candidate):
        return candidate

    def _peer_receipt(self, snapshot):
        c.validate("Receipt3", snapshot)
        return snapshot

    def _reviewed_csv_projection(self, doc, raw, candidate, inventory, generation):
        return False  # Historical 3.0.0 reader semantics are unchanged.

    def _evidence(self, candidate, inventory, audit, pins, generation):
        content_map = {}
        for doc in candidate["evidence_documents"]:
            reference, expected = doc["raw_artifact_reference"], doc["raw_artifact_hash"]
            raw = read_retained(self.root, reference, expected)
            content_map[reference] = raw
            pins.append({"reference": reference, "byte_hash": expected})
            if not self._requires_source_reader(doc):
                continue
            if self._reviewed_csv_projection(doc, raw, candidate, inventory, generation):
                continue
            # Verify a source-native JSON assertion projection where available. CSV and
            # reviewed headings are checked separately; arbitrary extracted PDF claims
            # never acquire support merely because their PDF hash exists.
            try:
                native = json.loads(raw, object_pairs_hook=c._pairs,
                    parse_constant=lambda _: c.require(False, "Nonfinite source JSON."))
            except ValidationError as exc:
                raise ResolutionError("INVALID_SOURCE_JSON", str(exc), stage="evidence") from exc
            except (ValueError, UnicodeError):
                native = None
            if type(native) is dict and type(native.get("assertions")) is list:
                ids = [a.get("assertion_id") if type(a) is dict else None for a in native["assertions"]]
                need(all(type(i) is str and bool(i) for i in ids) and len(set(ids)) == len(ids), "INVALID_SOURCE_JSON", "Source assertion IDs must be unique.", stage="evidence")
                native_assertions = {canonical_json(a) for a in native["assertions"]}
                need(all(canonical_json(a) in native_assertions for a in doc["assertions"]), "PROJECTION_MISMATCH", "Retained source assertions differ in value/type.", stage="evidence")
            elif reference == INVENTORY_ROOT + "candidate_inventory.csv":
                for ast in self._source_claims(doc):
                    key, raw_value = ast["attribute_key"], ast["raw_value"]
                    if key == "source_model_code":
                        ok = raw_value == inventory["model_code"]
                    elif key == "source_document_heading":
                        expected_heading = (f"United States / MY2024 / Jeep Wrangler ({inventory['body_style']}) / "
                                            f"{inventory['marketed_trim']} [{inventory['model_code']} / {inventory['quick_order_package']}]")
                        ok = raw_value == expected_heading
                    elif key == "research_offering_correspondence":
                        ok = type(raw_value) is dict and raw_value.get("candidate_id") == candidate["candidate_reference"] and all(
                            k in inventory and type(v) in (str, int) and str(v) == inventory[k] for k, v in raw_value.items())
                    else:
                        raise ResolutionError("UNSUPPORTED_SOURCE_READER", "CSV does not independently establish this extracted claim: " + key, stage="dependency")
                    need(ok, "PROJECTION_MISMATCH", "Retained CSV assertion differs from its exact row.", stage="evidence")
            else:
                raise ResolutionError("UNSUPPORTED_SOURCE_READER", "Source extraction cannot be independently checked by this profile.", stage="dependency")
        # Declared canonical body fields on the selected positive source row cannot
        # be omitted merely by withholding their interpretations from the candidate.
        basis = candidate["factory_body"]["identity"]["preimage"]["dimensions"]
        for qref in candidate["configuration_refs"]:
            _, assertion = wire.evidence_index(candidate)[qref]
            raw_value = assertion["raw_value"]
            if assertion["attribute_key"] == "configuration" and type(raw_value) is dict:
                for dimension in c.ATTRIBUTES:
                    key = "factory_body." + dimension
                    value = raw_value.get(key)
                    populated = value is not None and not (type(value) is str and not value.strip())
                    if dimension != "body_code_namespace" and populated:
                        need(dimension in basis, "KNOWN_DISCRIMINATOR_OMITTED", "Declared body discriminator omitted: " + dimension, stage="evidence")
                        need(canonical_json(basis[dimension]) == canonical_json(raw_value[key]), "PROJECTION_MISMATCH", "Declared body discriminator differs: " + dimension, stage="evidence")
        reviewed, resolved_findings, resolved_interpretations = self._generation_findings(candidate, generation, content_map, pins)
        report = validate_evidence(self._evidence_projection(candidate), retained_artifacts=content_map)
        for d in report.diagnostics:
            if d.stage == "dependency" and (d.path in resolved_findings or d.path in resolved_interpretations):
                continue  # Exact original Generation-only reader independently resolved these dependencies.
            if d.stage == "dependency" and d.path in ("/canonical_scope", "/factory_body"):
                continue  # Discharged below by reviewed Generation and exact parent resolution.
            if d.stage == "dependency" and d.message.startswith("Retained reviewed MY2024 trim mapping needed"):
                for i in candidate["normalized_assertions"]:
                    if i["target_attribute_key"] == "trim_name" and i["normalization"]["id"] == "wrangler_selector_heading":
                        _, ast = wire.evidence_index(candidate)[i["source_assertion_ref"]]
                        heading = HEADING.fullmatch(ast["raw_value"])
                        need(heading and heading[2] == inventory["marketed_trim"] and i["normalized_concept"] == audit["owner_required_canonical_trim"], "PROJECTION_MISMATCH", "Reviewed trim heading mapping differs.", stage="evidence")
                continue
            raise ResolutionError(d.code, d.message, d.path, d.stage)
        # Direct source assertions must actually occur in the retained source projection.
        # Provisional CSV powertrain proposals are intentionally never an approval source.
        return reviewed

    def _generation_findings(self, candidate, generation, content_map, pins):
        reviewed, resolved, interpretations = [], set(), set()
        apps = {a["applicability_id"]: a for a in candidate["applicability"]}
        available = {r["revision_uuid"]: r["review_payload"] for r in generation["correspondences"]}
        valid = {}
        for n, finding in enumerate(candidate.get("reviewed_findings", [])):
            ref = finding["artifact_reference"]
            raw = read_retained(self.root, ref, finding["artifact_hash"])
            content_map[ref] = raw
            pins.append({"reference": ref, "byte_hash": finding["artifact_hash"]})
            if (finding["artifact_type"], finding["artifact_version"]) != ("generation_correspondence_review", "1.0"):
                continue  # Pure evidence checker preserves unknown/legacy exact-base diagnostics.
            payload = c.parse("CorrespondenceReview", raw)
            need(available.get(payload["revision_uuid"]) == payload, "FINDING_SCOPE_MISMATCH", "Original finding is not an applied current published correspondence.", stage="evidence")
            app = apps[finding["applicability_ref"]]
            need(app["scope"] == generation["scope"]["canonical_scope"] and app["market"] == payload["market"] and app["start_year"] is not None and payload["start_year"] <= app["start_year"] <= app["end_year"] <= payload["end_year"], "FINDING_SCOPE_MISMATCH", "Original finding does not cover exact applicability.", stage="evidence")
            locator = finding["locator"]
            if locator["kind"] == "json_pointer":
                value = payload
                try:
                    for key in locator["pointer"].split("/")[1:]:
                        key = key.replace("~1", "/").replace("~0", "~")
                        if type(value) is list:
                            need(bool(key) and key.isascii() and key.isdecimal() and (key == "0" or not key.startswith("0")), "FINDING_SCOPE_MISMATCH", "JSON pointer array index is not canonical.", stage="evidence")
                            value = value[int(key)]
                        else:
                            value = value[key]
                except (KeyError, IndexError, ValueError, TypeError) as exc:
                    raise ResolutionError("FINDING_SCOPE_MISMATCH", "Original finding locator does not resolve.", stage="evidence") from exc
            else:
                need(locator["end_line"] <= len(raw.decode("utf-8").splitlines()), "FINDING_SCOPE_MISMATCH", "Original review line locator outside artifact.", stage="evidence")
            artifact = {"reference": ref, "byte_hash": finding["artifact_hash"], "reader": "generation-correspondence", "reader_version": "1.0", "snapshot": payload}
            reviewed.append(c.validate("ReviewedArtifact", artifact))
            valid[finding["finding_id"]] = (finding, payload)
            resolved.add(f"/reviewed_findings/{n}")
        for n, item in enumerate(candidate["normalized_assertions"]):
            target = item["target_attribute_key"]
            if not target.startswith("canonical_scope.") or item["normalization"]["id"] != "reviewed_alias" or not item["finding_refs"]:
                continue
            if not all(ref in valid for ref in item["finding_refs"]):
                continue  # Preserve the pure reader's original unsupported/exact-base diagnostic.
            scope_key = target.split(".", 1)[1]
            need(item["mapping_status"] == "mapped" and item["normalized_concept"] == generation["scope"]["canonical_scope"][scope_key], "FINDING_SCOPE_MISMATCH", "Reviewed Scope projection differs.", stage="evidence")
            for ref in item["finding_refs"]:
                finding, payload = valid[ref]
                refs = {"|".join((d["source_id"], d["raw_artifact_hash"], d["assertion_set_id"], a["assertion_id"])) for d in payload["evidence"] for a in d["assertions"] if a["attribute_key"] == payload["source_namespace"] and str(a["raw_value"]).strip() == payload["native_identifier"]}
                need(finding["applicability_ref"] == item["applicability_ref"] and item["source_assertion_ref"] in refs, "FINDING_SCOPE_MISMATCH", "Scope finding lacks exact qualified source selector.", stage="evidence")
            interpretations.add(f"/normalized_assertions/{n}")
        return reviewed, resolved, interpretations

    def _resolve(self, candidate, row, audit):
        ci = candidate["candidate_identity"]
        need(candidate["canonical_scope"] == SCOPE and ci["manufacturer_name"] == "Jeep" and ci["vehicle_model_name"] == "Wrangler" and ci["model_year"] == 2024 and ci["market"] == "US" and candidate["drivetrain"] == "4WD", "UNSUPPORTED_PROFILE", "Only reviewed MY2024 US Wrangler JL is executable.")
        need(candidate.get("factory_series") is None, "UNSUPPORTED_SERIES", "Series is unsupported.")
        need(candidate.get("factory_body") and candidate["factory_body"]["disposition"] == "pending", "UNSUPPORTED_BODY_MODE", "Only PendingBody reuse is supported.")
        c.validate("Powertrain", candidate.get("canonical_powertrain"))
        review = candidate.get("reconciliation_and_review") or {}
        need(not review.get("requires_human_review") or review.get("review_workflow_disposition") == "resolved", "UNRESOLVED_REVIEW", "Candidate retains an unresolved required human review.", stage="dependency")
        material = set(FIELDS) | {"trim_name", "generic_drive_classification", "generation", "canonical_scope"} | {"factory_body." + k for k in candidate["factory_body"]["identity"]["preimage"]["dimensions"]}
        for key, state in review.get("attribute_states", {}).items():
            if key in material:
                need(state["reconciliation_state"] in ("single_source", "corroborated") and state["review_disposition"] in ("not_required", "resolved"), "UNRESOLVED_REVIEW", "Material classification remains incomplete/conflicting/unreviewed: " + key, stage="dependency")
        need(ci["trim_name"] == audit["owner_required_canonical_trim"], "FAMILY_MAPPING_MISMATCH", "Canonical trim differs from reviewed inventory.")
        pre = candidate["factory_body"]["identity"]["preimage"]
        need(pre["dimensions"].get("door_configuration") == {"2-door": "two-door", "4-door": "four-door"}[row["body_style"]], "FAMILY_MAPPING_MISMATCH", "Reviewed doors differ.")
        pt = candidate["canonical_powertrain"]
        from decimal import Decimal
        need(Decimal(pt[FIELDS[0]]) == Decimal(row["engine_displacement_liters"]) and pt[FIELDS[1]] == int(row["engine_cylinders"]), "FAMILY_MAPPING_MISMATCH", "Engine inventory join differs.")
        model = VehicleModel.objects.select_related("manufacturer").get(name="Wrangler", manufacturer__name="Jeep")
        need(bool(candidate["generation_evidence"]), "GENERATION_UNRESOLVED", "Explicit reviewed correspondence required.")
        need(any(g["native_identifier"] == row["model_code"] and g["identity_type"] == "model_code" for g in candidate["generation_evidence"]), "FAMILY_MAPPING_MISMATCH", "Reviewed model-code join differs.")
        primary_doc, _ = wire.evidence_index(candidate)[candidate["configuration_refs"][0]]
        need(any(g["source_id"] == primary_doc["source_id"] and g["document_hash"] == primary_doc["raw_artifact_hash"] and g["assertion_set_id"] == primary_doc["assertion_set_id"] for g in candidate["generation_evidence"]), "ATTRIBUTION_UNRESOLVED", "Primary qualified grouping lacks its source identity.")
        fields = {"trim_name": ci["trim_name"], "drivetrain": "4WD", "engine_name": ENGINE_LABELS[row["engine_code"]]}
        resolved = resolve_generation(model, 2024, "US", candidate["generation_evidence"], candidate["evidence_documents"], fields)
        generation = Generation.objects.get(pk=resolved["parents"]["generation_id"])
        need(generation.name == "JL", "GENERATION_MISMATCH", "Correspondence did not resolve JL.")
        revisions = []
        for item in resolved["correspondences"]:
            revision = GenerationCorrespondenceRevision.objects.get(uuid=item["uuid"])
            need(revision.content_hash == item["hash"], "GENERATION_DRIFT", "Correspondence content changed.")
            revisions.append({"revision_uuid": str(revision.uuid), "review_payload": revision.review_payload(), "content_hash": revision.content_hash,
                              "successor_uuid": str(revision.successor.uuid) if hasattr(revision, "successor") else None})
        scope = {"manufacturer": {"pk": model.manufacturer.pk, "uuid": str(model.manufacturer.uuid)}, "vehicle_model": {"pk": model.pk, "uuid": str(model.uuid)},
                 "generation": {"pk": generation.pk, "uuid": str(generation.uuid)}, "canonical_scope": SCOPE, "model_year": 2024, "market": "US"}
        gs = c.validate("GenerationState", {"scope": scope, "parent_state": parent_snapshot(model, generation), "correspondences": sorted(revisions, key=lambda r: r["revision_uuid"])})
        namespace = sorted([body_state(b) for b in FactoryBodyConfiguration.objects.filter(generation=generation).select_related("generation")], key=lambda b: b["uuid"])
        exact = [b for b in namespace if b["semantic_preimage"] == pre]
        compatible = [b for b in namespace if compare_bodies(pre, b["semantic_preimage"]).relation == "compatible"]
        need(not compatible, "BODY_AMBIGUOUS", "Compatible sparse body namespace does not establish equality/distinctness.")
        need(len(exact) == 1, "BODY_PARENT_UNAVAILABLE", "Exactly one supported existing body parent is required.")
        return gs, exact[0], namespace

    def load(self):
        active, audit, pins = self._inventories()
        need(len(self.candidate_paths) == len(set(self.candidate_paths)) == 31, "FAMILY_INCOMPLETE", "All 31 distinct retained candidate locations are required.")
        candidates, contexts, members, reviewed = {}, {}, [], []
        for reference in self.candidate_paths:
            raw = read_retained(self.root, reference)
            candidate = self._read_candidate(reference)
            key = candidate["candidate_reference"]
            need(key in active and key not in candidates, "FAMILY_INCOMPLETE", "Unknown, duplicate or quarantined release member.")
            pins.append({"reference": reference, "byte_hash": byte_hash(raw)})
            # Parent resolution precedes source dependency acceptance; neither grants eligibility.
            generation, body, namespace = self._resolve(candidate, active[key], audit[key])
            reviewed.extend(self._evidence(candidate, active[key], audit[key], pins, generation))
            for revision in generation["correspondences"]:
                for doc in revision["review_payload"]["evidence"]:
                    read_retained(self.root, doc["raw_artifact_reference"], doc["raw_artifact_hash"])
                    pins.append({"reference": doc["raw_artifact_reference"], "byte_hash": doc["raw_artifact_hash"]})
            fields = target_fields(candidate, body)
            # Retained engine display labels are not the identity key. Preserve the
            # reviewed model-year descriptors instead of synthesizing new trim words.
            code = active[key]["engine_code"]
            if code in ENGINE_LABELS:
                fields["engine_name"] = ENGINE_LABELS[code]
            pre = baseline_preimage(scope=SCOPE, model_year=2024, trim_name=fields["trim_name"], drivetrain="4WD", market="US", canonical_powertrain=candidate["canonical_powertrain"], body_digest=body["semantic_digest"])
            member = {"candidate_reference": key, "candidate_hash": candidate["candidate_hash"], "baseline_preimage": pre, "baseline_digest": semantic_digest(pre),
                      "body_attributes": body["attributes"], "target_fields": fields, "legacy_base_slug": structured_base(fields)}
            candidates[key] = candidate
            contexts[key] = (generation, body, namespace)
            members.append(member)
        need(set(candidates) == set(active), "FAMILY_INCOMPLETE", "Reviewed family membership differs.")
        need(len({c.digest(context[0]["scope"]) for context in contexts.values()}) == 1,
             "GENERATION_MISMATCH", "The complete reviewed family must resolve one exact Generation/parent chain.")
        evidence = {"artifact_pins": sorted({(p["reference"], p["byte_hash"]): p for p in pins}.values(), key=lambda p: (p["reference"], p["byte_hash"])), "reviewed_artifacts": sorted({a["reference"]: a for a in reviewed}.values(), key=lambda a: a["reference"])}
        family = c.validate("FamilyState", {"profile": c.PROFILE, "release_members": sorted(members, key=lambda m: m["candidate_reference"]), "release_evidence": evidence})
        family_slugs(family["release_members"])
        return candidates, contexts, family

    def plan(self, reference):
        try:
            candidates, contexts, family = self.load()
            need(reference in candidates, "UNKNOWN_CANDIDATE", "Candidate outside reviewed family.")
            return plan_resolved(candidates[reference], *contexts[reference], family, self)
        except (ValidationError, OSError, ValueError, KeyError, VehicleModel.DoesNotExist, Generation.DoesNotExist) as exc:
            diagnostic = getattr(exc, "diagnostic", {"stage": "dependency", "code": "UNRESOLVED_DEPENDENCY", "path": "/", "message": str(exc)})
            if not isinstance(diagnostic, dict):
                diagnostic = asdict(diagnostic)
            candidate_hash = None
            for path in self.candidate_paths:
                try:
                    candidate = self._read_candidate(path)
                    if candidate["candidate_reference"] == reference:
                        candidate_hash = candidate["candidate_hash"]
                        break
                except (ValidationError, OSError, ValueError):
                    continue
            return c.validate("Assessment3", {"assessment_version": c.VERSION, "candidate_reference": reference, "candidate_hash": candidate_hash, "diagnostics": [diagnostic]})


def _peer(vehicle, candidate, release):
    state = vehicle_state(vehicle)
    result = {"vehicle": state, "body_basis": None, "powertrain_basis": None, "relation": "unresolved", "receipt_uuid": None, "receipt_snapshot_hash": None, "supporting_candidates": [], "evidence": {"artifact_pins": [], "reviewed_artifacts": []}}
    ci = candidate["candidate_identity"]
    if vehicle.trim_name != ci["trim_name"] or vehicle.drivetrain != candidate["drivetrain"]:
        result["relation"] = "irrelevant"
        return result
    receipts = list(ImportExecutionReceipt.objects.filter(created_vehicle_definition=vehicle, execution_outcome="created", operation_type="vehicle_definition_import")[:2])
    if len(receipts) != 1:
        return result
    receipt = receipts[0]
    result.update(receipt_uuid=str(receipt.uuid), receipt_snapshot_hash=c.digest(receipt.resolution_snapshot_json))
    snapshot = receipt.resolution_snapshot_json.get("body_import")
    if snapshot is not None:
        try:
            snapshot = release._peer_receipt(snapshot)
            need(set(receipt.resolution_snapshot_json) == {"body_import"}, "PEER_RECEIPT_MISMATCH", "Versioned receipt root differs.")
            need(snapshot["outcome"] == "created" and snapshot["plan"]["action"] == "create", "PEER_RECEIPT_MISMATCH", "Creation receipt scalar outcome contradicts its snapshot.")
            need(receipt.manifest_hash == snapshot["manifest"]["manifest_hash"] and receipt.target_fields_json == snapshot["persisted_fields"]
                 and receipt.candidate_reference == snapshot["plan"]["candidate_reference"] and receipt.resolved_generation_id == vehicle.generation_id
                 and receipt.operator_label == snapshot["manifest"]["approval"]["operator"]
                 and receipt.created_vehicle_definition_pk_snapshot == vehicle.pk and receipt.created_vehicle_definition_uuid_snapshot == str(vehicle.uuid)
                 and receipt.created_vehicle_definition_slug_snapshot == vehicle.slug, "PEER_RECEIPT_MISMATCH", "Peer scalar receipt mirrors differ.")
            original = snapshot["plan"]["candidate_snapshot"]
            source_doc, _ = wire.evidence_index(original)[original["configuration_refs"][0]]
            need(receipt.source_id == source_doc["source_id"] and receipt.raw_artifact_hash == source_doc["raw_artifact_hash"] and receipt.raw_artifact_reference == source_doc["raw_artifact_reference"], "PEER_RECEIPT_MISMATCH", "Peer scalar source attribution differs.")
            fields = snapshot["persisted_fields"]
            need(all(getattr(receipt, "target_" + key) == fields[key] for key in ("model_year", "trim_name", "engine_name", "drivetrain", "market"))
                 and receipt.target_slug == snapshot["vehicle"]["slug"] and receipt.planned_action == "create" and receipt.create_basis == "body_aware_identity",
                 "PEER_RECEIPT_MISMATCH", "Peer scalar target mirrors differ.")
            selectors = sorted([g for g in original["generation_evidence"] if g["source_id"] == source_doc["source_id"] and g["document_hash"] == source_doc["raw_artifact_hash"] and g["assertion_set_id"] == source_doc["assertion_set_id"]], key=lambda g: (g["source_id"], g["document_hash"], g["assertion_set_id"], g["assertion_id"]))
            need(bool(selectors) and receipt.source_identity_type == selectors[0]["identity_type"] and receipt.native_identifier == selectors[0]["native_identifier"], "PEER_RECEIPT_MISMATCH", "Peer scalar selector differs.")
            need(snapshot["vehicle"] == {"pk": vehicle.pk, "uuid": str(vehicle.uuid), "slug": vehicle.slug}, "PEER_RECEIPT_MISMATCH", "Peer receipt identity changed.")
            need(all(fields[k] == state["fields"][k] for k in state["fields"] if k != "engine_name"), "PEER_RECEIPT_MISMATCH", "Peer canonical fields changed.")
            if fields["engine_name"] != state["fields"]["engine_name"]:
                # Descriptors are outside baseline/2, but still must express the
                # evidenced displacement/cylinders; no different engine is inferred.
                from reference.powertrain import qualified_slug
                qualified_slug("descriptor", state["fields"]["canonical_powertrain"], state["fields"]["engine_name"])
            body_basis = snapshot["plan"]["body"]["semantic_preimage"]
            need(state["body"] is None or state["body"]["semantic_preimage"] == body_basis, "PEER_BODY_DRIFT", "Peer body state differs from its creation evidence.")
            # Independently verify all original retained support; do not require old
            # live peer sets to remain unchanged just to read a historical receipt.
            for pin in snapshot["plan"]["evidence"]["artifact_pins"]:
                read_retained(release.root, pin["reference"], pin["byte_hash"])
            result.update(body_basis=body_basis, powertrain_basis=original["canonical_powertrain"], supporting_candidates=[original], evidence=snapshot["plan"]["evidence"])
        except (ValidationError, OSError, ValueError, KeyError):
            return result
    else:
        # Engine Proof 2.0 cannot authenticate body annotations or supply the
        # complete versioned receipt snapshot required by this successor proof.
        # Do not promote historical unknown metadata after checking only its raw
        # artifact hash. A missing body-aware legacy reader is a real dependency.
        raise ResolutionError("UNSUPPORTED_REVIEW_VERSION", "Material legacy peer lacks a recognized body-aware original receipt reader; Engine Proof 2.0 alone is insufficient.", stage="dependency")
    # A proven different engine already establishes distinctness; null body alone does not.
    if result["powertrain_basis"] is not None and result["powertrain_basis"] != candidate["canonical_powertrain"]:
        result["relation"] = "distinct"
    elif result["body_basis"] is not None:
        relation = compare_bodies(result["body_basis"], candidate["factory_body"]["identity"]["preimage"]).relation
        result["relation"] = {"equal": "equal", "distinct": "distinct", "compatible": "unresolved", "conflict": "unresolved"}[relation]
    return c.validate("PeerAssessment", result)


def plan_resolved(candidate, generation, body, namespace, family, release):
    member = next(m for m in family["release_members"] if m["candidate_reference"] == candidate["candidate_reference"])
    gen_pk = generation["scope"]["generation"]["pk"]
    all_rows = list(VehicleDefinition.objects.filter(generation_id=gen_pk).select_related("generation", "factory_body_configuration__generation").order_by("uuid"))
    peers = [_peer(v, candidate, release) for v in all_rows if v.model_year == 2024 and v.market == "US"]
    equal = [p for p in peers if p["relation"] == "equal"]
    blocked = any(p["relation"] == "unresolved" for p in peers) or len(equal) > 1 or any(not p["vehicle"]["is_active"] for p in equal)
    action = "blocked" if blocked else "no_op" if equal else "create"
    existing = equal[0]["vehicle"] if action == "no_op" else None
    slugs = family_slugs(family["release_members"])
    fields = deepcopy(member["target_fields"])
    if existing:
        fields = existing["fields"] | {"factory_body_configuration_uuid": existing["body"]["uuid"] if existing["body"] else None}
    target = existing["slug"] if existing else slugs[candidate["candidate_reference"]]
    occupied = [v for v in all_rows if v.slug == target]
    diagnostics = []
    if occupied and not (existing and len(occupied) == 1 and str(occupied[0].uuid) == existing["uuid"]):
        action = "blocked"
        existing = None
        diagnostics.append({"stage": "resolution", "code": "SLUG_OCCUPIED", "path": "/target_slug", "message": "Active/inactive canonical owner occupies target slug."})
    if action == "blocked" and not diagnostics:
        diagnostics.append({"stage": "resolution", "code": "PEER_AMBIGUOUS", "path": "/proof/peers", "message": "Equal inactive/duplicate or unresolved overlapping peer."})
    relevant_slugs = sorted(set(slugs.values()) | {target})
    evidence = family["release_evidence"]
    proof = c.seal({"proof_version": c.VERSION, "profile": c.PROFILE, "candidate_hash": candidate["candidate_hash"], "generation_state_hash": c.digest(generation), "body_state_hash": c.digest(body), "body_namespace": namespace,
        "evidence_state_hash": c.digest(evidence), "baseline_preimage": member["baseline_preimage"], "baseline_digest": member["baseline_digest"], "family": family, "peers": peers,
        "slug_occupancy": [{"slug": slug, "owners": [vehicle_state(v) for v in all_rows if v.slug == slug]} for slug in relevant_slugs],
        "generation_slugs": sorted([{"slug": v.slug, "uuid": str(v.uuid), "is_active": v.is_active} for v in all_rows], key=lambda v: (v["slug"], v["uuid"])),
        "conclusion": action, "existing_vehicle_uuid": existing["uuid"] if existing else None}, "proof_hash")
    plan = c.seal({"plan_version": c.VERSION, "profile": c.PROFILE, "candidate_reference": candidate["candidate_reference"], "candidate_snapshot": candidate,
        "candidate_hash": candidate["candidate_hash"], "generation": generation, "body": body, "body_action": "reuse", "evidence": evidence, "target_fields": fields,
        "target_slug": target, "action": action, "existing_vehicle_uuid": existing["uuid"] if existing else None, "proof": proof, "diagnostics": diagnostics}, "plan_hash")
    return c.validate("Plan3", plan)
