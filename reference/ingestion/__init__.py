"""
Reference Data Ingestion Intermediate Serialization Package (RA-011 / RA-012).

Provides pure Python serialization contracts, deterministic JSON round-trip utilities,
and contract validation for reference ingestion intermediate artifacts.
"""

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
    MissingValueStatus,
    NormalizedInterpretation,
    NormalizedTechnicalDetails,
    PackageOrOption,
    ReconciliationAndReview,
    ReconciliationState,
    ReviewDisposition,
    SemanticMissingValue,
    SourceAssertion,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    TechnicalValue,
    TransmissionDetails,
)
from reference.ingestion.serialization import (
    deserialize_artifact,
    serialize_artifact,
)
from reference.ingestion.validation import (
    IngestionValidationError,
    validate_artifact,
    validate_candidate_configuration,
    validate_envelope,
    validate_semantic_missing_value,
    validate_source_assertion_set,
)

__all__ = [
    # Contracts & Enums
    "ArtifactType",
    "AttributeReconciliationState",
    "CandidateConfigurationDocument",
    "CandidateIdentity",
    "DrivetrainComponent",
    "DrivetrainDetails",
    "DrivetrainMode",
    "EngineDetails",
    "Envelope",
    "FactoryTechnicalFeature",
    "MissingValueStatus",
    "NormalizedInterpretation",
    "NormalizedTechnicalDetails",
    "PackageOrOption",
    "ReconciliationAndReview",
    "ReconciliationState",
    "ReviewDisposition",
    "SemanticMissingValue",
    "SourceAssertion",
    "SourceAssertionSet",
    "SourceConfigurationIdentity",
    "SourceMetadata",
    "TechnicalValue",
    "TransmissionDetails",
    # Functions
    "serialize_artifact",
    "deserialize_artifact",
    "validate_artifact",
    "validate_envelope",
    "validate_source_assertion_set",
    "validate_candidate_configuration",
    "validate_semantic_missing_value",
    "IngestionValidationError",
]
