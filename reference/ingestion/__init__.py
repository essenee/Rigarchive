"""
Reference Data Ingestion Intermediate Serialization Package (RA-011 / RA-012).

Provides pure Python serialization contracts, deterministic JSON round-trip utilities,
and contract validation for reference ingestion intermediate artifacts.
"""

from reference.ingestion.acquisition import (
    AcquisitionError,
    EPAAdapter,
    ManufacturerSpecificationAdapter,
    NHTSAAdapter,
    SourceParseError,
    TransportError,
)
from reference.ingestion.candidate import (
    CandidateConstructionError,
    construct_candidate_configuration,
)
from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportExecutionOutcome,
    ImportPlannedAction,
    execute_candidate_import,
    plan_candidate_import,
)

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
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceConfigurationIdentity,
    SourceMetadata,
    TechnicalValue,
    TransmissionDetails,
)
from reference.ingestion.normalization import (
    BaseSourceNormalizer,
    EPANormalizer,
    ManufacturerNormalizer,
    NHTSANormalizer,
    NormalizationError,
    UnsupportedSourceError,
    normalize_source_assertions,
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
    "SourceApplicability",
    "SourceAssertion",
    "SourceAssertionSet",
    "SourceConfigurationIdentity",
    "SourceMetadata",
    "TechnicalValue",
    "TransmissionDetails",
    # Functions & Utilities
    "serialize_artifact",
    "deserialize_artifact",
    "validate_artifact",
    "validate_envelope",
    "validate_source_assertion_set",
    "validate_candidate_configuration",
    "validate_semantic_missing_value",
    "IngestionValidationError",
    # Acquisition Adapters
    "NHTSAAdapter",
    "EPAAdapter",
    "ManufacturerSpecificationAdapter",
    "AcquisitionError",
    "TransportError",
    "SourceParseError",
    # Normalization Layer
    "BaseSourceNormalizer",
    "NHTSANormalizer",
    "EPANormalizer",
    "ManufacturerNormalizer",
    "NormalizationError",
    "UnsupportedSourceError",
    # Candidate Construction Engine
    "CandidateConstructionError",
    "construct_candidate_configuration",
    # Canonical Import Engine
    "ImportEligibilityStatus",
    "ImportPlannedAction",
    "ImportExecutionOutcome",
    "ImportCreateBasis",
    "CanonicalImportPlan",
    "CanonicalImportResult",
    "plan_candidate_import",
    "execute_candidate_import",
]
