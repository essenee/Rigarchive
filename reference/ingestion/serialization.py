"""
Deterministic JSON Serialization and Deserialization for Ingestion Artifacts (RA-011 / RA-012).

Provides deterministic round-trip JSON serialization, deserialization, and
unknown-field preservation for Tier 1 SourceAssertionSet and Tier 2 CandidateConfigurationDocument.
"""

import json
from typing import Any, Dict, List, Union

from reference.ingestion.contracts import (
    ArtifactType,
    AttributeReconciliationState,
    CandidateConfigurationDocument,
    CandidateIdentity,
    DrivetrainComponent,
    DrivetrainDetails,
    DrivetrainMode,
    EngineDetails,
    Envelope,
    FactoryTechnicalFeature,
    NormalizedInterpretation,
    NormalizedTechnicalDetails,
    PackageOrOption,
    ReconciliationAndReview,
    SemanticMissingValue,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    TechnicalValue,
    TransmissionDetails,
)



def _sort_dict_keys(d: Any) -> Any:
    """Recursively sort dictionary keys for deterministic serialization."""
    if isinstance(d, dict):
        return {k: _sort_dict_keys(v) for k, v in sorted(d.items())}
    elif isinstance(d, list):
        return [_sort_dict_keys(x) for x in d]
    return d


# --- Dataclass -> Dict Converters ---

def envelope_to_dict(envelope: Envelope) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "artifact_type": envelope.artifact_type,
        "schema_version": envelope.schema_version,
    }
    if envelope.schema_uri is not None:
        res["$schema"] = envelope.schema_uri
    if envelope.created_at is not None:
        res["created_at"] = envelope.created_at
    if envelope.generator is not None:
        res["generator"] = envelope.generator
    res.update(envelope.unknown_fields)
    return res


def source_applicability_to_dict(sa: SourceApplicability) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if sa.market is not None:
        res["market"] = sa.market
    if sa.applicability_basis is not None:
        res["applicability_basis"] = sa.applicability_basis
    if sa.publisher_jurisdiction is not None:
        res["publisher_jurisdiction"] = sa.publisher_jurisdiction
    res.update(sa.unknown_fields)
    return res


def source_metadata_to_dict(prov: SourceMetadata) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "source_id": prov.source_id,
    }
    if prov.source_type is not None:
        res["source_type"] = prov.source_type
    if prov.source_locator is not None:
        res["source_locator"] = prov.source_locator
    if prov.retrieved_at is not None:
        res["retrieved_at"] = prov.retrieved_at
    if prov.native_record_id is not None:
        res["native_record_id"] = prov.native_record_id
    if prov.acquisition_method is not None:
        res["acquisition_method"] = prov.acquisition_method
    if prov.source_use_notes is not None:
        res["source_use_notes"] = prov.source_use_notes
    if prov.review_status is not None:
        res["review_status"] = prov.review_status
    if prov.target_context:
        res["target_context"] = prov.target_context
    if prov.source_applicability is not None:
        res["source_applicability"] = source_applicability_to_dict(prov.source_applicability)
    res.update(prov.unknown_fields)
    return res



def source_assertion_to_dict(ast: SourceAssertion) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "assertion_id": ast.assertion_id,
        "attribute_key": ast.attribute_key,
        "raw_value": ast.raw_value,
    }
    if ast.source_context is not None:
        res["source_context"] = ast.source_context
    if ast.extracted_at is not None:
        res["extracted_at"] = ast.extracted_at
    res.update(ast.unknown_fields)
    return res


def source_assertion_set_to_dict(obj: SourceAssertionSet) -> Dict[str, Any]:
    # Sort source assertions deterministically by assertion_id
    sorted_assertions = sorted(obj.source_assertions, key=lambda a: a.assertion_id)
    res: Dict[str, Any] = {
        "envelope": envelope_to_dict(obj.envelope),
        "provenance": source_metadata_to_dict(obj.provenance),
        "source_assertions": [source_assertion_to_dict(a) for a in sorted_assertions],
    }
    res.update(obj.unknown_fields)
    return res


