"""
Canonical Import Executor (RA-018 / RA-019).

Executes transient CanonicalImportPlan artifacts inside database transactions.
Enforces Create-Only policy, stale plan revalidation, exact-match no-op logic,
and safe IntegrityError handling.
"""

from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


from reference.ingestion.importing import (
    CanonicalImportPlan,
    CanonicalImportResult,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportExecutionOutcome,
    ImportPlannedAction,
)
from reference.ingestion.importing.planner import _fields_match_exact
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


def execute_candidate_import(
    plan: CanonicalImportPlan,
) -> CanonicalImportResult:
    """
    Execute a CanonicalImportPlan inside a database transaction.

    Enforces Create-Only policy: creates proven-distinct new VehicleDefinition rows,
    executes idempotent no-ops on exact existing matches, and aborts stale plans.
    Never updates existing VehicleDefinition records, never deletes records, and
    never automatically creates parent entities.
    """
    ref_id = plan.candidate_reference

    # 1. Non-Create / Review / Reject Plan Handling (0 Writes)
    if plan.planned_action == ImportPlannedAction.FLAG_REVIEW:
        return CanonicalImportResult(
            candidate_reference=ref_id,
            outcome=ImportExecutionOutcome.FLAGGED_REVIEW,
            messages=plan.reasons or ["Plan flagged for human review."],
        )

    if plan.planned_action == ImportPlannedAction.REJECT or plan.eligibility_status == ImportEligibilityStatus.INELIGIBLE:
        return CanonicalImportResult(
            candidate_reference=ref_id,
            outcome=ImportExecutionOutcome.REJECTED,
            messages=plan.reasons or ["Plan rejected as ineligible."],
        )

    # 2. Exact-Match No-Op Handling (0 Writes)
    if plan.planned_action == ImportPlannedAction.NO_OP_EXACT_MATCH:
        if not plan.existing_vehicle_definition_id:
            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                messages=["No-Op plan missing existing_vehicle_definition_id."],
            )

        existing = VehicleDefinition.objects.filter(id=plan.existing_vehicle_definition_id, is_active=True).first()
        if (
            existing
            and existing.generation_id == plan.resolved_generation_id
            and existing.slug == plan.target_slug
            and _fields_match_exact(existing, plan.target_vehicle_definition_fields)
        ):
            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.NO_OP_EXACT_MATCH,
                vehicle_definition_id=existing.id,
                vehicle_definition_uuid=str(existing.uuid),
                vehicle_definition_slug=existing.slug,
                messages=["Exact match verified in canonical Reference database. Zero writes performed."],
            )
        else:
            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                messages=["Existing record was deleted, deactivated, or modified prior to execution."],
            )

    # 3. Create Execution (Create-Only)
    if plan.planned_action != ImportPlannedAction.CREATE or plan.eligibility_status != ImportEligibilityStatus.ELIGIBLE:
        return CanonicalImportResult(
            candidate_reference=ref_id,
            outcome=ImportExecutionOutcome.REJECTED,
            messages=["Invalid plan action or status for execution."],
        )

    # Transactional Create Attempt
    try:
        with transaction.atomic():
            # Revalidate parent entities exist in database
            if not Manufacturer.objects.filter(id=plan.resolved_manufacturer_id, is_active=True).exists():
                return CanonicalImportResult(
                    candidate_reference=ref_id,
                    outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                    messages=["Resolved Manufacturer no longer active in database."],
                )

            if not VehicleModel.objects.filter(id=plan.resolved_vehicle_model_id, is_active=True).exists():
                return CanonicalImportResult(
                    candidate_reference=ref_id,
                    outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                    messages=["Resolved VehicleModel no longer active in database."],
                )

            if not Generation.objects.filter(id=plan.resolved_generation_id, is_active=True).exists():
                return CanonicalImportResult(
                    candidate_reference=ref_id,
                    outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                    messages=["Resolved Generation no longer active in database."],
                )

            # Re-check concurrent insert of target slug inside transaction
            existing_concurrent = VehicleDefinition.objects.filter(
                generation_id=plan.resolved_generation_id,
                slug=plan.target_slug,
                is_active=True,
            ).first()

            if existing_concurrent:
                if _fields_match_exact(existing_concurrent, plan.target_vehicle_definition_fields):
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.NO_OP_EXACT_MATCH,
                        vehicle_definition_id=existing_concurrent.id,
                        vehicle_definition_uuid=str(existing_concurrent.uuid),
                        vehicle_definition_slug=existing_concurrent.slug,
                        messages=["Concurrent insert detected matching target slug. Verified identical fields."],
                    )
                else:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Concurrent insert detected matching target slug with conflicting fields."],
                    )

            # Revalidate distinctness basis against current canonical namespace
            target_year = plan.target_vehicle_definition_fields.get("model_year")
            target_market = plan.target_vehicle_definition_fields.get("market")
            current_namespace_rows = list(
                VehicleDefinition.objects.filter(
                    generation_id=plan.resolved_generation_id,
                    model_year=target_year,
                    market=target_market,
                    is_active=True,
                )
            )

            if plan.create_basis == ImportCreateBasis.FIRST_REPRESENTATION:
                if len(current_namespace_rows) > 0:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["First-representation CREATE plan is stale because new canonical records exist in namespace."],
                    )

            elif plan.create_basis == ImportCreateBasis.MECHANICAL_DIMENSION:
                expected_count = plan.namespace_snapshot_count or 0
                if len(current_namespace_rows) != expected_count:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Mechanical-dimension CREATE plan is stale because canonical namespace count changed."],
                    )

                if not plan.mechanical_basis_existing_id:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Mechanical-dimension CREATE plan missing mechanical_basis_existing_id."],
                    )

                basis_vd = VehicleDefinition.objects.filter(id=plan.mechanical_basis_existing_id, is_active=True).first()
                if not basis_vd:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Original mechanical basis record was deleted prior to execution."],
                    )

                if (
                    basis_vd.generation_id != plan.resolved_generation_id
                    or basis_vd.model_year != target_year
                    or basis_vd.market != target_market
                    or basis_vd.trim_name != plan.target_vehicle_definition_fields.get("trim_name")
                    or basis_vd.drivetrain == plan.target_vehicle_definition_fields.get("drivetrain")
                ):
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Original mechanical basis record was modified prior to execution."],
                    )

            elif plan.create_basis == ImportCreateBasis.SOURCE_ESTABLISHED_GRADE:
                expected_count = plan.namespace_snapshot_count or 0
                if len(current_namespace_rows) != expected_count:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Source-established grade CREATE plan is stale because canonical namespace count changed."],
                    )

            elif plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE:
                if not plan.adjudication_hash:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Adjudicated CREATE plan missing adjudication_hash provenance."],
                    )

                target_trim = plan.target_vehicle_definition_fields.get("trim_name")
                same_trim_exists = any(row.trim_name == target_trim for row in current_namespace_rows)

                if same_trim_exists:
                    return CanonicalImportResult(
                        candidate_reference=ref_id,
                        outcome=ImportExecutionOutcome.ABORTED_STALE_PLAN,
                        messages=["Adjudicated CREATE plan is stale because a canonical record with matching trim now exists."],
                    )

            # Instantiate new VehicleDefinition instance
            vd = VehicleDefinition(
                generation_id=plan.resolved_generation_id,
                **plan.target_vehicle_definition_fields,
            )

            # Model validation before save
            try:
                vd.full_clean()
                vd.save()
            except ValidationError as ve:
                return CanonicalImportResult(
                    candidate_reference=ref_id,
                    outcome=ImportExecutionOutcome.REJECTED,
                    messages=[f"Model validation failed: {ve}"],
                )

            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.CREATED,
                vehicle_definition_id=vd.id,
                vehicle_definition_uuid=str(vd.uuid),
                vehicle_definition_slug=vd.slug,
                messages=["Successfully created new canonical VehicleDefinition."],
            )


    except IntegrityError:
        # Atomic block has exited and rolled back cleanly. Re-query outside atomic block.
        existing_after = VehicleDefinition.objects.filter(
            generation_id=plan.resolved_generation_id,
            slug=plan.target_slug,
            is_active=True,
        ).first()

        if existing_after and _fields_match_exact(existing_after, plan.target_vehicle_definition_fields):
            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.NO_OP_EXACT_MATCH,
                vehicle_definition_id=existing_after.id,
                vehicle_definition_uuid=str(existing_after.uuid),
                vehicle_definition_slug=existing_after.slug,
                messages=["Caught concurrent IntegrityError. Verified identical fields and resolved to no-op."],
            )
        else:
            return CanonicalImportResult(
                candidate_reference=ref_id,
                outcome=ImportExecutionOutcome.REJECTED,
                messages=["Caught database IntegrityError. Target record absent or fields conflict."],
            )
