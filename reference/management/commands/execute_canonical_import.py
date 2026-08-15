"""
Django Management Command: execute_canonical_import (RA-024).

Explicit human-authorized canonical execution command. Reads a validated
CanonicalImportReviewManifest artifact, reconstructs the exact reviewed
CanonicalImportPlan, prompts operator authorization, invokes the execution
workflow service, and persists a durable ImportExecutionReceipt audit record.

GUARANTEE: Executes exactly ONE explicitly selected plan per command invocation.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.importing.workflow import (
    CanonicalExecutionWorkflowError,
    execute_canonical_import_workflow,
)
from reference.ingestion.manifest import (
    ManifestValidationError,
    dict_to_manifest,
    reconstruct_plan_from_manifest,
)


class Command(BaseCommand):
    help = (
        "Executes an explicit human-authorized canonical reference import plan "
        "from a validated review manifest artifact."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            type=str,
            required=True,
            help="Path to validated CanonicalImportReviewManifest JSON file.",
        )
        parser.add_argument(
            "--plan-ref",
            type=str,
            required=True,
            help="Candidate reference identifier of the exact reviewed plan to execute.",
        )
        parser.add_argument(
            "--operator",
            type=str,
            default="",
            help="Optional operator attribution label override (default: 'cli:<local_user>').",
        )
        parser.add_argument(
            "--adjudication-file",
            type=str,
            default="",
            help="Optional path to CanonicalImportAdjudication JSON file for adjudicated plans.",
        )

    def handle(self, *args, **options):
        manifest_path = Path(options["manifest"]).resolve()
        plan_ref = options["plan_ref"]
        operator_label = options.get("operator", "")
        adj_file_arg = options.get("adjudication_file", "")

        if not manifest_path.exists():
            raise CommandError(f"Review manifest file '{manifest_path}' does not exist.")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_dict = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to read manifest file '{manifest_path}': {str(e)}") from e

        try:
            manifest = dict_to_manifest(manifest_dict)
        except ManifestValidationError as e:
            raise CommandError(f"Manifest validation failed: {str(e)}") from e

        matching_plans = [p for p in manifest.plans if p.candidate_reference == plan_ref]
        if not matching_plans:
            raise CommandError(f"Candidate reference '{plan_ref}' not found in review manifest.")

        review_plan = matching_plans[0]

        if review_plan.planned_action in ("flag_review", "reject"):
            raise CommandError(
                f"Candidate plan '{plan_ref}' has non-executable planned action "
                f"'{review_plan.planned_action}' and cannot be executed."
            )

        # Load adjudication artifact if plan specifies ADJUDICATED_DISTINCT_GRADE
        adjudication_artifact = None
        if review_plan.create_basis == "adjudicated_distinct_grade":
            adj_path = Path(adj_file_arg).resolve() if adj_file_arg else None
            if not adj_path or not adj_path.exists():
                # Attempt default resolution in manifest directory
                ref_name = review_plan.adjudication_reference or f"adjudication_{plan_ref}.json"
                default_adj_path = manifest_path.parent / ref_name
                if default_adj_path.exists():
                    adj_path = default_adj_path

            if adj_path and adj_path.exists() and adj_path.is_file():
                try:
                    with open(adj_path, "r", encoding="utf-8") as f:
                        adj_dict = json.load(f)
                    from reference.ingestion.serialization import adjudication_from_dict
                    adjudication_artifact = adjudication_from_dict(adj_dict)
                except Exception as e:
                    raise CommandError(f"Failed to read adjudication artifact '{adj_path}': {str(e)}") from e

        # Display exact target configuration details for operator review
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(self.style.MIGRATE_HEADING("CANONICAL PROMOTION EXECUTION AUTHORIZATION"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(f"Manifest Source ID:  {manifest.source_id}")
        self.stdout.write(f"Raw Artifact Hash:   {manifest.raw_artifact_hash}")
        self.stdout.write(f"Manifest Content Hash: {manifest.manifest_hash}")
        self.stdout.write(f"Candidate Reference: {review_plan.candidate_reference}")
        self.stdout.write(f"Native Identifier:   {review_plan.native_identifier}")
        self.stdout.write(f"Eligibility Status:  {review_plan.eligibility_status}")
        self.stdout.write(f"Planned Action:      {review_plan.planned_action}")
        self.stdout.write(f"Create Basis:        {review_plan.create_basis or 'N/A'}")
        self.stdout.write(f"Target Slug:         {review_plan.target_slug}")
        self.stdout.write(f"Target Fields:       {json.dumps(review_plan.target_vehicle_definition_fields)}")
        if review_plan.reasons:
            self.stdout.write(f"Planner Reasons:     {', '.join(review_plan.reasons)}")
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 80))

        # Request explicit human operator authorization
        try:
            confirm = input("Do you authorize executing this canonical import plan? [y/N]: ")
        except (KeyboardInterrupt, EOFError):
            self.stdout.write(self.style.WARNING("\nExecution authorization aborted by user."))
            return

        if confirm.strip().lower() not in ("y", "yes"):
            self.stdout.write(self.style.WARNING("Execution authorization declined. Zero canonical writes performed."))
            return

        # Reconstruct exact reviewed plan
        plan = reconstruct_plan_from_manifest(review_plan)

        # Dispatch canonical execution workflow
        try:
            result, receipt = execute_canonical_import_workflow(
                plan=plan,
                manifest=manifest,
                review_plan=review_plan,
                operator_label=operator_label,
                adjudication_artifact=adjudication_artifact,
            )
        except CanonicalExecutionWorkflowError as e:
            raise CommandError(f"Canonical execution workflow failed: {str(e)}") from e
        except Exception as e:
            raise CommandError(f"Unexpected canonical execution error: {str(e)}") from e

        # Report execution outcome and durable receipt
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 80))
        if result.outcome.value == "created":
            self.stdout.write(self.style.SUCCESS(f"CANONICAL PROMOTION SUCCESSFUL: {result.outcome.value.upper()}"))
            self.stdout.write(f"VehicleDefinition ID:   {result.vehicle_definition_id}")
            self.stdout.write(f"VehicleDefinition UUID: {result.vehicle_definition_uuid}")
            self.stdout.write(f"VehicleDefinition Slug: {result.vehicle_definition_slug}")
        elif result.outcome.value == "no_op_exact_match":
            self.stdout.write(self.style.SUCCESS(f"CANONICAL PROMOTION NO-OP: {result.outcome.value.upper()}"))
            self.stdout.write(f"Existing Record ID:   {result.vehicle_definition_id}")
            self.stdout.write(f"Existing Record Slug: {result.vehicle_definition_slug}")
        else:
            self.stdout.write(self.style.WARNING(f"CANONICAL PROMOTION OUTCOME: {result.outcome.value.upper()}"))

        self.stdout.write(f"Execution Receipt UUID: {receipt.uuid}")
        if result.messages:
            self.stdout.write(f"Execution Messages:     {', '.join(result.messages)}")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