def normalized_interpretation_to_dict(interp: NormalizedInterpretation) -> Dict[str, Any]:
    concept_val = interp.normalized_concept
    if isinstance(concept_val, TechnicalValue):
        concept_val = technical_value_to_dict(concept_val)

    res: Dict[str, Any] = {
        "interpretation_id": interp.interpretation_id,
        "source_assertion_ref": interp.source_assertion_ref,
        "target_attribute_key": interp.target_attribute_key,
        "normalized_concept": concept_val,
    }

    if interp.raw_source_value is not None:
        res["raw_source_value"] = interp.raw_source_value
    if interp.manufacturer_term is not None:
        res["manufacturer_term"] = interp.manufacturer_term
    if interp.mapping_status is not None:
        res["mapping_status"] = interp.mapping_status
    if interp.normalization_notes is not None:
        res["normalization_notes"] = interp.normalization_notes
    res.update(interp.unknown_fields)
    return res


def candidate_identity_to_dict(ident: CandidateIdentity) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "manufacturer_name": ident.manufacturer_name,
        "vehicle_model_name": ident.vehicle_model_name,
    }
    if ident.generation_name is not None:
        res["generation_name"] = ident.generation_name
    if ident.model_year is not None:
        res["model_year"] = ident.model_year
    if ident.market is not None:
        res["market"] = ident.market
    if ident.trim_name is not None:
        res["trim_name"] = ident.trim_name
    res.update(ident.unknown_fields)
    return res


def source_config_identity_to_dict(sc: SourceConfigurationIdentity) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "source_id": sc.source_id,
        "identity_type": sc.identity_type,
        "native_identifier": sc.native_identifier,
    }
    if sc.source_description is not None:
        res["source_description"] = sc.source_description
    res.update(sc.unknown_fields)
    return res


def technical_value_to_dict(tv: TechnicalValue) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if tv.normalized_value is not None:
        res["normalized_value"] = tv.normalized_value
    if tv.normalized_unit is not None:
        res["normalized_unit"] = tv.normalized_unit
    if tv.raw_source_string is not None:
        res["raw_source_string"] = tv.raw_source_string
    if tv.rpm_normalized is not None:
        res["rpm_normalized"] = tv.rpm_normalized
    res.update(tv.extra_context)
    res.update(tv.unknown_fields)
    return res


def engine_details_to_dict(eng: EngineDetails) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if eng.code is not None:
        res["code"] = eng.code
    if eng.cylinders is not None:
        res["cylinders"] = eng.cylinders
    if eng.displacement is not None:
        res["displacement"] = technical_value_to_dict(eng.displacement)
    if eng.horsepower is not None:
        res["horsepower"] = technical_value_to_dict(eng.horsepower)
    res.update(eng.unknown_fields)
    return res


def transmission_details_to_dict(trans: TransmissionDetails) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if trans.code is not None:
        res["code"] = trans.code
    if trans.type is not None:
        res["type"] = trans.type
    if trans.speeds is not None:
        res["speeds"] = trans.speeds
    res.update(trans.unknown_fields)
    return res


def drivetrain_component_to_dict(comp: DrivetrainComponent) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "component_type": comp.component_type,
        "name": comp.name,
    }
    if comp.low_range_ratio is not None:
        res["low_range_ratio"] = comp.low_range_ratio
    if comp.has_locking_feature is not None:
        res["has_locking_feature"] = comp.has_locking_feature
    res.update(comp.extra_properties)
    res.update(comp.unknown_fields)
    return res


def drivetrain_mode_to_dict(mode: DrivetrainMode) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "mode_code": mode.mode_code,
        "name": mode.name,
    }
    if mode.center_coupling is not None:
        res["center_coupling"] = mode.center_coupling
    if mode.center_differential_state is not None:
        res["center_differential_state"] = mode.center_differential_state
    if mode.low_range is not None:
        res["low_range"] = mode.low_range
    if mode.torque_split_default is not None:
        res["torque_split_default"] = mode.torque_split_default
    res.update(mode.unknown_fields)
    return res


