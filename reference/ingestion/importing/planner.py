"""
Canonical Import Planner (RA-018 / RA-019).

Provides pure Python read-only planning logic for evaluating candidate configuration
documents against canonical Reference database entities without performing database writes.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from reference.ingestion.contracts import (
    CandidateConfigurationDocument,
    NormalizedInterpretation,
    ReconciliationState,
    SourceAssertionSet,
    TechnicalValue,
)
from reference.ingestion.importing import (
    CanonicalImportPlan,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportPlannedAction,
    ImportReviewCategory,
)
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


def _extract_comparable_value(val: Any) -> Any:
    """Extract comparable python primitives from concept values (including TechnicalValue)."""
    if isinstance(val, TechnicalValue):
        return (val.normalized_value, val.normalized_unit)
    return val


def _extract_mapped_concept_values(
    normalized_assertions: List[NormalizedInterpretation],
    target_key: str,
) -> List[Any]:
    """Extract mapped normalized concept values for a specific target_attribute_key."""
    return [
        interp.normalized_concept
        for interp in normalized_assertions
        if interp.target_attribute_key == target_key
        and interp.mapping_status == "mapped"
        and interp.normalized_concept is not None
    ]


def _format_engine_name(displacement: Any, cylinders: Any) -> Optional[str]:
    """Format standard descriptive engine display string (e.g. '4.0L V6')."""
    displ_val = None
    if isinstance(displacement, TechnicalValue):
        displ_val = displacement.normalized_value
    elif isinstance(displacement, (int, float)):
        displ_val = displacement

    cyls_val = cylinders if isinstance(cylinders, int) else None

    if displ_val is None or cyls_val is None:
        return None

    return f"{displ_val:.1f}L V{cyls_val}"


def _fields_match_exact(vd: VehicleDefinition, target_fields: Dict[str, Any]) -> bool:
    """Verify exact equality across all current VehicleDefinition target fields."""
    return (
        vd.model_year == target_fields.get("model_year")
        and vd.trim_name == target_fields.get("trim_name")
        and vd.engine_name == target_fields.get("engine_name")
        and vd.drivetrain == target_fields.get("drivetrain")
        and vd.market == target_fields.get("market")
    )


def plan_candidate_import(
    candidate: CandidateConfigurationDocument,
) -> CanonicalImportPlan:
    """
    Evaluate a CandidateConfigurationDocument against canonical Reference data.

    Returns a transient CanonicalImportPlan detailing eligibility, parent entity
    resolution, target representation fields, target slug, and planned action.

    MUST execute zero database writes.
    """
    ref_id = candidate.candidate_reference or "unknown_reference"

    # 1. Envelope Schema Check
    if not candidate.envelope or not candidate.envelope.schema_version or not candidate.envelope.schema_version.startswith("1."):
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=["Unsupported candidate schema version. Requires major version 1."],
        )

    # 2. Extract Mapped Normalized Evidence from normalized_assertions
    norm_interps = candidate.normalized_assertions or []

    makes = _extract_mapped_concept_values(norm_interps, "make")
    models = _extract_mapped_concept_values(norm_interps, "model")
    years = _extract_mapped_concept_values(norm_interps, "model_year")
    drives = _extract_mapped_concept_values(norm_interps, "generic_drive_classification")
    displs = _extract_mapped_concept_values(norm_interps, "engine_displacement_liters")
    cyls = _extract_mapped_concept_values(norm_interps, "engine_cylinders")
    trims = _extract_mapped_concept_values(norm_interps, "trim")
    markets = _extract_mapped_concept_values(norm_interps, "market")

    # Check for evidence conflict within single attributes
    for key_name, val_list in [
        ("make", makes),
        ("model", models),
        ("model_year", years),
        ("generic_drive_classification", drives),
        ("engine_displacement_liters", displs),
        ("engine_cylinders", cyls),
        ("trim", trims),
        ("market", markets),
    ]:
        distinct = {_extract_comparable_value(v) for v in val_list}
        if len(distinct) > 1:
            return CanonicalImportPlan(
                candidate_reference=ref_id,
                eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
                planned_action=ImportPlannedAction.FLAG_REVIEW,
                review_category=ImportReviewCategory.EVIDENCE_CONFLICT,
                reasons=[f"Multiple conflicting normalized values present for key '{key_name}': {distinct}"],
            )

    # Core required evidence validation (make, model, model_year, drivetrain, engine, trim, market)
    missing_evidence = []
    if not makes:
        missing_evidence.append("make")
    if not models:
        missing_evidence.append("model")
    if not years or not isinstance(years[0], int):
        missing_evidence.append("model_year")
    if not drives or drives[0] not in ("2WD", "4WD", "AWD"):
        missing_evidence.append("generic_drive_classification")
    if not displs:
        missing_evidence.append("engine_displacement_liters")
    if not cyls or not isinstance(cyls[0], int):
        missing_evidence.append("engine_cylinders")
    if not trims:
        missing_evidence.append("trim")
    if not markets or markets[0] not in ("US", "CA", "OT"):
        missing_evidence.append("market")

    if missing_evidence:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            review_category=ImportReviewCategory.MISSING_EVIDENCE,
            reasons=[f"Candidate lacks complete evidence-backed normalized attributes: missing {missing_evidence}."],
        )

    evidence_make = str(makes[0])
    evidence_model = str(models[0])
    evidence_year = int(years[0])
    evidence_drive = str(drives[0])
    evidence_displ = displs[0]
    evidence_cyls = int(cyls[0])
    evidence_trim = str(trims[0])
    evidence_market = str(markets[0])

    # Context contradiction verification (CandidateIdentity vs Source Evidence)
    reasons: List[str] = []
    cid = candidate.candidate_identity
    if cid.manufacturer_name and cid.manufacturer_name.lower() != evidence_make.lower():
        reasons.append(f"CandidateIdentity manufacturer '{cid.manufacturer_name}' contradicts evidence '{evidence_make}'.")
    if cid.vehicle_model_name and cid.vehicle_model_name.lower() != evidence_model.lower():
        reasons.append(f"CandidateIdentity model '{cid.vehicle_model_name}' contradicts evidence '{evidence_model}'.")
    if cid.model_year is not None and cid.model_year != evidence_year:
        reasons.append(f"CandidateIdentity model_year {cid.model_year} contradicts evidence {evidence_year}.")
    if cid.trim_name and cid.trim_name.strip().lower() != evidence_trim.strip().lower():
        reasons.append(f"CandidateIdentity trim_name '{cid.trim_name}' contradicts evidence '{evidence_trim}'.")
    if cid.market and cid.market.strip().upper() != evidence_market.strip().upper():
        reasons.append(f"CandidateIdentity market '{cid.market}' contradicts evidence '{evidence_market}'.")

    if reasons:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            review_category=ImportReviewCategory.CONTEXT_CONTRADICTION,
            reasons=reasons,
        )

    # 3. Parent Entity Resolution (Manufacturer -> VehicleModel -> Generation)
    try:
        mfr = Manufacturer.objects.get(name__iexact=evidence_make, is_active=True)
    except Manufacturer.DoesNotExist:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=[f"Manufacturer '{evidence_make}' does not exist in canonical database."],
        )
    except Manufacturer.MultipleObjectsReturned:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=[f"Multiple active Manufacturers match '{evidence_make}'."],
        )

    try:
        vm = VehicleModel.objects.get(manufacturer=mfr, name__iexact=evidence_model, is_active=True)
    except VehicleModel.DoesNotExist:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=[f"VehicleModel '{evidence_model}' does not exist under Manufacturer '{mfr.name}'."],
        )
    except VehicleModel.MultipleObjectsReturned:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=[f"Multiple active VehicleModels match '{evidence_model}'."],
        )

    gen_qs = Generation.objects.filter(
        vehicle_model=vm,
        start_year__lte=evidence_year,
        is_active=True,
    )
    gens = [g for g in gen_qs if g.end_year is None or g.end_year >= evidence_year]

    if len(gens) == 0:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.INELIGIBLE,
            planned_action=ImportPlannedAction.REJECT,
            reasons=[f"No active Generation covering model year {evidence_year} for model '{vm.name}'."],
        )
    elif len(gens) > 1:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            review_category=ImportReviewCategory.MULTIPLE_OVERLAPPING_GENERATIONS,
            reasons=[f"Multiple overlapping Generations match model year {evidence_year}."],
        )

    resolved_gen = gens[0]

    engine_label = _format_engine_name(evidence_displ, evidence_cyls)
    if not engine_label:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            review_category=ImportReviewCategory.UNFORMATTED_ENGINE_LABEL,
            reasons=["Unable to format descriptive engine display label from displacement and cylinders."],
        )

    target_fields = {
        "model_year": evidence_year,
        "trim_name": evidence_trim,
        "engine_name": engine_label,
        "drivetrain": evidence_drive,
        "market": evidence_market,
    }

    temp_vd = VehicleDefinition(generation=resolved_gen, **target_fields)
    target_slug = temp_vd.build_slug()

    # 4. Review Flag & Reconciliation Check
    rar = candidate.reconciliation_and_review
    if rar is not None:
        rar_reasons = []
        if rar.requires_human_review:
            rar_reasons.append("Candidate configuration document is flagged for human review.")

        for attr_key, attr_state in rar.attribute_states.items():
            if attr_state.reconciliation_state in (
                ReconciliationState.CONFLICTING.value,
                ReconciliationState.AMBIGUOUS.value,
            ):
                rar_reasons.append(
                    f"Attribute '{attr_key}' has conflicting/ambiguous evidence state '{attr_state.reconciliation_state}'."
                )

        if rar_reasons:
            review_cat = ImportReviewCategory.EVIDENCE_CONFLICT
            if rar.attribute_states:
                trim_state = rar.attribute_states.get("trim")
                if trim_state and trim_state.reconciliation_state in (
                    ReconciliationState.AMBIGUOUS.value,
                    ReconciliationState.CONFLICTING.value,
                ):
                    review_cat = ImportReviewCategory.DISTINCT_FACTORY_GRADE

            return CanonicalImportPlan(
                candidate_reference=ref_id,
                eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
                planned_action=ImportPlannedAction.FLAG_REVIEW,
                review_category=review_cat,
                resolved_manufacturer_id=mfr.id,
                resolved_vehicle_model_id=vm.id,
                resolved_generation_id=resolved_gen.id,
                target_vehicle_definition_fields=target_fields,
                target_slug=target_slug,
                reasons=rar_reasons,
            )

    # 5. Canonical Match Classification against DB
    existing_exact = VehicleDefinition.objects.filter(
        generation=resolved_gen,
        slug=target_slug,
    ).first()

    if existing_exact:
        if _fields_match_exact(existing_exact, target_fields):
            return CanonicalImportPlan(
                candidate_reference=ref_id,
                eligibility_status=ImportEligibilityStatus.ELIGIBLE,
                planned_action=ImportPlannedAction.NO_OP_EXACT_MATCH,
                resolved_manufacturer_id=mfr.id,
                resolved_vehicle_model_id=vm.id,
                resolved_generation_id=resolved_gen.id,
                target_vehicle_definition_fields=target_fields,
                target_slug=target_slug,
                existing_vehicle_definition_id=existing_exact.id,
                reasons=["Exact match found in canonical Reference database. Zero writes required."],
            )
        else:
            return CanonicalImportPlan(
                candidate_reference=ref_id,
                eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
                planned_action=ImportPlannedAction.FLAG_REVIEW,
                review_category=ImportReviewCategory.SLUG_CONFLICT,
                resolved_manufacturer_id=mfr.id,
                resolved_vehicle_model_id=vm.id,
                resolved_generation_id=resolved_gen.id,
                target_vehicle_definition_fields=target_fields,
                target_slug=target_slug,
                existing_vehicle_definition_id=existing_exact.id,
                reasons=["Target slug matches an existing record, but current fields conflict."],
            )

    # No exact slug match: inspect existing rows within resolved (generation, model_year, market) namespace
    namespace_rows = list(
        VehicleDefinition.objects.filter(
            generation=resolved_gen,
            model_year=evidence_year,
            market=evidence_market,
        )
    )

    if len(namespace_rows) == 0:
        # First-Representation Create
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.FIRST_REPRESENTATION,
            namespace_snapshot_count=0,
            resolved_manufacturer_id=mfr.id,
            resolved_vehicle_model_id=vm.id,
            resolved_generation_id=resolved_gen.id,
            target_vehicle_definition_fields=target_fields,
            target_slug=target_slug,
            reasons=["First representation in generation/year/market namespace."],
        )

    # Namespace contains existing rows: evaluate trim and drivetrain matching
    same_trim_rows = [row for row in namespace_rows if row.trim_name == evidence_trim]
    if same_trim_rows:
        for row in same_trim_rows:
            if row.drivetrain != evidence_drive:
                # Proven Mechanical Dimensional Difference (Drivetrain)
                return CanonicalImportPlan(
                    candidate_reference=ref_id,
                    eligibility_status=ImportEligibilityStatus.ELIGIBLE,
                    planned_action=ImportPlannedAction.CREATE,
                    create_basis=ImportCreateBasis.MECHANICAL_DIMENSION,
                    namespace_snapshot_count=len(namespace_rows),
                    mechanical_basis_existing_id=row.id,
                    resolved_manufacturer_id=mfr.id,
                    resolved_vehicle_model_id=vm.id,
                    resolved_generation_id=resolved_gen.id,
                    target_vehicle_definition_fields=target_fields,
                    target_slug=target_slug,
                    reasons=["Proven mechanical dimensional difference (drivetrain) with matching trim."],
                )

        # Same trim and same drivetrain already exists in namespace (candidate differs only by engine label string)
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            review_category=ImportReviewCategory.DISTINCT_FACTORY_GRADE,
            resolved_manufacturer_id=mfr.id,
            resolved_vehicle_model_id=vm.id,
            resolved_generation_id=resolved_gen.id,
            target_vehicle_definition_fields=target_fields,
            target_slug=target_slug,
            reasons=["Candidate differs from existing same-trim, same-drivetrain row only by engine display label; requires human review."],
        )

    # No existing row with this trim name exists in namespace: check if distinct factory grade is established by mapped qualified source evidence
    trim_mapped = any(
        i.target_attribute_key == "trim" and i.mapping_status == "mapped" and i.normalized_concept is not None
        for i in norm_interps
    )

    if trim_mapped:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.SOURCE_ESTABLISHED_GRADE,
            namespace_snapshot_count=len(namespace_rows),
            resolved_manufacturer_id=mfr.id,
            resolved_vehicle_model_id=vm.id,
            resolved_generation_id=resolved_gen.id,
            target_vehicle_definition_fields=target_fields,
            target_slug=target_slug,
            reasons=["Qualified source evidence explicitly establishes distinct factory grade configuration."],
        )

    # Candidate differs from existing rows only by unmapped/ambiguous trim string or engine display label
    return CanonicalImportPlan(
        candidate_reference=ref_id,
        eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
        planned_action=ImportPlannedAction.FLAG_REVIEW,
        review_category=ImportReviewCategory.DISTINCT_FACTORY_GRADE,
        resolved_manufacturer_id=mfr.id,
        resolved_vehicle_model_id=vm.id,
        resolved_generation_id=resolved_gen.id,
        target_vehicle_definition_fields=target_fields,
        target_slug=target_slug,
        reasons=["Candidate differs from existing rows only by trim string or engine display label; requires human review."],
    )


def plan_candidate_import_with_adjudications(
    candidate: CandidateConfigurationDocument,
    adjudications: List[Any],
) -> CanonicalImportPlan:
    """
    Adjudication-aware import planning entry point (RA-025 / RA-026).
    Enforces a strict trust boundary: validates adjudication artifact integrity, SHA-256 hash digest,
    category eligibility, and candidate trim binding before promoting a FLAG_REVIEW candidate
    to ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE.
    """
    from reference.ingestion.contracts import CanonicalImportAdjudication
    from reference.ingestion.serialization import adjudication_to_dict, compute_adjudication_hash
    from reference.ingestion.validation import validate_adjudication

    base_plan = plan_candidate_import(candidate)

    if base_plan.planned_action != ImportPlannedAction.FLAG_REVIEW:
        return base_plan

    if not adjudications:
        return base_plan

    # Enforce typed review category eligibility (must be DISTINCT_FACTORY_GRADE)
    if base_plan.review_category != ImportReviewCategory.DISTINCT_FACTORY_GRADE:
        return base_plan

    target_trim = base_plan.target_vehicle_definition_fields.get("trim_name")

    # Extract candidate raw artifact hash set
    cand_raw_hashes = set()
    if hasattr(candidate, "evidence_raw_hashes") and candidate.evidence_raw_hashes:
        cand_raw_hashes = set(candidate.evidence_raw_hashes)
    elif hasattr(candidate, "source_assertion_sets") and getattr(candidate, "source_assertion_sets", None):
        cand_raw_hashes = {
            sas.provenance.extraction_provenance.raw_artifact_hash
            for sas in candidate.source_assertion_sets
            if sas.provenance and sas.provenance.extraction_provenance and sas.provenance.extraction_provenance.raw_artifact_hash
        }
    elif hasattr(candidate, "raw_artifact_hash") and candidate.raw_artifact_hash:
        cand_raw_hashes = {candidate.raw_artifact_hash}

    for adj in adjudications:
        if not isinstance(adj, CanonicalImportAdjudication):
            continue

        # Trust Boundary Step 1: Validate adjudication artifact fields and hash
        try:
            validate_adjudication(adj)
        except Exception:
            continue

        # Trust Boundary Step 2: Typed original review category match
        if adj.original_review_category != base_plan.review_category.value:
            continue

        # Trust Boundary Step 3: Candidate reference & trim name binding
        ref_matches = (adj.candidate_reference == candidate.candidate_reference)
        trim_matches = (adj.adjudicated_trim_name == target_trim)

        if not (ref_matches and trim_matches):
            continue

        # Trust Boundary Step 4: Multi-Artifact Evidence Revision Set Binding
        adj_anchors = adj.evidence_anchors or {}
        adj_raw_hashes = set()
        if "raw_artifact_hashes" in adj_anchors and isinstance(adj_anchors["raw_artifact_hashes"], list):
            adj_raw_hashes = set(adj_anchors["raw_artifact_hashes"])
        elif "raw_artifact_hash" in adj_anchors and adj_anchors["raw_artifact_hash"]:
            adj_raw_hashes = {adj_anchors["raw_artifact_hash"]}
        elif "raw_artifact_hash" in adj.source_identity and adj.source_identity.get("raw_artifact_hash"):
            adj_raw_hashes = {adj.source_identity["raw_artifact_hash"]}

        if cand_raw_hashes and adj_raw_hashes and cand_raw_hashes != adj_raw_hashes:
            continue

        # Trust Boundary Step 5: Verify SHA-256 hash digest
        expected_hash = compute_adjudication_hash(adjudication_to_dict(adj))
        if adj.adjudication_hash != expected_hash:
            continue

        # Trust Boundary Step 6: Approved adjudicable categories for DISTINCT_FACTORY_GRADE
        if adj.adjudication_category not in {"distinct_factory_grade", "special_edition_grade"}:
            continue

        adj_ref_name = f"adjudication_{candidate.candidate_reference}.json"

        return CanonicalImportPlan(
            candidate_reference=base_plan.candidate_reference,
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE,
            review_category=base_plan.review_category,
            namespace_snapshot_count=base_plan.namespace_snapshot_count,
            resolved_manufacturer_id=base_plan.resolved_manufacturer_id,
            resolved_vehicle_model_id=base_plan.resolved_vehicle_model_id,
            resolved_generation_id=base_plan.resolved_generation_id,
            target_vehicle_definition_fields=base_plan.target_vehicle_definition_fields,
            target_slug=base_plan.target_slug,
            existing_vehicle_definition_id=base_plan.existing_vehicle_definition_id,
            reasons=[f"Validated human domain adjudication ({adj.adjudication_category}) proves distinct factory grade."],
            adjudication_reference=adj_ref_name,
            adjudication_hash=adj.adjudication_hash,
        )

    return base_plan
