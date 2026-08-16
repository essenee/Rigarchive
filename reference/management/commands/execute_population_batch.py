"""
One-Step Batch Population Execution Management Command (RA-031 Part 2 & 3).

Loads a PopulationBatchManifest, displays ONE complete review summary, prompts once for
operator domain authorization, and dispatches batch execution.

Preserves per-record canonical execution safeguards, stale-plan revalidation, and individual
ImportExecutionReceipt audit provenance logs linked to the batch manifest hash.
"""

import json, sys
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.manifest import PopulationBatchItem, PopulationBatchManifest
from reference.ingestion.orchestration.generation_bootstrap import GenerationBootstrapOrchestrator


class Command(BaseCommand):
    help = "Execute an authorized population batch manifest inside a single operator authorization boundary."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--manifest",
            type=str,
            required=True,
            help="Path to serialized PopulationBatchManifest JSON file.",
        )
        parser.add_argument(
            "--authorize",
            action="store_true",
            help="Provide non-interactive operator domain authorization for reviewed batch execution.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        manifest_path = Path(options["manifest"])
        if not manifest_path.exists():
            raise CommandError(f"Population batch manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = [
                PopulationBatchItem(
                    candidate_reference=it["candidate_reference"],
                    native_identifier=it["native_identifier"],
                    model_year=it["model_year"],
                    trim_name=it.get("trim_name"),
                    engine_name=it.get("engine_name"),
                    drivetrain=it.get("drivetrain"),
                    planned_action=it["planned_action"],
                    create_basis=it.get("create_basis"),
                    target_slug=it["target_slug"],
                )
                for it in data.get("items", [])
            ]

            manifest = PopulationBatchManifest(
                batch_id=data["batch_id"],
                manufacturer_name=data["manufacturer_name"],
                vehicle_model_name=data["vehicle_model_name"],
                market=data["market"],
                start_year=data["start_year"],
                end_year=data["end_year"],
                total_candidates=data["total_candidates"],
                create_count=data["create_count"],
                no_op_count=data["no_op_count"],
                review_count=data["review_count"],
                items=items,
                created_at=data.get("created_at", ""),
                batch_manifest_hash=data.get("batch_manifest_hash", ""),
            )
        except Exception as e:
            raise CommandError(f"Failed to parse PopulationBatchManifest JSON from '{manifest_path}': {e}") from e

        # Validate manifest hash integrity
        expected_hash = manifest.compute_manifest_hash()
        if manifest.batch_manifest_hash and manifest.batch_manifest_hash != expected_hash:
            raise CommandError(
                f"Batch manifest integrity mismatch! Stored hash '{manifest.batch_manifest_hash}' "
                f"does not match computed hash '{expected_hash}'."
            )

        # Display ONE review summary
        self.stdout.write(manifest.summary_text())

        # Check authorization
        authorized = options["authorize"]
        if not authorized:
            if sys.stdin.isatty():
                response = input("\nDo you authorize executing this population batch? [y/N]: ").strip().lower()
                authorized = response in ("y", "yes")
            else:
                self.stdout.write(self.style.WARNING("\nNon-interactive mode without --authorize flag. Zero writes performed."))
                return

        if not authorized:
            self.stdout.write(self.style.WARNING("Batch execution cancelled by operator. Zero writes performed."))
            return

        self.stdout.write(self.style.SUCCESS(f"\nOperator authorization confirmed for batch '{manifest.batch_id}' ({manifest.batch_manifest_hash}). Executing batch..."))

        orchestrator = GenerationBootstrapOrchestrator()
        result = orchestrator.execute_authorized_batch(manifest)

        self.stdout.write(self.style.SUCCESS("\n=== BATCH EXECUTION COMPLETE ==="))
        self.stdout.write(f"Total Attempted:      {result['total_attempted']}")
        self.stdout.write(f"Created:              {result['created']}")
        self.stdout.write(f"Exact Match / No-Op:  {result['no_op']}")
        self.stdout.write(f"Blocked / Exceptions: {result['blocked']}")
        self.stdout.write(f"Outside Authorized:   {result['outside_authorization']}")