def drivetrain_details_to_dict(dt: DrivetrainDetails) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if dt.generic_classification is not None:
        res["generic_classification"] = dt.generic_classification
    if dt.architecture is not None:
        res["architecture"] = dt.architecture
    if dt.components:
        res["components"] = [drivetrain_component_to_dict(c) for c in dt.components]
    if dt.operating_modes:
        res["operating_modes"] = [drivetrain_mode_to_dict(m) for m in dt.operating_modes]
    if dt.capabilities:
        res["capabilities"] = dt.capabilities
    if dt.manufacturer_terminology is not None:
        res["manufacturer_terminology"] = dt.manufacturer_terminology
    res.update(dt.unknown_fields)
    return res


def normalized_technical_details_to_dict(ntd: NormalizedTechnicalDetails) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    if ntd.drivetrain_details is not None:
        res["drivetrain_details"] = drivetrain_details_to_dict(ntd.drivetrain_details)
    if ntd.engine is not None:
        res["engine"] = engine_details_to_dict(ntd.engine)
    if ntd.transmission is not None:
        res["transmission"] = transmission_details_to_dict(ntd.transmission)
    res.update(ntd.unknown_fields)
    return res


def factory_technical_feature_to_dict(ftf: FactoryTechnicalFeature) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "feature_name": ftf.feature_name,
    }
    if ftf.category_status is not None:
        res["category_status"] = ftf.category_status
    if ftf.source_classification is not None:
        res["source_classification"] = ftf.source_classification
    if ftf.normalized_classification_status is not None:
        res["normalized_classification_status"] = ftf.normalized_classification_status
    if ftf.source_assertion_ref is not None:
        res["source_assertion_ref"] = ftf.source_assertion_ref
    if ftf.notes is not None:
        res["notes"] = ftf.notes
    res.update(ftf.unknown_fields)
    return res


def package_or_option_to_dict(poo: PackageOrOption) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "name": poo.name,
    }
    if poo.source_classification is not None:
        res["source_classification"] = poo.source_classification
    if poo.normalized_classification_status is not None:
        res["normalized_classification_status"] = poo.normalized_classification_status
    if poo.is_distinct_trim_identity is not None:
        res["is_distinct_trim_identity"] = poo.is_distinct_trim_identity
    if poo.availability is not None:
        res["availability"] = poo.availability
    res.update(poo.unknown_fields)
    return res


def attribute_reconcil_state_to_dict(ars: AttributeReconciliationState) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "reconciliation_state": ars.reconciliation_state,
        "review_disposition": ars.review_disposition,
    }
    if ars.conflict_details is not None:
        res["conflict_details"] = ars.conflict_details
    res.update(ars.unknown_fields)
    return res


def reconciliation_and_review_to_dict(rar: ReconciliationAndReview) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "requires_human_review": rar.requires_human_review,
        "review_workflow_disposition": rar.review_workflow_disposition,
    }
    if rar.attribute_states:
        res["attribute_states"] = {
            k: attribute_reconcil_state_to_dict(v) for k, v in rar.attribute_states.items()
        }
    if rar.reconciliation_notes is not None:
        res["reconciliation_notes"] = rar.reconciliation_notes
    res.update(rar.unknown_fields)
    return res


