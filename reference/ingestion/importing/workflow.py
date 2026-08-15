"""
Canonical Reference Import Execution Workflow Service.

Coordinates explicit human-authorized promotion attempts across the RA-019 execute_candidate_import
boundary while persisting durable ImportExecutionReceipt audit records within atomic database transactions.
"""

import getpass
from typing import Tuple

from django.db import transaction

from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportCreateBasis,
    ImportExecutionOutcome,
    ImportPlannedAction,
    execute_candidate_import,
)
from reference.ingestion.manifest import (
    CanonicalImportReviewManifest,
    CanonicalImportReviewPlan,
)
from reference.models import ImportExecutionReceipt


class CanonicalExecutionWorkflowError(Exception):
    """Raised when an infrastructure, validation, or receipt persistence error halts execution workflow."""
    pass


def execute_canonical_import_workflow(
    plan: CanonicalImportPlan,
    manifest: CanonicalImportReviewManifest,
    review_plan: CanonicalImportReviewPlan,
    operator_label: str = "",
    adjudication_artifact: Optional[Any] = None,
) -> Tuple[CanonicalImportResult, ImportExecutionReceipt]:
    """
    Executes an authorized CanonicalImportPlan and persists a durable ImportExecutionReceipt audit record.

    Enforces transaction atomicity: for CREATE attempts, canonical VehicleDefinition creation and
    ImportExecutionReceipt persistence MUST succeed together inside the same transaction.atomic() block.
    If receipt creation fails, the outer transaction rolls back the VehicleDefinition creation cleanly.
    """
    if review_plan.planned_action in (ImportPlannedAction.FLAG_REVIEW.value, ImportPlannedAction.REJECT.value):
        raise CanonicalExecutionWorkflowError(
            f"Candidate plan '{review_plan.candidate_reference}' has non-executable action "
            f"'{review_plan.planned_action}' and cannot be executed."
        )

    # Cryptographic & Structural Adjudication Artifact Verification for ADJUDICATED_DISTINCT_GRADE plans
    if review_plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE.value or plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE:
        if not adjudication_artifact:
            raise CanonicalExecutionWorkflowError(
                f"Execution refused: Plan '{review_plan.candidate_reference}' specifies ADJUDICATED_DISTINCT_GRADE "
                "basis but no validated CanonicalImportAdjudication artifact was provided to the workflow."
            )

        from reference.ingestion.contracts import CanonicalImportAdjudication
        from reference.ingestion.serialization import adjudication_to_dict, compute_adjudication_hash
        from reference.ingestion.validation import validate_adjudication

        if not isinstance(adjudication_artifact, CanonicalImportAdjudication):
            raise CanonicalExecutionWorkflowError(
                "Execution refused: Provided adjudication_artifact is not a CanonicalImportAdjudication instance."
            )

        try:
            validate_adjudication(adjudication_artifact)
        except Exception as ve:
            raise CanonicalExecutionWorkflowError(
                f"Execution refused: Adjudication artifact contract validation failed: {str(ve)}"
            ) from ve

        computed_hash = compute_adjudication_hash(adjudication_to_dict(adjudication_artifact))
        if computed_hash != adjudication_artifact.adjudication_hash:
            raise CanonicalExecutionWorkflowError(
                f"Execution refused: Adjudication artifact content hash mismatch: computed '{computed_hash}', stored '{adjudication_artifact.adjudication_hash}'."
            )

        if adjudication_artifact.adjudication_hash != review_plan.adjudication_hash or adjudication_artifact.adjudication_hash != plan.adjudication_hash:
            raise CanonicalExecutionWorkflowError(
                "Execution refused: Adjudication artifact hash does not match plan adjudication_hash."
            )

        if adjudication_artifact.candidate_reference != review_plan.candidate_reference:
            raise CanonicalExecutionWorkflowError(
                f"Execution refused: Adjudication candidate_reference '{adjudication_artifact.candidate_reference}' does not match plan '{review_plan.candidate_reference}'."
            )

        target_trim = (plan.target_vehicle_definition_fields or {}).get("trim_name")
        if target_trim and adjudication_artifact.adjudicated_trim_name != target_trim:
            raise CanonicalExecutionWorkflowError(
                f"Execution refused: Adjudication trim '{adjudication_artifact.adjudicated_trim_name}' does not match plan target trim '{target_trim}'."
            )

        if review_plan.adjudication_reference:
            expected_ref_name = f"adjudication_{review_plan.candidate_reference}.json"
            if review_plan.adjudication_reference != expected_ref_name:
                raise CanonicalExecutionWorkflowError(
                    f"Execution refused: Review plan adjudication_reference '{review_plan.adjudication_reference}' does not match expected '{expected_ref_name}'."
                )

    op_label = operator_label or f"cli:{getpass.getuser()}"

    def _build_and_save_receipt(res: CanonicalImportResult) -> ImportExecutionReceipt:
        is_created = res.outcome == ImportExecutionOutcome.CREATED
        is_noop = res.outcome == ImportExecutionOutcome.NO_OP_EXACT_MATCH

        created_vd_id = res.vehicle_definition_id if is_created else None
        created_pk = res.vehicle_definition_id if is_created else None
        created_uuid = res.vehicle_definition_uuid if is_created else ""
        created_slug = res.vehicle_definition_slug if is_created else ""

        existing_vd_id = res.vehicle_definition_id if is_noop else None
        existing_pk = res.vehicle_definition_id if is_noop else None
        existing_uuid = res.vehicle_definition_uuid if is_noop else ""
        existing_slug = res.vehicle_definition_slug if is_noop else ""

        target_fields = dict(review_plan.target_vehicle_definition_fields)

        return ImportExecutionReceipt.objects.create(
            operator_label=op_label,
            execution_channel="cli",
            manifest_hash=manifest.manifest_hash,
            candidate_reference=review_plan.candidate_reference,
            planned_action=review_plan.planned_action,
            create_basis=review_plan.create_basis or "",
            adjudication_hash=review_plan.adjudication_hash or "",
            source_id=manifest.source_id,
            raw_artifact_hash=manifest.raw_artifact_hash,
            raw_artifact_reference=manifest.raw_artifact_reference,
            source_identity_type=review_plan.source_identity_type,
            native_identifier=review_plan.native_identifier,
            resolved_generation_id=review_plan.resolved_generation_id,
            target_slug=review_plan.target_slug or "",
            target_model_year=target_fields.get("model_year"),
            target_trim_name=target_fields.get("trim_name", ""),
            target_engine_name=target_fields.get("engine_name", ""),
            target_drivetrain=target_fields.get("drivetrain", ""),
            target_market=target_fields.get("market", ""),
            target_fields_json=target_fields,
            execution_outcome=res.outcome.value,
            messages_json=list(res.messages),
            created_vehicle_definition_id=created_vd_id,
            created_vehicle_definition_pk_snapshot=created_pk,
            created_vehicle_definition_uuid_snapshot=created_uuid,
            created_vehicle_definition_slug_snapshot=created_slug,
            existing_vehicle_definition_id=existing_vd_id,
            existing_vehicle_definition_pk_snapshot=existing_pk,
            existing_vehicle_definition_uuid_snapshot=existing_uuid,
            existing_vehicle_definition_slug_snapshot=existing_slug,
        )

    if plan.planned_action == ImportPlannedAction.CREATE:
        try:
            with transaction.atomic():
                result = execute_candidate_import(plan)
                receipt = _build_and_save_receipt(result)
                return result, receipt
        except Exception as e:
            if isinstance(e, CanonicalExecutionWorkflowError):
                raise
            raise CanonicalExecutionWorkflowError(
                f"Transactional execution workflow failed for plan '{plan.candidate_reference}': {str(e)}"
            ) from e
    else:
        result = execute_candidate_import(plan)
        try:
            receipt = _build_and_save_receipt(result)
            return result, receipt
        except Exception as e:
            raise CanonicalExecutionWorkflowError(
                f"Failed to persist execution receipt for non-mutating outcome '{result.outcome.value}': {str(e)}"
            ) from e
