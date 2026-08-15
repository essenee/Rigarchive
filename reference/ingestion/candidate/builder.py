"""
Candidate Configuration Construction & Aggregation Engine (RA-016 / RA-017).

Implements deterministic pure-Python candidate configuration construction and aggregation,
transforming caller-supplied CandidateIdentity workflow context, Tier 1 SourceAssertionSet
artifacts, and Tier 2 NormalizedInterpretation objects into transient, non-canonical
CandidateConfigurationDocument artifacts.

No Django ORM models, database persistence, or canonical entity matching are used.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union



from reference.ingestion.contracts import (
    ArtifactType,
    AttributeReconciliationState,
    CandidateConfigurationDocument,
    CandidateIdentity,
    DrivetrainDetails,
    EngineDetails,
    Envelope,
    FactoryTechnicalFeature,
    NormalizedInterpretation,
    NormalizedTechnicalDetails,
    PackageOrOption,
    ReconciliationAndReview,
    ReconciliationState,
    ReviewDisposition,
    SourceAssertion,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    TechnicalValue,
)
from reference.ingestion.validation import validate_candidate_configuration


class CandidateConstructionError(ValueError):
    """Raised when candidate construction input fails validation or structural routing."""
    pass


# Concept keys that project into CandidateConfigurationDocument destinations
PROJECTED_CONCEPT_KEYS: Set[str] = {
    "make",
    "model",
    "model_year",
    "generic_drive_classification",
    "drivetrain_architecture",
    "engine_displacement_liters",
    "engine_cylinders",
    "nhtsa_make_id",
    "nhtsa_model_id",
}


def _comparable_concept_value(val: Any) -> Any:
    if isinstance(val, TechnicalValue):
        return (val.normalized_value, val.normalized_unit)
    return val


def _resolve_evidence_lineage(

    interp: NormalizedInterpretation,
    source_metadata_map: Dict[str, SourceMetadata],
    assertion_to_source_map: Dict[str, str],
) -> Tuple[str, Optional[str]]:
    """
    Resolve the evidence lineage key (source_id, native_record_id) for a NormalizedInterpretation.
    """
    source_id = assertion_to_source_map.get(interp.source_assertion_ref, "unknown")
    meta = source_metadata_map.get(source_id)
    native_record_id = meta.native_record_id if meta else None
    return (source_id, native_record_id)


def _extract_source_configuration_identities(
    source_assertion_sets: List[SourceAssertionSet],
    normalized_assertions: List[NormalizedInterpretation],
) -> List[SourceConfigurationIdentity]:
    """
    Extract source-native configuration identities (e.g. NHTSA Make ID, NHTSA Model ID, EPA Vehicle ID)
    from source metadata and mapped source-native ID interpretations.
    """
    identities: List[SourceConfigurationIdentity] = []
    seen: Set[Tuple[str, str, str]] = set()

    # 1. Native IDs from SourceMetadata provenance (e.g. EPA vehicle_id)
    for sas in source_assertion_sets:
        meta = sas.provenance
        if meta.source_id and meta.native_record_id:
            identity_type = "record_id"
            if meta.source_id == "epa_fueleconomy":
                identity_type = "vehicle_id"

            key = (meta.source_id, identity_type, str(meta.native_record_id))
            if key not in seen:
                seen.add(key)
                identities.append(
                    SourceConfigurationIdentity(
                        source_id=meta.source_id,
                        identity_type=identity_type,
                        native_identifier=str(meta.native_record_id),
                        source_description=f"{meta.source_id} {identity_type} {meta.native_record_id}",
                    )
                )

    # 2. Native IDs from mapped NormalizedInterpretation objects (e.g. NHTSA make_id, model_id)
    for interp in normalized_assertions:
        if interp.mapping_status == "mapped" and interp.normalized_concept is not None:
            if interp.target_attribute_key in ("nhtsa_make_id", "nhtsa_model_id"):
                identity_type = "make_id" if interp.target_attribute_key == "nhtsa_make_id" else "model_id"
                native_id = str(interp.normalized_concept)
                key = ("nhtsa_vpic", identity_type, native_id)
                if key not in seen:
                    seen.add(key)
                    identities.append(
                        SourceConfigurationIdentity(
                            source_id="nhtsa_vpic",
                            identity_type=identity_type,
                            native_identifier=native_id,
                            source_description=f"NHTSA vPIC {identity_type} {native_id}",
                        )
                    )

    # Sort deterministically
    identities.sort(key=lambda i: (i.source_id, i.identity_type, i.native_identifier))
    return identities


def _project_technical_details(
    mapped_groups: Dict[str, List[Tuple[NormalizedInterpretation, Tuple[str, Optional[str]]]]],
) -> Optional[NormalizedTechnicalDetails]:
    """
    Project mapped normalized interpretations into structured NormalizedTechnicalDetails.
    If evidence conflicts on a scalar field, leave that field None.
    """
    # 1. Drivetrain Details
    generic_drive: Optional[str] = None
    drive_arch: Optional[str] = None

    if "generic_drive_classification" in mapped_groups:
        lineage_values = mapped_groups["generic_drive_classification"]
        distinct_vals = {i.normalized_concept for i, _ in lineage_values if i.normalized_concept is not None}
        if len(distinct_vals) == 1:
            generic_drive = str(next(iter(distinct_vals)))
        elif len(distinct_vals) > 1:
            generic_drive = None  # Scalar field unset under value variance

    if "drivetrain_architecture" in mapped_groups:
        lineage_values = mapped_groups["drivetrain_architecture"]
        distinct_vals = {i.normalized_concept for i, _ in lineage_values if i.normalized_concept is not None}
        if len(distinct_vals) == 1:
            drive_arch = str(next(iter(distinct_vals)))
        elif len(distinct_vals) > 1:
            drive_arch = None  # Scalar field unset under value variance

    drivetrain = None
    if generic_drive is not None or drive_arch is not None:
        drivetrain = DrivetrainDetails(
            generic_classification=generic_drive,
            architecture=drive_arch,
        )

    # 2. Engine Details
    displ: Optional[TechnicalValue] = None
    cyls: Optional[int] = None

    if "engine_displacement_liters" in mapped_groups:
        lineage_values = mapped_groups["engine_displacement_liters"]
        distinct_vals = [i.normalized_concept for i, _ in lineage_values if i.normalized_concept is not None]

        # Compare TechnicalValue instances by normalized_value / raw string
        unique_displs = []
        for d in distinct_vals:
            if isinstance(d, TechnicalValue):
                if not any(u.normalized_value == d.normalized_value for u in unique_displs):
                    unique_displs.append(d)

        if len(unique_displs) == 1:
            displ = unique_displs[0]
        elif len(unique_displs) > 1:
            displ = None  # Scalar field unset under value variance

    if "engine_cylinders" in mapped_groups:
        lineage_values = mapped_groups["engine_cylinders"]
        distinct_vals = {i.normalized_concept for i, _ in lineage_values if i.normalized_concept is not None}
        if len(distinct_vals) == 1:
            val = next(iter(distinct_vals))
            cyls = int(val) if val is not None else None
        elif len(distinct_vals) > 1:
            cyls = None  # Scalar field unset under value variance


    engine = None
    if displ is not None or cyls is not None:
        engine = EngineDetails(
            displacement=displ,
            cylinders=cyls,
        )

    # 3. Transmission Details (Currently unmapped in RA-015, left None)
    transmission = None

    if drivetrain is None and engine is None and transmission is None:
        return None

    return NormalizedTechnicalDetails(
        drivetrain_details=drivetrain,
        engine=engine,
        transmission=transmission,
    )


def construct_candidate_configuration(
    candidate_identity: CandidateIdentity,
    source_assertion_sets: List[SourceAssertionSet],
    normalized_assertions: List[NormalizedInterpretation],
    candidate_reference: Optional[str] = None,
    created_at: Optional[str] = None,
) -> CandidateConfigurationDocument:

    """
    Construct a transient, non-canonical CandidateConfigurationDocument from caller-supplied
    CandidateIdentity context, Tier 1 SourceAssertionSet artifacts, and Tier 2 NormalizedInterpretation objects.

    :param candidate_identity: Caller-supplied workflow context.
    :param source_assertion_sets: List of Tier 1 SourceAssertionSet artifacts.
    :param normalized_assertions: List of Tier 2 NormalizedInterpretation objects.
    :param candidate_reference: Optional transient candidate reference string.
    :return: Validated CandidateConfigurationDocument instance.
    :raises CandidateConstructionError: If input structure or provenance validation fails.
    """
    # 1. Structural Validation of CandidateIdentity Required Fields
    if not candidate_identity.manufacturer_name or not candidate_identity.manufacturer_name.strip():
        raise CandidateConstructionError("CandidateIdentity 'manufacturer_name' is required and cannot be empty.")
    if not candidate_identity.vehicle_model_name or not candidate_identity.vehicle_model_name.strip():
        raise CandidateConstructionError("CandidateIdentity 'vehicle_model_name' is required and cannot be empty.")

    if candidate_identity.model_year is not None:
        year = candidate_identity.model_year
        if year < 1886 or year > 2100:
            raise CandidateConstructionError(f"CandidateIdentity 'model_year' {year} is out of valid range (1886-2100).")

    if not source_assertion_sets:
        raise CandidateConstructionError("At least one SourceAssertionSet is required for candidate construction.")
    if not normalized_assertions:
        raise CandidateConstructionError("At least one NormalizedInterpretation is required for candidate construction.")

    # Deduplicate normalized_assertions by interpretation_id (preserving order)
    seen_interp_ids: Set[str] = set()
    unique_normalized_assertions: List[NormalizedInterpretation] = []
    for interp in normalized_assertions:
        if interp.interpretation_id not in seen_interp_ids:
            seen_interp_ids.add(interp.interpretation_id)
            unique_normalized_assertions.append(interp)
    normalized_assertions = unique_normalized_assertions


    # 2. Build Transitive Provenance Lookup Maps
    source_metadata_map: Dict[str, SourceMetadata] = {}
    assertion_to_source_map: Dict[str, str] = {}
    all_assertion_ids: Set[str] = set()

    for sas in source_assertion_sets:
        if not sas.provenance or not sas.provenance.source_id:
            raise CandidateConstructionError("SourceAssertionSet missing valid SourceMetadata provenance.")
        
        src_id = sas.provenance.source_id
        source_metadata_map[src_id] = sas.provenance

        for ast in sas.source_assertions:
            if not ast.assertion_id:
                raise CandidateConstructionError("SourceAssertion missing required 'assertion_id'.")
            all_assertion_ids.add(ast.assertion_id)
            assertion_to_source_map[ast.assertion_id] = src_id

    # 3. Transitive Provenance Integrity Check: Every interp.source_assertion_ref must exist
    for interp in normalized_assertions:
        if not interp.interpretation_id:
            raise CandidateConstructionError("NormalizedInterpretation missing required 'interpretation_id'.")
        if not interp.source_assertion_ref:
            raise CandidateConstructionError(f"NormalizedInterpretation '{interp.interpretation_id}' missing 'source_assertion_ref'.")
        if interp.source_assertion_ref not in all_assertion_ids:
            raise CandidateConstructionError(
                f"NormalizedInterpretation '{interp.interpretation_id}' references unknown source_assertion_ref '{interp.source_assertion_ref}'."
            )

    # 4. Group Mapped Interpretations with Lineage Tracking
    mapped_groups: Dict[str, List[Tuple[NormalizedInterpretation, Tuple[str, Optional[str]]]]] = {}
    for interp in normalized_assertions:
        if interp.mapping_status == "mapped" and interp.target_attribute_key:
            lineage = _resolve_evidence_lineage(interp, source_metadata_map, assertion_to_source_map)
            mapped_groups.setdefault(interp.target_attribute_key, []).append((interp, lineage))

    # 5. Build Attribute Provenance Map (Category A & Context Concepts ONLY)
    attribute_provenance: Dict[str, List[str]] = {}
    for attr_key, interp_lineage_tuples in mapped_groups.items():
        if attr_key in PROJECTED_CONCEPT_KEYS:
            interp_ids = [interp.interpretation_id for interp, _ in interp_lineage_tuples]
            # Deduplicate while preserving order
            seen_ids: Set[str] = set()
            ordered_ids: List[str] = []
            for i_id in interp_ids:
                if i_id not in seen_ids:
                    seen_ids.add(i_id)
                    ordered_ids.append(i_id)
            ordered_ids.sort()
            attribute_provenance[attr_key] = ordered_ids

    # 6. Project Technical Details
    tech_details = _project_technical_details(mapped_groups)

    # 7. Collect Factory Technical Features (From mapped feature interpretations ONLY)
    factory_features: List[FactoryTechnicalFeature] = []
    # Current RA-015 mappings do not establish mapped features, so factory_features remains []

    # 8. Extract Source Configuration Identities
    source_config_identities = _extract_source_configuration_identities(
        source_assertion_sets, normalized_assertions
    )

    # 9. Evaluate Evidence Reconciliation States (Evidence vs Evidence)
    attribute_states: Dict[str, AttributeReconciliationState] = {}
    for attr_key, interp_lineage_tuples in mapped_groups.items():
        if attr_key not in PROJECTED_CONCEPT_KEYS:
            continue

        distinct_sources = {lineage[0] for _, lineage in interp_lineage_tuples}
        distinct_mapped_vals = {
            _comparable_concept_value(interp.normalized_concept)
            for interp, _ in interp_lineage_tuples
            if interp.normalized_concept is not None
        }

        # Check for unmapped Case A or parsing failure interpretations
        unmapped_interps = [
            interp for interp, _ in interp_lineage_tuples if interp.mapping_status == "unmapped" or interp.normalized_concept is None
        ]

        if unmapped_interps and not distinct_mapped_vals:
            # Case A unmapped or parsing failure
            attribute_states[attr_key] = AttributeReconciliationState(
                reconciliation_state=ReconciliationState.INCOMPLETE.value,
                review_disposition=ReviewDisposition.NOT_REQUIRED.value,
                conflict_details="Mapping deferred or parsing failure for concept",
            )
        elif len(distinct_mapped_vals) > 1 and len(distinct_sources) > 1:
            # True cross-source conflict across independent source authorities
            attribute_states[attr_key] = AttributeReconciliationState(
                reconciliation_state=ReconciliationState.CONFLICTING.value,
                review_disposition=ReviewDisposition.PENDING_REVIEW.value,
                conflict_details=f"Incompatible mapped values across independent source authorities: {distinct_mapped_vals}",
            )
        elif len(distinct_sources) > 1 and len(distinct_mapped_vals) == 1:
            # Corroborated evidence across 2+ independent source authorities
            attribute_states[attr_key] = AttributeReconciliationState(
                reconciliation_state=ReconciliationState.CORROBORATED.value,
                review_disposition=ReviewDisposition.NOT_REQUIRED.value,
            )
        elif len(distinct_mapped_vals) >= 1:
            # Single source authority (same source_id, whether 1 or multiple records)
            attribute_states[attr_key] = AttributeReconciliationState(
                reconciliation_state=ReconciliationState.SINGLE_SOURCE.value,
                review_disposition=ReviewDisposition.NOT_REQUIRED.value,
            )


    # 10. Internal Context Verification (Candidate Identity vs Source Evidence)
    is_context_contradicted = False
    context_notes: List[str] = []

    # Check make
    if "make" in mapped_groups and candidate_identity.manufacturer_name:
        make_interps = mapped_groups["make"]
        for interp, _ in make_interps:
            if interp.normalized_concept and str(interp.normalized_concept).strip().lower() != candidate_identity.manufacturer_name.strip().lower():
                is_context_contradicted = True
                context_notes.append(
                    f"Context contradiction detected: manufacturer_name context '{candidate_identity.manufacturer_name}' vs evidence '{interp.normalized_concept}'"
                )

    # Check model
    if "model" in mapped_groups and candidate_identity.vehicle_model_name:
        model_interps = mapped_groups["model"]
        for interp, _ in model_interps:
            if interp.normalized_concept and str(interp.normalized_concept).strip().lower() != candidate_identity.vehicle_model_name.strip().lower():
                is_context_contradicted = True
                context_notes.append(
                    f"Context contradiction detected: vehicle_model_name context '{candidate_identity.vehicle_model_name}' vs evidence '{interp.normalized_concept}'"
                )

    # Check model_year
    if "model_year" in mapped_groups and candidate_identity.model_year is not None:
        year_interps = mapped_groups["model_year"]
        for interp, _ in year_interps:
            if interp.normalized_concept is not None and int(interp.normalized_concept) != candidate_identity.model_year:
                is_context_contradicted = True
                context_notes.append(
                    f"Context contradiction detected: model_year context {candidate_identity.model_year} vs evidence {interp.normalized_concept}"
                )

    # 11. Top-Level Review Workflow Disposition
    has_evidence_conflict = any(
        s.reconciliation_state in (ReconciliationState.CONFLICTING.value, ReconciliationState.AMBIGUOUS.value)
        for s in attribute_states.values()
    )

    requires_human_review = has_evidence_conflict or is_context_contradicted

    rec_notes_str: Optional[str] = None
    if context_notes:
        rec_notes_str = "; ".join(context_notes)

    rec_and_review = ReconciliationAndReview(
        requires_human_review=requires_human_review,
        review_workflow_disposition=ReviewDisposition.PENDING_REVIEW.value if requires_human_review else ReviewDisposition.NOT_REQUIRED.value,
        attribute_states=attribute_states,
        reconciliation_notes=rec_notes_str,
    )

    # 12. Enforce Deterministic Sorting
    sorted_assertions = sorted(normalized_assertions, key=lambda i: (i.target_attribute_key or "", i.interpretation_id))
    sorted_features = sorted(factory_features, key=lambda f: f.feature_name)
    sorted_attr_provenance = {k: sorted(v) for k, v in sorted(attribute_provenance.items())}

    # Generate transient reference if not provided (non-semantic UUID)
    cand_ref = candidate_reference or f"cand_ref_{uuid.uuid4().hex[:12]}"
    env_created_at = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc = CandidateConfigurationDocument(
        envelope=Envelope(
            artifact_type=ArtifactType.CANDIDATE_CONFIGURATION.value,
            schema_version="1.0.0",
            created_at=env_created_at,
            generator="RigArchive-CandidateConstruction/0.1.0",
        ),

        candidate_reference=cand_ref,
        candidate_identity=candidate_identity,
        source_configuration_identities=source_config_identities,
        normalized_assertions=sorted_assertions,
        normalized_technical_details=tech_details,
        factory_technical_features=sorted_features,
        packages_and_options=[],
        attribute_provenance=sorted_attr_provenance,
        reconciliation_and_review=rec_and_review,
    )

    # Run contract validation
    validate_candidate_configuration(doc)

    return doc