def candidate_config_doc_to_dict(obj: CandidateConfigurationDocument) -> Dict[str, Any]:
    # Sort lists deterministically where appropriate
    sorted_interps = sorted(obj.normalized_assertions, key=lambda x: x.interpretation_id)
    sorted_features = sorted(obj.factory_technical_features, key=lambda x: x.feature_name)
    sorted_packages = sorted(obj.packages_and_options, key=lambda x: x.name)
    sorted_source_ids = sorted(obj.source_configuration_identities, key=lambda x: (x.source_id, x.identity_type))

    res: Dict[str, Any] = {
        "envelope": envelope_to_dict(obj.envelope),
        "candidate_reference": obj.candidate_reference,
        "candidate_identity": candidate_identity_to_dict(obj.candidate_identity),
    }
    if sorted_source_ids:
        res["source_configuration_identities"] = [source_config_identity_to_dict(s) for s in sorted_source_ids]
    if sorted_interps:
        res["normalized_assertions"] = [normalized_interpretation_to_dict(i) for i in sorted_interps]
    if obj.normalized_technical_details is not None:
        res["normalized_technical_details"] = normalized_technical_details_to_dict(obj.normalized_technical_details)
    if sorted_features:
        res["factory_technical_features"] = [factory_technical_feature_to_dict(f) for f in sorted_features]
    if sorted_packages:
        res["packages_and_options"] = [package_or_option_to_dict(p) for p in sorted_packages]
    if obj.attribute_provenance:
        res["attribute_provenance"] = {k: sorted(v) for k, v in obj.attribute_provenance.items()}
    if obj.reconciliation_and_review is not None:
        res["reconciliation_and_review"] = reconciliation_and_review_to_dict(obj.reconciliation_and_review)
    res.update(obj.unknown_fields)
    return res


# --- Dict -> Dataclass Parsers ---

