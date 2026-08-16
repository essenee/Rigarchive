"""
Reference Data Ingestion Intermediate Serialization Contracts (RA-011 / RA-012).

Defines pure Python dataclasses and enumeration types representing Tier 1
SourceAssertionSet payloads and Tier 2 CandidateConfigurationDocument payloads,
including normalized interpretations, 7-dimension drivetrain details, preserved
factory technical features, and separated reconciliation/review states.

No Django ORM models or database persistence are used.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# --- Enum Definitions ---

class ArtifactType(str, Enum):
    SOURCE_ASSERTION_SET = "rigarchive.source_assertion_set.v1"
    CANDIDATE_CONFIGURATION = "rigarchive.candidate_configuration.v1"


class ReconciliationState(str, Enum):
    SINGLE_SOURCE = "single_source"
    CORROBORATED = "corroborated"
    CONFLICTING = "conflicting"
    AMBIGUOUS = "ambiguous"
    INCOMPLETE = "incomplete"


class InventoryCompletenessStatus(str, Enum):
    ESTABLISHED = "established"
    CORROBORATED = "corroborated"
    INCOMPLETE = "incomplete"
    UNVERIFIED = "unverified"


class ReviewDisposition(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    REJECTED_EXCLUDED = "rejected_excluded"


class MissingValueStatus(str, Enum):
    NOT_SUPPLIED_BY_SOURCE = "not_supplied_by_source"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED_CONFLICT = "unresolved_conflict"
    UNKNOWN = "unknown"
    INTENTIONALLY_EXCLUDED = "intentionally_excluded"


class ApplicabilityScope(str, Enum):
    CONFIGURATION = "configuration"
    MODEL_YEAR = "model_year"


# --- Helper Data Classes ---

@dataclass
class Envelope:
    artifact_type: str
    schema_version: str
    created_at: Optional[str] = None
    generator: Optional[str] = None
    schema_uri: Optional[str] = None  # $schema (reserved optional)
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceApplicability:
    market: Optional[str] = None
    applicability_basis: Optional[str] = None
    publisher_jurisdiction: Optional[str] = None
    applicability_scope: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionProvenance:
    raw_artifact_hash: str
    raw_artifact_reference: str
    extractor_id: str
    extractor_version: str
    extraction_mode: str
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceMetadata:
    source_id: str  # RigArchive-local stable source identifier
    source_type: Optional[str] = None
    source_locator: Optional[str] = None
    retrieved_at: Optional[str] = None
    native_record_id: Optional[str] = None
    acquisition_method: Optional[str] = None
    source_use_notes: Optional[str] = None
    review_status: Optional[str] = None
    target_context: Dict[str, Any] = field(default_factory=dict)
    source_applicability: Optional[SourceApplicability] = None
    extraction_provenance: Optional[ExtractionProvenance] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)




@dataclass
class SourceAssertion:
    assertion_id: str
    attribute_key: str
    raw_value: Any
    source_context: Optional[str] = None
    extracted_at: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceAssertionSet:
    envelope: Envelope
    provenance: SourceMetadata
    source_assertions: List[SourceAssertion] = field(default_factory=list)
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedInterpretation:
    interpretation_id: str
    source_assertion_ref: str
    target_attribute_key: str
    normalized_concept: Any
    raw_source_value: Optional[Any] = None
    manufacturer_term: Optional[str] = None
    mapping_status: Optional[str] = "mapped"
    normalization_notes: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateIdentity:
    manufacturer_name: str
    vehicle_model_name: str
    generation_name: Optional[str] = None
    model_year: Optional[int] = None
    market: Optional[str] = "US"
    trim_name: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceConfigurationIdentity:
    source_id: str
    identity_type: str
    native_identifier: str
    source_description: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TechnicalValue:
    normalized_value: Optional[Union[int, float]] = None
    normalized_unit: Optional[str] = None
    raw_source_string: Optional[str] = None
    rpm_normalized: Optional[int] = None
    extra_context: Dict[str, Any] = field(default_factory=dict)
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineDetails:
    code: Optional[str] = None
    cylinders: Optional[int] = None
    displacement: Optional[TechnicalValue] = None
    horsepower: Optional[TechnicalValue] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransmissionDetails:
    code: Optional[str] = None
    type: Optional[str] = None
    speeds: Optional[int] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DrivetrainComponent:
    component_type: str
    name: str
    low_range_ratio: Optional[float] = None
    has_locking_feature: Optional[bool] = None
    extra_properties: Dict[str, Any] = field(default_factory=dict)
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DrivetrainMode:
    mode_code: str
    name: str
    center_coupling: Optional[str] = None
    center_differential_state: Optional[str] = None
    low_range: Optional[bool] = None
    torque_split_default: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DrivetrainDetails:
    generic_classification: Optional[str] = None
    architecture: Optional[str] = None
    components: List[DrivetrainComponent] = field(default_factory=list)
    operating_modes: List[DrivetrainMode] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    manufacturer_terminology: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedTechnicalDetails:
    drivetrain_details: Optional[DrivetrainDetails] = None
    engine: Optional[EngineDetails] = None
    transmission: Optional[TransmissionDetails] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FactoryTechnicalFeature:
    feature_name: str
    source_classification: Optional[str] = None
    normalized_classification_status: Optional[str] = "unresolved"
    source_assertion_ref: Optional[str] = None
    category_status: Optional[str] = "unclassified_feature"
    notes: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PackageOrOption:
    name: str
    source_classification: Optional[str] = None
    normalized_classification_status: Optional[str] = None
    is_distinct_trim_identity: Optional[bool] = False
    availability: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributeReconciliationState:
    reconciliation_state: str
    review_disposition: str
    conflict_details: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationAndReview:
    requires_human_review: bool = False
    review_workflow_disposition: str = ReviewDisposition.NOT_REQUIRED.value
    attribute_states: Dict[str, AttributeReconciliationState] = field(default_factory=dict)
    reconciliation_notes: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticMissingValue:
    status: str
    reason: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateConfigurationDocument:
    envelope: Envelope
    candidate_reference: str  # Transient reference string
    candidate_identity: CandidateIdentity
    source_configuration_identities: List[SourceConfigurationIdentity] = field(default_factory=list)
    normalized_assertions: List[NormalizedInterpretation] = field(default_factory=list)
    normalized_technical_details: Optional[NormalizedTechnicalDetails] = None
    factory_technical_features: List[FactoryTechnicalFeature] = field(default_factory=list)
    packages_and_options: List[PackageOrOption] = field(default_factory=list)
    attribute_provenance: Dict[str, List[str]] = field(default_factory=dict)
    evidence_raw_hashes: List[str] = field(default_factory=list)
    reconciliation_and_review: Optional[ReconciliationAndReview] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalImportAdjudication:
    adjudication_version: str = "1.0"
    created_at: str = ""
    operator_label: str = ""
    original_manifest_hash: str = ""
    candidate_reference: str = ""
    source_identity: Dict[str, Any] = field(default_factory=dict)
    original_review_category: str = ""
    adjudication_category: str = ""  # "distinct_factory_grade" or "special_edition_grade"
    adjudication_decision: str = ""  # "approved_distinct_trim"
    adjudicated_trim_name: str = ""
    adjudication_notes: str = ""
    evidence_anchors: Optional[Dict[str, Any]] = None
    adjudication_hash: Optional[str] = None
    unknown_fields: Dict[str, Any] = field(default_factory=dict)
