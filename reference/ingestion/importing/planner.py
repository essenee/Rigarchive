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

    # 2. Review Flag & Reconciliation Check
    reasons: List[str] = []
    rar = candidate.reconciliation_and_review
    if rar is not None:
        if rar.requires_human_review:
            reasons.append("Candidate configuration document is flagged for human review.")

        for attr_key, attr_state in rar.attribute_states.items():
            if attr_state.reconciliation_state in (
                ReconciliationState.CONFLICTING.value,
                ReconciliationState.AMBIGUOUS.value,
            ):
                reasons.append(
                    f"Attribute '{attr_key}' has conflicting/ambiguous evidence state '{attr_state.reconciliation_state}'."
                )

    if reasons:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            reasons=reasons,
        )

    # 3. Extract Mapped Normalized Evidence from normalized_assertions
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
    cid = candidate.candidate_identity
    if cid.manufacturer_name and cid.manufacturer_name.lower() != evidence_make.lower():
        reasons.append(f"CandidateIdentity manufacturer '{cid.manufacturer_name}' contradicts evidence '{evidence_make}'.")
    if cid.vehicle_model_name and cid.vehicle_model_name.lower() != evidence_model.lower():
        reasons.append(f"CandidateIdentity model '{cid.vehicle_model_name}' contradicts evidence '{evidence_model}'.")
    if cid.model_year is not None and cid.model_year != evidence_year:
        reasons.append(f"CandidateIdentity model_year {cid.model_year} contradicts evidence {evidence_year}.")

    if reasons:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            reasons=reasons,
        )

    # 4. Parent Entity Resolution (Manufacturer -> VehicleModel -> Generation)
    # A. Manufacturer
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

    # B. VehicleModel
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

    # C. Generation (by model_year range)
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
            reasons=[f"Multiple overlapping Generations match model year {evidence_year}."],
        )

    resolved_gen = gens[0]

    # Format engine display label
    engine_label = _format_engine_name(evidence_displ, evidence_cyls)
    if not engine_label:
        return CanonicalImportPlan(
            candidate_reference=ref_id,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            reasons=["Unable to format descriptive engine display label from displacement and cylinders."],
        )

    # Construct target VehicleDefinition fields dictionary
    target_fields = {
        "model_year": evidence_year,
        "trim_name": evidence_trim,
        "engine_name": engine_label,
        "drivetrain": evidence_drive,
        "market": evidence_market,
    }

    # Compute target slug deterministically via temporary VehicleDefinition instance
    temp_vd = VehicleDefinition(generation=resolved_gen, **target_fields)
    target_slug = temp_vd.build_slug()

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

    # Namespace contains existing rows: evaluate mechanical dimensional distinctness
    for row in namespace_rows:
        if row.trim_name == evidence_trim:
            # Shared evidence-backed trim name: check for mechanical dimensional difference (drivetrain)
            # Free-text engine_name string inequality is NOT used as proof of mechanical distinctness
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


    # Candidate differs from existing rows only by trim string (e.g. SR5 vs SR5 Premium) or engine display label
    return CanonicalImportPlan(
        candidate_reference=ref_id,
        eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
        planned_action=ImportPlannedAction.FLAG_REVIEW,
        resolved_manufacturer_id=mfr.id,
        resolved_vehicle_model_id=vm.id,
        resolved_generation_id=resolved_gen.id,
        target_vehicle_definition_fields=target_fields,
        target_slug=target_slug,
        reasons=["Candidate differs from existing rows only by trim string or engine display label; requires human review."],
    )
