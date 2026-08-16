"""
Canonical Record Correction & Supersession Workflow Service (RA-029).

Executes general canonical record corrections: supersedes obsolete/incorrect
canonical VehicleDefinition records (is_active=False) and creates/links replacement
canonical VehicleDefinition records while persisting durable CanonicalRecordCorrection
audit records inside atomic database transactions.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from django.db import transaction

from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportExecutionOutcome,
    execute_candidate_import,
)
from reference.ingestion.importing.workflow import execute_canonical_import_workflow
from reference.models import (
    CanonicalRecordCorrection,
    ImportExecutionReceipt,
    VehicleDefinition,
)


class CanonicalCorrectionWorkflowError(Exception):
    """Raised when validation, execution, or persistence fails during correction workflow."""
    pass


@dataclass
class CanonicalRecordCorrectionResult:
    """Dataclass reporting outcome and identity snapshots of a canonical correction execution."""

    outcome: str  # "CORRECTED", "NO_OP_ALREADY_CORRECTED", "FAILED_REPLACEMENT_EXECUTION"
    superseded_vehicle_definition_id: int
    superseded_vehicle_definition_uuid: str
    superseded_vehicle_definition_slug: str
    replacement_vehicle_definition_id: Optional[int] = None
    replacement_vehicle_definition_uuid: Optional[str] = None
    replacement_vehicle_definition_slug: Optional[str] = None
    execution_receipt_uuid: Optional[str] = None
    correction_audit_uuid: Optional[str] = None
    messages: List[str] = field(default_factory=list)


def execute_canonical_record_correction(
    superseded_vehicle_definition: VehicleDefinition,
    replacement_plan: Optional[CanonicalImportPlan] = None,
    correction_reason: str = CanonicalRecordCorrection.CorrectionReason.NORMALIZATION_RULE_CORRECTION,
    operator_label: str = "cli:canonical_correction_operator",
    adjudication_artifact: Optional[Any] = None,
    manifest: Optional[Any] = None,
    review_plan: Optional[Any] = None,
    candidate_document: Optional[Any] = None,
) -> CanonicalRecordCorrectionResult:
    """
    Execute a canonical record correction and supersession workflow inside an atomic transaction.

    Steps:
    1. Revalidate superseded record active state. If already inactive, check for existing correction.
    2. Deactivate superseded record (is_active=False).
    3. Re-plan candidate document (if candidate_document provided) or execute replacement plan.
    4. Persist durable CanonicalRecordCorrection audit record linking old -> replacement.
    5. Return CanonicalRecordCorrectionResult.
    """
    superseded_id = superseded_vehicle_definition.id
    superseded_uuid = str(superseded_vehicle_definition.uuid)
    superseded_slug = superseded_vehicle_definition.slug

    # 1. Recheck active state outside/at start of transaction
    current_vd = VehicleDefinition.objects.filter(id=superseded_id).first()
    if not current_vd:
        raise CanonicalCorrectionWorkflowError(
            f"Superseded VehicleDefinition ID {superseded_id} does not exist in database."
        )

    if not current_vd.is_active:
        # Check if already corrected
        existing_corr = CanonicalRecordCorrection.objects.filter(
            superseded_vehicle_definition_pk_snapshot=superseded_id
        ).first()

        if existing_corr:
            return CanonicalRecordCorrectionResult(
                outcome="NO_OP_ALREADY_CORRECTED",
                superseded_vehicle_definition_id=superseded_id,
                superseded_vehicle_definition_uuid=superseded_uuid,
                superseded_vehicle_definition_slug=superseded_slug,
                replacement_vehicle_definition_id=existing_corr.replacement_vehicle_definition_pk_snapshot,
                replacement_vehicle_definition_uuid=existing_corr.replacement_vehicle_definition_uuid_snapshot,
                replacement_vehicle_definition_slug=existing_corr.replacement_vehicle_definition_slug_snapshot,
                execution_receipt_uuid=str(existing_corr.execution_receipt.uuid) if existing_corr.execution_receipt else None,
                correction_audit_uuid=str(existing_corr.uuid),
                messages=["Record has already been superseded by a prior canonical correction."],
            )
        else:
            raise CanonicalCorrectionWorkflowError(
                f"Superseded VehicleDefinition ID {superseded_id} is inactive but no correction audit record was found."
            )

    # 2. Atomic Correction Execution Block
    with transaction.atomic():
        # Deactivate superseded record
        current_vd.is_active = False
        current_vd.save(update_fields=["is_active", "updated_at"])

        if candidate_document:
            from reference.ingestion.importing.planner import plan_candidate_import
            effective_plan = plan_candidate_import(candidate_document)
        else:
            effective_plan = replacement_plan

        if not effective_plan:
            transaction.set_rollback(True)
            raise CanonicalCorrectionWorkflowError("No replacement plan or candidate document provided for correction.")

        receipt = None
        if manifest and review_plan:
            import_res, receipt = execute_canonical_import_workflow(
                plan=effective_plan,
                manifest=manifest,
                review_plan=review_plan,
                operator_label=operator_label,
                adjudication_artifact=adjudication_artifact,
            )
        else:
            import_res = execute_candidate_import(effective_plan)

        if import_res.outcome not in (
            ImportExecutionOutcome.CREATED,
            ImportExecutionOutcome.NO_OP_EXACT_MATCH,
        ):
            # Force rollback if replacement execution did not succeed
            transaction.set_rollback(True)
            return CanonicalRecordCorrectionResult(
                outcome="FAILED_REPLACEMENT_EXECUTION",
                superseded_vehicle_definition_id=superseded_id,
                superseded_vehicle_definition_uuid=superseded_uuid,
                superseded_vehicle_definition_slug=superseded_slug,
                messages=import_res.messages or ["Replacement promotion execution failed."],
            )

        replacement_vd_id = import_res.vehicle_definition_id
        replacement_vd = VehicleDefinition.objects.get(id=replacement_vd_id)

        # Persist durable CanonicalRecordCorrection audit record
        correction_audit = CanonicalRecordCorrection.objects.create(
            superseded_vehicle_definition=current_vd,
            replacement_vehicle_definition=replacement_vd,
            superseded_vehicle_definition_pk_snapshot=current_vd.id,
            superseded_vehicle_definition_uuid_snapshot=str(current_vd.uuid),
            superseded_vehicle_definition_slug_snapshot=current_vd.slug,
            replacement_vehicle_definition_pk_snapshot=replacement_vd.id,
            replacement_vehicle_definition_uuid_snapshot=str(replacement_vd.uuid),
            replacement_vehicle_definition_slug_snapshot=replacement_vd.slug,
            correction_reason=correction_reason,
            operator_label=operator_label,
            execution_receipt=receipt,
        )

        return CanonicalRecordCorrectionResult(
            outcome="CORRECTED",
            superseded_vehicle_definition_id=current_vd.id,
            superseded_vehicle_definition_uuid=str(current_vd.uuid),
            superseded_vehicle_definition_slug=current_vd.slug,
            replacement_vehicle_definition_id=replacement_vd.id,
            replacement_vehicle_definition_uuid=str(replacement_vd.uuid),
            replacement_vehicle_definition_slug=replacement_vd.slug,
            execution_receipt_uuid=str(receipt.uuid) if receipt else None,
            correction_audit_uuid=str(correction_audit.uuid),
            messages=[
                f"Successfully superseded canonical record '{current_vd.slug}' with corrected record '{replacement_vd.slug}'."
            ],
        )
