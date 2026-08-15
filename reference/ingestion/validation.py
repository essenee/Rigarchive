"""
Structural and Semantic Validation for Reference Ingestion Serialization (RA-011 / RA-012).

Provides contract validation for SourceAssertionSet and CandidateConfigurationDocument
artifacts, ensuring envelope metadata, assertion uniqueness, provenance traceability,
reconciliation/review categories, and semantic missing-value states satisfy contract rules.
"""

import re
from typing import List, Optional, Set, Union

from reference.ingestion.contracts import (
    ArtifactType,
    CandidateConfigurationDocument,
    MissingValueStatus,
    ReconciliationState,
    ReviewDisposition,
    SemanticMissingValue,
    SourceAssertionSet,
)


class IngestionValidationError(ValueError):
    """Raised when an ingestion artifact fails structural or semantic contract validation."""
    pass


def validate_envelope(envelope, expected_type: str) -> None:
    """Validate artifact envelope metadata."""
    if not envelope.artifact_type:
        raise IngestionValidationError("Envelope 'artifact_type' is required and cannot be empty.")
    if envelope.artifact_type != expected_type:
        raise IngestionValidationError(
            f"Envelope 'artifact_type' mismatch: expected '{expected_type}', got '{envelope.artifact_type}'."
        )
    if not envelope.schema_version:
        raise IngestionValidationError("Envelope 'schema_version' is required and cannot be empty.")

    # Validate SemVer pattern (MAJOR.MINOR.PATCH)
    semver_match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", envelope.schema_version)
    if not semver_match:
        raise IngestionValidationError(
            f"Envelope 'schema_version' '{envelope.schema_version}' must be a valid SemVer string (MAJOR.MINOR.PATCH)."
        )

    major_version = semver_match.group(1)
    if major_version != "1":
        raise IngestionValidationError(
            f"Unsupported major schema_version '{major_version}' (contract supports major version 1)."
        )


def validate_source_assertion_set(obj: SourceAssertionSet) -> None:
    """Validate structural and semantic rules for a Tier 1 SourceAssertionSet."""
    validate_envelope(obj.envelope, ArtifactType.SOURCE_ASSERTION_SET.value)

    if not obj.provenance.source_id:
        raise IngestionValidationError("SourceMetadata 'source_id' is required and cannot be empty.")

    seen_assertion_ids: Set[str] = set()
    for ast in obj.source_assertions:
        if not ast.assertion_id:
            raise IngestionValidationError("SourceAssertion 'assertion_id' cannot be empty.")
        if not ast.attribute_key:
            raise IngestionValidationError(
                f"SourceAssertion '{ast.assertion_id}' missing required 'attribute_key'."
            )
        if ast.assertion_id in seen_assertion_ids:
            raise IngestionValidationError(
                f"Duplicate assertion_id '{ast.assertion_id}' found in SourceAssertionSet."
            )
        seen_assertion_ids.add(ast.assertion_id)


def validate_candidate_configuration(
    obj: CandidateConfigurationDocument,
    source_assertion_set: Optional[SourceAssertionSet] = None,
) -> None:
    """Validate structural and semantic rules for a Tier 2 CandidateConfigurationDocument."""
    validate_envelope(obj.envelope, ArtifactType.CANDIDATE_CONFIGURATION.value)

    if not obj.candidate_reference:
        raise IngestionValidationError("CandidateConfigurationDocument 'candidate_reference' is required.")

    if not obj.candidate_identity.manufacturer_name:
        raise IngestionValidationError("CandidateIdentity 'manufacturer_name' is required.")
    if not obj.candidate_identity.vehicle_model_name:
        raise IngestionValidationError("CandidateIdentity 'vehicle_model_name' is required.")

    if obj.candidate_identity.model_year is not None:
        year = obj.candidate_identity.model_year
        if year < 1886 or year > 2100:
            raise IngestionValidationError(f"CandidateIdentity 'model_year' {year} is out of reasonable range (1886-2100).")

    # Track valid assertion IDs if SourceAssertionSet context provided
    valid_source_assertion_ids: Set[str] = set()
    if source_assertion_set is not None:
        valid_source_assertion_ids = {a.assertion_id for a in source_assertion_set.source_assertions}

    seen_interp_ids: Set[str] = set()
    for interp in obj.normalized_assertions:
        if not interp.interpretation_id:
            raise IngestionValidationError("NormalizedInterpretation 'interpretation_id' cannot be empty.")
        if not interp.source_assertion_ref:
            raise IngestionValidationError(
                f"NormalizedInterpretation '{interp.interpretation_id}' missing 'source_assertion_ref'."
            )
        if not interp.target_attribute_key:
            raise IngestionValidationError(
                f"NormalizedInterpretation '{interp.interpretation_id}' missing 'target_attribute_key'."
            )
        if interp.interpretation_id in seen_interp_ids:
            raise IngestionValidationError(
                f"Duplicate interpretation_id '{interp.interpretation_id}' found in CandidateConfigurationDocument."
            )
        seen_interp_ids.add(interp.interpretation_id)

        # Check for broken source assertion references when context is available
        if source_assertion_set is not None and interp.source_assertion_ref not in valid_source_assertion_ids:
            raise IngestionValidationError(
                f"NormalizedInterpretation '{interp.interpretation_id}' references unknown source_assertion_ref '{interp.source_assertion_ref}'."
            )

    # Check attribute provenance links to interpretation IDs
    for attr, interp_refs in obj.attribute_provenance.items():
        for ref in interp_refs:
            if ref not in seen_interp_ids:
                raise IngestionValidationError(
                    f"Attribute provenance for '{attr}' references unknown interpretation_id '{ref}'."
                )

    # Validate reconciliation and review states if present
    if obj.reconciliation_and_review is not None:
        rar = obj.reconciliation_and_review
        valid_dispositions = {d.value for d in ReviewDisposition}
        if rar.review_workflow_disposition not in valid_dispositions:
            raise IngestionValidationError(
                f"Invalid review_workflow_disposition '{rar.review_workflow_disposition}'. Expected one of {valid_dispositions}."
            )

        valid_states = {s.value for s in ReconciliationState}
        for attr, state in rar.attribute_states.items():
            if state.reconciliation_state not in valid_states:
                raise IngestionValidationError(
                    f"Invalid reconciliation_state '{state.reconciliation_state}' for attribute '{attr}'. Expected one of {valid_states}."
                )
            if state.review_disposition not in valid_dispositions:
                raise IngestionValidationError(
                    f"Invalid review_disposition '{state.review_disposition}' for attribute '{attr}'. Expected one of {valid_dispositions}."
                )


def validate_semantic_missing_value(obj: SemanticMissingValue) -> None:
    """Validate semantic missing value status."""
    valid_statuses = {s.value for s in MissingValueStatus}
    if obj.status not in valid_statuses:
        raise IngestionValidationError(
            f"Invalid SemanticMissingValue status '{obj.status}'. Expected one of {valid_statuses}."
        )


def validate_artifact(
    obj: Union[SourceAssertionSet, CandidateConfigurationDocument],
    source_assertion_set: Optional[SourceAssertionSet] = None,
) -> None:
    """
    Main validation entry point for ingestion artifacts.
    Validates structural integrity, envelope metadata, unique IDs, reference traceability,
    and reconciliation/review status boundaries.
    """
    if isinstance(obj, SourceAssertionSet):
        validate_source_assertion_set(obj)
    elif isinstance(obj, CandidateConfigurationDocument):
        validate_candidate_configuration(obj, source_assertion_set=source_assertion_set)
    else:
        raise IngestionValidationError(f"Unsupported object type for validation: {type(obj)}")