def envelope_from_dict(d: Dict[str, Any]) -> Envelope:
    known_keys = {"artifact_type", "schema_version", "$schema", "created_at", "generator"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return Envelope(
        artifact_type=d.get("artifact_type", ""),
        schema_version=d.get("schema_version", ""),
        schema_uri=d.get("$schema"),
        created_at=d.get("created_at"),
        generator=d.get("generator"),
        unknown_fields=unknown,
    )


def source_applicability_from_dict(d: Dict[str, Any]) -> SourceApplicability:
    known_keys = {"market", "applicability_basis", "publisher_jurisdiction"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return SourceApplicability(
        market=d.get("market"),
        applicability_basis=d.get("applicability_basis"),
        publisher_jurisdiction=d.get("publisher_jurisdiction"),
        unknown_fields=unknown,
    )


def source_metadata_from_dict(d: Dict[str, Any]) -> SourceMetadata:
    known_keys = {
        "source_id", "source_type", "source_locator", "retrieved_at",
        "native_record_id", "acquisition_method", "source_use_notes",
        "review_status", "target_context", "source_applicability"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    sa_dict = d.get("source_applicability")
    sa_obj = source_applicability_from_dict(sa_dict) if isinstance(sa_dict, dict) else None
    return SourceMetadata(
        source_id=d.get("source_id", ""),
        source_type=d.get("source_type"),
        source_locator=d.get("source_locator"),
        retrieved_at=d.get("retrieved_at"),
        native_record_id=d.get("native_record_id"),
        acquisition_method=d.get("acquisition_method"),
        source_use_notes=d.get("source_use_notes"),
        review_status=d.get("review_status"),
        target_context=d.get("target_context", {}),
        source_applicability=sa_obj,
        unknown_fields=unknown,
    )



def source_assertion_from_dict(d: Dict[str, Any]) -> SourceAssertion:
    known_keys = {"assertion_id", "attribute_key", "raw_value", "source_context", "extracted_at"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return SourceAssertion(
        assertion_id=d.get("assertion_id", ""),
        attribute_key=d.get("attribute_key", ""),
        raw_value=d.get("raw_value"),
        source_context=d.get("source_context"),
        extracted_at=d.get("extracted_at"),
        unknown_fields=unknown,
    )


def source_assertion_set_from_dict(d: Dict[str, Any]) -> SourceAssertionSet:
    known_keys = {"envelope", "provenance", "source_assertions"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    env = envelope_from_dict(d.get("envelope", {}))
    prov = source_metadata_from_dict(d.get("provenance", {}))
    assertions = [source_assertion_from_dict(a) for a in d.get("source_assertions", [])]
    return SourceAssertionSet(
        envelope=env,
        provenance=prov,
        source_assertions=assertions,
        unknown_fields=unknown,
    )


def normalized_interpretation_from_dict(d: Dict[str, Any]) -> NormalizedInterpretation:
    known_keys = {
        "interpretation_id", "source_assertion_ref", "target_attribute_key",
        "normalized_concept", "raw_source_value", "manufacturer_term",
        "mapping_status", "normalization_notes"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}

    concept_val = d.get("normalized_concept")
    if isinstance(concept_val, dict) and "normalized_value" in concept_val:
        concept_val = technical_value_from_dict(concept_val)

    return NormalizedInterpretation(
        interpretation_id=d.get("interpretation_id", ""),
        source_assertion_ref=d.get("source_assertion_ref", ""),
        target_attribute_key=d.get("target_attribute_key", ""),
        normalized_concept=concept_val,
        raw_source_value=d.get("raw_source_value"),
        manufacturer_term=d.get("manufacturer_term"),
        mapping_status=d.get("mapping_status", "mapped"),
        normalization_notes=d.get("normalization_notes"),
        unknown_fields=unknown,
    )



def candidate_identity_from_dict(d: Dict[str, Any]) -> CandidateIdentity:
    known_keys = {
        "manufacturer_name", "vehicle_model_name", "generation_name",
        "model_year", "market", "trim_name"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return CandidateIdentity(
        manufacturer_name=d.get("manufacturer_name", ""),
        vehicle_model_name=d.get("vehicle_model_name", ""),
        generation_name=d.get("generation_name"),
        model_year=d.get("model_year"),
        market=d.get("market", "US"),
        trim_name=d.get("trim_name"),
        unknown_fields=unknown,
    )


def source_config_identity_from_dict(d: Dict[str, Any]) -> SourceConfigurationIdentity:
    known_keys = {"source_id", "identity_type", "native_identifier", "source_description"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return SourceConfigurationIdentity(
        source_id=d.get("source_id", ""),
        identity_type=d.get("identity_type", ""),
        native_identifier=d.get("native_identifier", ""),
        source_description=d.get("source_description"),
        unknown_fields=unknown,
    )


def technical_value_from_dict(d: Dict[str, Any]) -> TechnicalValue:
    known_keys = {"normalized_value", "normalized_unit", "raw_source_string", "rpm_normalized"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return TechnicalValue(
        normalized_value=d.get("normalized_value"),
        normalized_unit=d.get("normalized_unit"),
        raw_source_string=d.get("raw_source_string"),
        rpm_normalized=d.get("rpm_normalized"),
        unknown_fields=unknown,
    )


def engine_details_from_dict(d: Dict[str, Any]) -> EngineDetails:
    known_keys = {"code", "cylinders", "displacement", "horsepower"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    disp = technical_value_from_dict(d["displacement"]) if "displacement" in d else None
    hp = technical_value_from_dict(d["horsepower"]) if "horsepower" in d else None
    return EngineDetails(
        code=d.get("code"),
        cylinders=d.get("cylinders"),
        displacement=disp,
        horsepower=hp,
        unknown_fields=unknown,
    )


def transmission_details_from_dict(d: Dict[str, Any]) -> TransmissionDetails:
    known_keys = {"code", "type", "speeds"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return TransmissionDetails(
        code=d.get("code"),
        type=d.get("type"),
        speeds=d.get("speeds"),
        unknown_fields=unknown,
    )


def drivetrain_component_from_dict(d: Dict[str, Any]) -> DrivetrainComponent:
    known_keys = {"component_type", "name", "low_range_ratio", "has_locking_feature"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return DrivetrainComponent(
        component_type=d.get("component_type", ""),
        name=d.get("name", ""),
        low_range_ratio=d.get("low_range_ratio"),
        has_locking_feature=d.get("has_locking_feature"),
        unknown_fields=unknown,
    )


def drivetrain_mode_from_dict(d: Dict[str, Any]) -> DrivetrainMode:
    known_keys = {"mode_code", "name", "center_coupling", "center_differential_state", "low_range", "torque_split_default"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return DrivetrainMode(
        mode_code=d.get("mode_code", ""),
        name=d.get("name", ""),
        center_coupling=d.get("center_coupling"),
        center_differential_state=d.get("center_differential_state"),
        low_range=d.get("low_range"),
        torque_split_default=d.get("torque_split_default"),
        unknown_fields=unknown,
    )


def drivetrain_details_from_dict(d: Dict[str, Any]) -> DrivetrainDetails:
    known_keys = {
        "generic_classification", "architecture", "components",
        "operating_modes", "capabilities", "manufacturer_terminology"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    comps = [drivetrain_component_from_dict(c) for c in d.get("components", [])]
    modes = [drivetrain_mode_from_dict(m) for m in d.get("operating_modes", [])]
    return DrivetrainDetails(
        generic_classification=d.get("generic_classification"),
        architecture=d.get("architecture"),
        components=comps,
        operating_modes=modes,
        capabilities=d.get("capabilities", []),
        manufacturer_terminology=d.get("manufacturer_terminology"),
        unknown_fields=unknown,
    )


def normalized_technical_details_from_dict(d: Dict[str, Any]) -> NormalizedTechnicalDetails:
    known_keys = {"drivetrain_details", "engine", "transmission"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    dt = drivetrain_details_from_dict(d["drivetrain_details"]) if "drivetrain_details" in d else None
    eng = engine_details_from_dict(d["engine"]) if "engine" in d else None
    trans = transmission_details_from_dict(d["transmission"]) if "transmission" in d else None
    return NormalizedTechnicalDetails(
        drivetrain_details=dt,
        engine=eng,
        transmission=trans,
        unknown_fields=unknown,
    )


def factory_technical_feature_from_dict(d: Dict[str, Any]) -> FactoryTechnicalFeature:
    known_keys = {
        "feature_name", "source_classification", "normalized_classification_status",
        "source_assertion_ref", "category_status", "notes"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return FactoryTechnicalFeature(
        feature_name=d.get("feature_name", ""),
        source_classification=d.get("source_classification"),
        normalized_classification_status=d.get("normalized_classification_status", "unresolved"),
        source_assertion_ref=d.get("source_assertion_ref"),
        category_status=d.get("category_status", "unclassified_feature"),
        notes=d.get("notes"),
        unknown_fields=unknown,
    )


def package_or_option_from_dict(d: Dict[str, Any]) -> PackageOrOption:
    known_keys = {
        "name", "source_classification", "normalized_classification_status",
        "is_distinct_trim_identity", "availability"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return PackageOrOption(
        name=d.get("name", ""),
        source_classification=d.get("source_classification"),
        normalized_classification_status=d.get("normalized_classification_status"),
        is_distinct_trim_identity=d.get("is_distinct_trim_identity", False),
        availability=d.get("availability"),
        unknown_fields=unknown,
    )


def attribute_reconcil_state_from_dict(d: Dict[str, Any]) -> AttributeReconciliationState:
    known_keys = {"reconciliation_state", "review_disposition", "conflict_details"}
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    return AttributeReconciliationState(
        reconciliation_state=d.get("reconciliation_state", ""),
        review_disposition=d.get("review_disposition", ""),
        conflict_details=d.get("conflict_details"),
        unknown_fields=unknown,
    )


def reconciliation_and_review_from_dict(d: Dict[str, Any]) -> ReconciliationAndReview:
    known_keys = {
        "requires_human_review", "review_workflow_disposition",
        "attribute_states", "reconciliation_notes"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    states_dict = {}
    if "attribute_states" in d:
        for k, v in d["attribute_states"].items():
            states_dict[k] = attribute_reconcil_state_from_dict(v)
    return ReconciliationAndReview(
        requires_human_review=d.get("requires_human_review", False),
        review_workflow_disposition=d.get("review_workflow_disposition", "not_required"),
        attribute_states=states_dict,
        reconciliation_notes=d.get("reconciliation_notes"),
        unknown_fields=unknown,
    )


def candidate_config_doc_from_dict(d: Dict[str, Any]) -> CandidateConfigurationDocument:
    known_keys = {
        "envelope", "candidate_reference", "candidate_identity",
        "source_configuration_identities", "normalized_assertions",
        "normalized_technical_details", "factory_technical_features",
        "packages_and_options", "attribute_provenance", "reconciliation_and_review"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    env = envelope_from_dict(d.get("envelope", {}))
    cand_ref = d.get("candidate_reference", "")
    ident = candidate_identity_from_dict(d.get("candidate_identity", {}))
    scs = [source_config_identity_from_dict(s) for s in d.get("source_configuration_identities", [])]
    interps = [normalized_interpretation_from_dict(i) for i in d.get("normalized_assertions", [])]
    ntd = normalized_technical_details_from_dict(d["normalized_technical_details"]) if "normalized_technical_details" in d else None
    ftfs = [factory_technical_feature_from_dict(f) for f in d.get("factory_technical_features", [])]
    poos = [package_or_option_from_dict(p) for p in d.get("packages_and_options", [])]
    prov = d.get("attribute_provenance", {})
    rar = reconciliation_and_review_from_dict(d["reconciliation_and_review"]) if "reconciliation_and_review" in d else None

    return CandidateConfigurationDocument(
        envelope=env,
        candidate_reference=cand_ref,
        candidate_identity=ident,
        source_configuration_identities=scs,
        normalized_assertions=interps,
        normalized_technical_details=ntd,
        factory_technical_features=ftfs,
        packages_and_options=poos,
        attribute_provenance=prov,
        reconciliation_and_review=rar,
        unknown_fields=unknown,
    )


# --- Public Entry Points ---

def serialize_artifact(obj: Union[SourceAssertionSet, CandidateConfigurationDocument]) -> str:
    """
    Deterministically serialize an artifact dataclass to a UTF-8 JSON string
    with 2-space indentation and sorted object keys.
    """
    if isinstance(obj, SourceAssertionSet):
        raw_dict = source_assertion_set_to_dict(obj)
    elif isinstance(obj, CandidateConfigurationDocument):
        raw_dict = candidate_config_doc_to_dict(obj)
    else:
        raise TypeError(f"Unsupported artifact type for serialization: {type(obj)}")

    sorted_dict = _sort_dict_keys(raw_dict)
    return json.dumps(sorted_dict, indent=2, ensure_ascii=False)


def deserialize_artifact(json_input: Union[str, Dict[str, Any]]) -> Union[SourceAssertionSet, CandidateConfigurationDocument]:
    """
    Deserialize a JSON string or dict into a SourceAssertionSet or CandidateConfigurationDocument
    dataclass while preserving any unknown/unmodeled fields.
    """
    if isinstance(json_input, str):
        data = json.loads(json_input)
    elif isinstance(json_input, dict):
        data = json_input
    else:
        raise TypeError(f"Input must be JSON string or dict, got {type(json_input)}")

    if not isinstance(data, dict):
        raise ValueError("Root JSON artifact must be an object")

    env_dict = data.get("envelope", {})
    artifact_type = env_dict.get("artifact_type")

    if artifact_type == ArtifactType.SOURCE_ASSERTION_SET.value:
        return source_assertion_set_from_dict(data)
    elif artifact_type == ArtifactType.CANDIDATE_CONFIGURATION.value:
        return candidate_config_doc_from_dict(data)
    else:
        raise ValueError(f"Unknown or missing artifact_type in envelope: {artifact_type}")
