"""Pure supplied-data evidence checks for RA-046, never live resolution/approval.

No file reads, ORM, parent lookup, rule widening or human adjudication occurs here.
Unimplemented source/review decoders are dependencies, not presumed approvals.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from reference.candidate_v3 import (
    CandidateV3Document, Diagnostic, evidence_index, path_at, validate_structure,
)
from reference.powertrain import FIELDS, decimal_string
from django.core.exceptions import ValidationError

HEADING = re.compile(r"United States / MY2024 / Jeep Wrangler \((2|4)-door\) / (.+) \[([^\]]+)\]")


@dataclass(frozen=True)
class EvidenceReport:
    diagnostics: tuple

    @property
    def has_evidence_errors(self):
        return any(d.stage == "evidence" for d in self.diagnostics)

    @property
    def dependencies(self):
        return tuple(d for d in self.diagnostics if d.stage == "dependency")


def _heading(raw):
    return HEADING.fullmatch(raw) if type(raw) is str else None


def _literal(raw, target):
    if type(raw) is not dict:
        return raw
    # Source_literal admits a unique named member, never arbitrary recursive search.
    return raw.get(target, _ABSENT)


_ABSENT = object()


def _terms(raw, target, expected, scope):
    from reference.powertrain_evidence import supports
    jeep = bool(scope and scope["manufacturer_key"] == "jeep" and scope["model_key"] == "wrangler")
    if target == "electrification_type" and not jeep and re.search(r"\b4xe\b", str(raw), re.I):
        return False
    return supports(raw, target, expected, jeep=jeep)


def validate_evidence(value, *, retained_artifacts=None):
    """Check what supplied structures permit; dependencies remain explicit.

    retained_artifacts is a caller-supplied map of retained path -> original bytes.
    No paths are opened. Hash-valid bytes alone do not verify an extractor's claims.
    Existing binding, registry and whole-peer resolution are ALWAYS later dependencies.
    """
    c = value.to_dict() if isinstance(value, CandidateV3Document) else value
    validate_structure(c)
    retained_artifacts = {} if retained_artifacts is None else retained_artifacts
    diagnostics = []
    def issue(stage, code, path, message):
        item = Diagnostic(stage, code, path, message)
        if item not in diagnostics: diagnostics.append(item)
    def evidence(code, path, message): issue("evidence", code, path, message)
    def dependency(path, message, code="UNAVAILABLE_ARTIFACT"): issue("dependency", code, path, message)
    refs = evidence_index(c)
    apps = {a["applicability_id"]: a for a in c["applicability"]}
    findings = {f["finding_id"]: f for f in c.get("reviewed_findings", [])}
    interps = {i["interpretation_id"]: i for i in c["normalized_assertions"]}
    def bytes_for(reference, expected, p):
        content = retained_artifacts.get(reference)
        if type(content) is not bytes:
            dependency(p, "Original retained bytes not supplied: " + reference)
            return None
        if "sha256:" + hashlib.sha256(content).hexdigest() != expected:
            dependency(p, "Supplied retained bytes changed: " + reference)
            return None
        return content
    for n, d in enumerate(c["evidence_documents"]):
        bytes_for(d["raw_artifact_reference"], d["raw_artifact_hash"], f"/evidence_documents/{n}/raw_artifact_reference")
    expected_generation = []
    for q, (doc, ast) in refs.items():
        key = ast["attribute_key"]
        if key in {"generation_designation", "generation_code", "source_model_code", "generation_section"}:
            if ast["raw_value"] is None or not str(ast["raw_value"]).strip():
                evidence("PROJECTION_MISMATCH", "/generation_evidence", "Empty source value cannot establish an explicit Generation identity.")
                continue
            expected_generation.append({"source_id": doc["source_id"], "source_namespace": key,
                "identity_type": "model_code" if key == "source_model_code" else "generation_designation",
                "native_identifier": str(ast["raw_value"]).strip(), "document_hash": doc["raw_artifact_hash"],
                "assertion_set_id": doc["assertion_set_id"], "assertion_id": ast["assertion_id"],
                "normalizer_id": "explicit_generation_identity", "normalizer_version": "1.0.0"})
    expected_generation.sort(key=lambda x: (x["source_id"], x["document_hash"], x["assertion_set_id"], x["assertion_id"]))
    if expected_generation != c["generation_evidence"]:
        evidence("PROJECTION_MISMATCH", "/generation_evidence", "Explicit source Generation projection differs or was omitted.")
    ci = c["candidate_identity"]
    for n, a in enumerate(c["applicability"]):
        p = f"/applicability/{n}"
        if (a["scope"] is not None and a["scope"] != c["canonical_scope"]) or (a["market"] is not None and a["market"] != ci["market"]):
            evidence("APPLICABILITY_MISMATCH", p, "Claimed scope/market differs from candidate.")
        if a["start_year"] is None or a["market"] is None or a["scope"] is None:
            dependency(p, "Unestablished applicability coverage is not unlimited coverage.")
        elif ci["model_year"] is not None and not a["start_year"] <= ci["model_year"] <= a["end_year"]:
            evidence("APPLICABILITY_MISMATCH", p, "Candidate year outside claimed coverage.")
        if not set(a["configuration_refs"]) <= set(c["configuration_refs"]):
            evidence("APPLICABILITY_MISMATCH", p, "Applicability grouping is outside root grouping.")
        for q in a["configuration_refs"] + a["source_assertion_refs"]:
            doc, ast = refs[q]
            source_market = (doc.get("source_applicability") or {}).get("market")
            if source_market is not None and a["market"] is not None and source_market != a["market"]:
                evidence("APPLICABILITY_MISMATCH", p, "Source market does not cover claimed grouping.")
            raw = ast["raw_value"]
            if type(raw) is dict:
                if "model_year" in raw and a["start_year"] is not None and not (a["start_year"] == a["end_year"] == raw["model_year"]):
                    evidence("APPLICABILITY_MISMATCH", p, "Claimed range broadens the explicit source year.")
                if "market" in raw and a["market"] is not None and raw["market"] != a["market"]:
                    evidence("APPLICABILITY_MISMATCH", p, "Raw source market differs.")
            if _heading(raw) and (a["market"] != "US" or a["start_year"] != 2024 or a["end_year"] != 2024):
                evidence("APPLICABILITY_MISMATCH", p, "MY2024 US heading cannot establish another year/market.")
    for n, f in enumerate(c.get("reviewed_findings", [])):
        p = f"/reviewed_findings/{n}"
        content = bytes_for(f["artifact_reference"], f["artifact_hash"], p)
        # RA-046 intentionally does not define a new workflow/adjudication approval format.
        # Existing adjudications stay exact-base-bound; unknown review decoders fail closed.
        if content is not None and f["artifact_type"] == "canonical_import_adjudication" and f["artifact_version"] == "1.1":
            try: original = json.loads(content)
            except (ValueError, UnicodeError): original = None
            if type(original) is dict and (original.get("evidence_anchors") or {}).get("candidate_hash") != c["candidate_hash"]:
                evidence("FINDING_SCOPE_MISMATCH", p, "Historical Candidate-bound approval cannot approve this v3 base.")
        dependency(p, "Original review authority/version/constraints need their versioned decoder.", "UNSUPPORTED_REVIEW_VERSION")
    confirmed = {}
    mapped = {}
    grouped = set()
    # Only positive source shapes/rules actually specified by RA-046 can establish
    # supplied grouping. Document/assertion-set/table proximity never enters this set.
    def positive_group(q):
        _, a = refs[q]
        return (a["attribute_key"] == "configuration" and type(a["raw_value"]) is dict
                and any(k in a["raw_value"] for k in ("trim_name", "make", "model_year"))) or bool(_heading(a["raw_value"]))
    for n, i in enumerate(c["normalized_assertions"]):
        p = f"/normalized_assertions/{n}"
        a = apps[i["applicability_ref"]]
        raw = refs[i["source_assertion_ref"]][1]["raw_value"]
        target, proposed, rule = i["target_attribute_key"], i["normalized_concept"], i["normalization"]["id"]
        if "raw_source_value" in i and i["raw_source_value"] != raw:
            evidence("PROJECTION_MISMATCH", p, "Copied raw source value differs from qualified assertion.")
        if i["mapping_status"] == "conflicting": evidence("SOURCE_CONFLICT", p, "Retained conflicting source interpretation.")
        if i["mapping_status"] != "mapped" or proposed is None: continue
        mapped.setdefault((i["applicability_ref"], target), []).append(proposed)
        for finding_id in i["finding_refs"]:
            f = findings[finding_id]
            if f["applicability_ref"] != i["applicability_ref"]:
                evidence("FINDING_SCOPE_MISMATCH", p, "Finding applicability differs from interpretation.")
            if f["artifact_type"] == "generation_correspondence_review" and not target.startswith("canonical_scope."):
                evidence("FINDING_SCOPE_MISMATCH", p, "Generation finding cannot approve body/series/grade/powertrain.")
        same_group = i["source_assertion_ref"] in a["configuration_refs"] and positive_group(i["source_assertion_ref"])
        if same_group:
            grouped.add(i["interpretation_id"])
        else:
            linkage_claim = rule == "existing_body_equivalence" or a["finding_refs"] or i["finding_refs"] or any(
                refs[r][1]["attribute_key"] == "configuration_cross_reference" for r in a["source_assertion_refs"])
            if linkage_claim:
                dependency(p, "Claimed qualified cross-source grouping needs its source/review decoder; no join presumed.")
            else:
                evidence("COEXISTENCE_NOT_ESTABLISHED", p, "No positive same-configuration grouping; shared document/table/set is insufficient.")
        supported = False
        unknown_support = False
        if rule == "source_literal":
            observed = _literal(raw, target)
            supported = observed is not _ABSENT and type(observed) is type(proposed) and observed == proposed
        elif rule == "decimal_liters":
            observed = _literal(raw, target)
            try: supported = type(observed) is str and decimal_string(observed) == proposed
            except ValidationError: supported = False
        elif rule == "powertrain_terminology":
            supported = target in FIELDS and _terms(raw, target, proposed, c["canonical_scope"])
        elif rule == "wrangler_door_taxonomy":
            text_ = raw if type(raw) is str else ""
            kinds = {value for value, pattern in (("two-door", r"(?:\(2-door\)|\b2-Door\b|\btwo-door\b)"),
                                                 ("four-door", r"(?:\(4-door\)|\b4-Door\b|\bfour-door\b)")) if re.search(pattern, text_)}
            scope_ = c["canonical_scope"] or {}
            supported = target == "factory_body.door_configuration" and kinds == {proposed} and scope_.get("manufacturer_key") == "jeep" and scope_.get("model_key") == "wrangler" and scope_.get("generation_key") == "jl"
        elif rule == "wrangler_selector_heading":
            match = _heading(raw)
            observed = {"make": "Jeep", "model": "Wrangler", "model_year": 2024, "market": "US"}
            # Only the two literal approved pairs explicitly given in RA-046 can
            # be checked without the retained broader normalization mapping.
            if match and match[2] in ("Sport", "Unlimited Sport"):
                observed["trim_name"] = "Sport"
            if match and target in observed:
                supported = type(observed[target]) is type(proposed) and observed[target] == proposed
            elif match and target == "trim_name":
                unknown_support = True
                dependency(p, "Retained reviewed MY2024 trim mapping needed; unrestricted prefix stripping forbidden.")
        else:
            unknown_support = True
            if rule == "existing_body_equivalence":
                dependency(p, "Exact existing immutable alias/binding verification requires later resolution.")
            elif not i["finding_refs"]:
                evidence("FINDING_SCOPE_MISMATCH", p, "Reviewed normalization needs an applicable retained finding reference.")
            else:
                dependency(p, "Reviewed normalization requires original finding decoding.", "UNSUPPORTED_REVIEW_VERSION")
        if not supported and not unknown_support:
            evidence("PROJECTION_MISMATCH", p, "Qualified raw value does not support normalized proposal.")
        confirmed[i["interpretation_id"]] = supported and same_group
    for (app, target), values in mapped.items():
        if any(x != values[0] for x in values[1:]):
            evidence("SOURCE_CONFLICT", "/normalized_assertions", "Contradictory known values for the same applicability/configuration: " + target)
    inherited_basis = set()
    projection = {"make": ci["manufacturer_name"], "model": ci["vehicle_model_name"], "model_year": ci["model_year"],
                  "market": ci["market"], "trim_name": ci["trim_name"], "generic_drive_classification": c["drivetrain"]}
    if c.get("canonical_powertrain") is not None: projection.update(c["canonical_powertrain"])
    for kind in ("factory_body", "factory_series"):
        par = c.get(kind)
        if par is None: continue
        pre, sup = par["identity"]["preimage"], par["support"]
        p = "/" + kind
        app = apps[sup["applicability_ref"]]
        expected_scope = c["canonical_scope"]
        if kind == "factory_series" and expected_scope is not None:
            expected_scope = {k: expected_scope[k] for k in ("manufacturer_key", "model_key")}
        if pre["scope"] != expected_scope:
            evidence("APPLICABILITY_MISMATCH", p, "Parent scope differs from candidate.")
        if not set(sup["configuration_refs"]) <= set(app["configuration_refs"]):
            evidence("APPLICABILITY_MISMATCH", p, "Parent support grouping differs from applicability.")
        if kind == "factory_body": expected = {"factory_body." + k: v for k, v in pre["dimensions"].items()}
        else: expected = {"factory_series.namespace": pre["namespace"], "factory_series.designation": pre["designation"], "factory_series.identity_role": "independent_series"}
        projection.update(expected)
        observed = {}
        for ref in sup["interpretation_refs"]:
            i = interps[ref]
            if i["applicability_ref"] != sup["applicability_ref"]:
                evidence("APPLICABILITY_MISMATCH", p + "/support", "Support interpretation has another applicability.")
            if i["mapping_status"] == "mapped" and i["normalized_concept"] is not None:
                observed.setdefault(i["target_attribute_key"], []).append(i["normalized_concept"])
        eq = sup["equivalence_interpretation_ref"]
        if eq is not None:
            i = interps[eq]
            if (i["target_attribute_key"] != "body_identity_equivalence" or i["normalization"]["id"] != "existing_body_equivalence"
                    or i["mapping_status"] != "mapped" or i["normalized_concept"] != par["identity"]["semantic_digest"] or i["applicability_ref"] != sup["applicability_ref"]):
                evidence("PROJECTION_MISMATCH", p + "/support", "Invalid complete-configuration equivalence claim.")
            else:
                inherited_basis.update(target for target in expected if target not in observed)
        for target, value_ in expected.items():
            if target not in observed and eq is None:
                evidence("PROJECTION_MISMATCH", p + "/support", "Populated identity basis lacks qualified support: " + target)
            elif target in observed and any(v != value_ for v in observed[target]):
                evidence("PROJECTION_MISMATCH", p + "/support", "Support differs from frozen identity basis: " + target)
        if par["disposition"] == "existing":
            if par["binding_revision"]["applicability_ref"] != sup["applicability_ref"]:
                evidence("APPLICABILITY_MISMATCH", p + "/binding_revision", "Binding/support applicability references differ.")
            dependency(p + "/binding_revision", "Live immutable parent/binding snapshot is not resolved by the pure contract.")
        else:
            dependency(p, "Pending relationship has no create/reuse disposition; relevant peer/source evidence and exact planning remain later work.")
    for target, proposed in projection.items():
        if proposed is None: continue
        applicable = [i for i in c["normalized_assertions"] if i["target_attribute_key"] == target and i["mapping_status"] == "mapped" and i["normalized_concept"] is not None]
        if (not applicable and target not in inherited_basis) or any(i["normalized_concept"] != proposed for i in applicable):
            evidence("PROJECTION_MISMATCH", "/normalized_assertions", "Canonical projection lacks matching qualified interpretations: " + target)
    # Distinct positive rows are not automatically a single positive configuration.
    # Require a complete supplied grouping, or report the source-linkage dependency.
    # A body's row A plus engine's alternative row B cannot form a Cartesian tuple.
    for app_id, app in [*apps.items(), (None, None)]:
        coverage = {}
        claimed_targets = set()
        for i in c["normalized_assertions"]:
            target = i["target_attribute_key"]
            if ((app_id is None or i["applicability_ref"] == app_id) and i["mapping_status"] == "mapped"
                    and target in projection and projection[target] is not None
                    and i["normalized_concept"] == projection[target]):
                claimed_targets.add(target)
                if i["interpretation_id"] in grouped:
                    coverage.setdefault(i["source_assertion_ref"], set()).add(target)
        if len(coverage) > 1 and not any(claimed_targets <= targets for targets in coverage.values()):
            selected_apps = [app] if app is not None else list(apps.values())
            if inherited_basis or any(a["finding_refs"] or any(refs[r][1]["attribute_key"] == "configuration_cross_reference" for r in a["source_assertion_refs"]) for a in selected_apps):
                dependency("/applicability", "Cross-source/row coexistence needs its source/review decoder; separate rows are not joined.")
            else:
                evidence("COEXISTENCE_NOT_ESTABLISHED", "/configuration_refs", "Individually positive alternative rows do not establish joint coexistence.")
    body_basis = (c.get("factory_body") or {}).get("identity", {}).get("preimage", {}).get("dimensions", {})
    series_pre = (c.get("factory_series") or {}).get("identity", {}).get("preimage", {})
    for i in c["normalized_assertions"]:
        if i["mapping_status"] != "mapped" or i["normalized_concept"] is None: continue
        target = i["target_attribute_key"]
        if target.startswith("factory_body.") and target.split(".", 1)[1] not in body_basis:
            evidence("KNOWN_DISCRIMINATOR_OMITTED", "/factory_body", "Known populated body discriminator was omitted.")
        if target.startswith("factory_series.") and not series_pre:
            evidence("KNOWN_DISCRIMINATOR_OMITTED", "/factory_series", "Known independent series was omitted.")
    for q in c["configuration_refs"]:
        match = _heading(refs[q][1]["raw_value"])
        if match and body_basis.get("door_configuration") != {"2": "two-door", "4": "four-door"}[match[1]]:
            evidence("KNOWN_DISCRIMINATOR_OMITTED", "/factory_body", "Explicit reviewed Wrangler source doors cannot be suppressed by omitting interpretations.")
    for target, declared_refs in c.get("attribute_provenance", {}).items():
        normalized_refs = {i["source_assertion_ref"] for i in c["normalized_assertions"] if i["target_attribute_key"] == target}
        if normalized_refs and set(declared_refs) != normalized_refs:
            evidence("PROJECTION_MISMATCH", path_at("/attribute_provenance", target), "Provenance inventory differs from interpretations.")
    technical = c.get("normalized_technical_details") or {}
    rich_drive = (technical.get("drivetrain_details") or {}).get("generic_classification")
    if rich_drive is not None and c["drivetrain"] is not None and rich_drive != c["drivetrain"]:
        evidence("PROJECTION_MISMATCH", "/normalized_technical_details/drivetrain_details", "Retained drivetrain contradicts canonical drive.")
    engine = technical.get("engine") or {}
    powertrain = c.get("canonical_powertrain") or {}
    if engine.get("cylinders") is not None and powertrain.get("engine_cylinders") is not None and engine["cylinders"] != powertrain["engine_cylinders"]:
        evidence("PROJECTION_MISMATCH", "/normalized_technical_details/engine/cylinders", "Retained cylinder count contradicts canonical powertrain.")
    # Scope keys are proposed, not an already authorized Generation correspondence.
    dependency("/canonical_scope", "Reviewed registry/Generation and full identity resolution are outside the pure contract.")
    return EvidenceReport(tuple(diagnostics))
