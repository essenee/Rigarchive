"""
Non-Canonical-Writing Generation Population Planning Management Command (RA-040).

Invokes GenerationBootstrapOrchestrator to construct a deterministic PopulationBatchManifest
for a requested vehicle model and model-year range without performing any database writes.

Optionally writes the reviewed batch manifest JSON file to an explicit output path.
"""

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.orchestration.generation_bootstrap import GenerationBootstrapOrchestrator


class Command(BaseCommand):
    help = "Construct and display/save a PopulationBatchManifest for a target model and year range (STRICTLY NON-CANONICAL-WRITING)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--manufacturer",
            type=str,
            required=True,
            help="Manufacturer name (e.g. 'Toyota').",
        )
        parser.add_argument(
            "--model",
            type=str,
            required=True,
            help="VehicleModel name (e.g. '4Runner').",
        )
        parser.add_argument(
            "--market",
            type=str,
            default="US",
            help="Commercial sales market (default: 'US').",
        )
        parser.add_argument(
            "--start-year",
            type=int,
            default=None,
            help="Start model year (e.g. 2025).",
        )
        parser.add_argument(
            "--end-year",
            type=int,
            default=None,
            help="End model year (e.g. 2026). Defaults to start-year if omitted.",
        )
        parser.add_argument(
            "--model-year",
            type=int,
            default=None,
            help="Single model year shortcut (e.g. 2025). Sets start-year and end-year.",
        )
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default=None,
            help="File path to save the serialized PopulationBatchManifest JSON.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Allow overwriting output file if it already exists.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output raw batch manifest JSON to stdout instead of summary text.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        manufacturer = options["manufacturer"].strip()
        model = options["model"].strip()
        market = options["market"].strip()

        start_year = options["start_year"]
        end_year = options["end_year"]
        model_year = options["model_year"]

        if model_year is not None:
            start_year = model_year
            end_year = model_year

        if start_year is None:
            raise CommandError("Either --start-year or --model-year must be specified.")

        if end_year is None:
            end_year = start_year

        if start_year > end_year:
            raise CommandError(f"Start year ({start_year}) cannot be greater than end year ({end_year}).")

        orchestrator = GenerationBootstrapOrchestrator()

        try:
            manifest = orchestrator.create_batch_manifest(
                make=manufacturer,
                model=model,
                market=market,
                start_year=start_year,
                end_year=end_year,
            )
        except Exception as e:
            raise CommandError(f"Failed to plan generation population batch: {e}") from e

        manifest_dict = asdict(manifest)

        # File output handling
        output_path_str = options["output"]
        if output_path_str:
            output_path = Path(output_path_str)
            if output_path.exists() and not options["overwrite"]:
                raise CommandError(
                    f"Output manifest file already exists at '{output_path}'. "
                    f"Use --overwrite to allow replacing existing manifest."
                )

            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_dict, f, indent=2)
                self.stdout.write(self.style.SUCCESS(f"Saved PopulationBatchManifest ({manifest.batch_manifest_hash}) to '{output_path}'."))
            except Exception as e:
                raise CommandError(f"Failed to write manifest output file to '{output_path}': {e}") from e

        # Stdout output handling
        if options["json"]:
            self.stdout.write(json.dumps(manifest_dict, indent=2))
        else:
            self.stdout.write(manifest.summary_text())
