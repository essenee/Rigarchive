"""
Django Management Command: acquire_manufacturer_specs (RA-023).

Operator-invoked CLI command for acquiring production manufacturer specifications,
storing immutable raw snapshots with full SHA-256 hashing, extracting configuration
assertions, normalizing, constructing candidates, and rendering dry-run import plan reports.

GUARANTEE: Dry-run planning only. NEVER invokes execute_candidate_import().
"""

from dataclasses import asdict
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.acquisition.profiles import ToyotaUSAPressroomProfile
from reference.ingestion.manifest import build_review_manifest, manifest_to_dict
from reference.ingestion.orchestration.manufacturer import ProductionManufacturerOrchestrator



class Command(BaseCommand):
    help = (
        "Acquires authoritative manufacturer specification artifacts, retains immutable "
        "raw snapshots, and executes dry-run canonical import planning without database writes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Path to local authoritative manufacturer specification artifact file.",
        )
        parser.add_argument(
            "--url",
            type=str,
            help="HTTPS URL to acquire live authoritative specification payload.",
        )
        parser.add_argument(
            "--profile",
            type=str,
            default="toyota_usa",
            help="Publication source profile identifier (default: 'toyota_usa').",
        )
        parser.add_argument(
            "--transcription-file",
            type=str,
            help="Optional path to verified structured derivative transcription JSON file.",
        )
        parser.add_argument(
            "--output-json",
            type=str,
            help="Optional output file path to save machine-readable dry-run JSON report.",
        )
        parser.add_argument(
            "--output-manifest",
            type=str,
            help="Optional output file path to save executable CanonicalImportReviewManifest JSON artifact.",
        )

    def handle(self, *args, **options):

        file_arg = options.get("file")
        url_arg = options.get("url")
        profile_name = options.get("profile", "toyota_usa")

        if not file_arg and not url_arg:
            # Default to authentic raw Toyota pricing PDF fixture if no input specified
            default_fixture = (
                settings.BASE_DIR
                / "reference"
                / "tests"
                / "fixtures"
                / "acquisition"
                / "toyota"
                / "2020_4runner_pricing.pdf"
            )
            file_arg = str(default_fixture)

        if profile_name != "toyota_usa":
            raise CommandError(f"Unsupported publication profile '{profile_name}'. Approved profile: 'toyota_usa'.")

        transcription_path = options.get("transcription_file") or options.get("transcription-file")
        if not transcription_path and file_arg and file_arg.endswith(".json"):
            transcription_path = file_arg

        transcription_data = None
        expected_raw_hash = None

        if transcription_path:
            try:
                with open(transcription_path, "r", encoding="utf-8") as f:
                    transcription_data = json.load(f)
                expected_raw_hash = transcription_data.get("_provenance", {}).get("expected_raw_artifact_hash")
            except Exception as e:
                raise CommandError(f"Failed to read derivative transcription file '{transcription_path}': {str(e)}") from e

        orchestrator = ProductionManufacturerOrchestrator()

        source_input = url_arg if url_arg else file_arg
        is_url = bool(url_arg)

        try:
            result = orchestrator.run_dry_run_pipeline(
                source_input=source_input,
                is_url=is_url,
                transcription_data=transcription_data,
                override_expected_hash=expected_raw_hash,
            )
        except Exception as e:
            raise CommandError(f"Production acquisition dry-run failed: {str(e)}") from e

        # Format human-readable operator console report
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(self.style.MIGRATE_HEADING("RIGARCHIVE PRODUCTION ACQUISITION DRY-RUN REPORT"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))
        self.stdout.write(f"Source Profile:     {result.source_id}")
        self.stdout.write(f"Publisher Locator:  {result.publisher_locator}")
        self.stdout.write(f"Acquisition Status: {result.acquisition_status}")
        self.stdout.write(f"Content Hash:       {result.snapshot_meta.content_hash}")
        self.stdout.write(f"Storage Path:       {result.snapshot_meta.storage_path}")
        self.stdout.write(f"Extracted Sets:     {result.total_extracted_sets}")
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 80))

        create_count = 0
        review_count = 0
        ineligible_count = 0

        for idx, cand_res in enumerate(result.candidate_results, 1):
            plan = cand_res.plan
            cand_id = cand_res.candidate_identity
            self.stdout.write(
                f"{idx:2d}. Model Code {cand_res.native_identifier:4s} | "
                f"{cand_id.manufacturer_name} {cand_id.vehicle_model_name} {cand_id.model_year} "
                f"{cand_id.trim_name or ''} [{cand_id.market}]"
            )
            self.stdout.write(
                f"    Status: {plan.eligibility_status.value} | "
                f"Action: {plan.planned_action.value} | "
                f"Basis: {plan.create_basis.value if plan.create_basis else 'None'}"
            )
            if plan.reasons:
                self.stdout.write(f"    Reasons: {', '.join(plan.reasons)}")

            if plan.eligibility_status.value == "eligible":
                create_count += 1
            elif plan.eligibility_status.value == "requires_review":
                review_count += 1
            else:
                ineligible_count += 1

        self.stdout.write(self.style.MIGRATE_HEADING("-" * 80))
        self.stdout.write(
            self.style.SUCCESS(
                f"Dry-Run Summary: Eligible (CREATE): {create_count} | "
                f"Requires Review: {review_count} | Ineligible: {ineligible_count}"
            )
        )
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 80))

        # Write optional machine-readable dry-run JSON report
        if options.get("output_json"):
            output_path = Path(options["output_json"]).resolve()
            json_report = {
                "source_id": result.source_id,
                "publisher_locator": result.publisher_locator,
                "acquisition_status": result.acquisition_status,
                "content_hash": result.snapshot_meta.content_hash,
                "storage_path": result.snapshot_meta.storage_path,
                "total_extracted_sets": result.total_extracted_sets,
                "summary": {
                    "eligible_create": create_count,
                    "requires_review": review_count,
                    "ineligible": ineligible_count,
                },
                "candidates": [
                    {
                        "native_identifier": cr.native_identifier,
                        "candidate_reference": cr.candidate_reference,
                        "eligibility_status": cr.plan.eligibility_status.value,
                        "planned_action": cr.plan.planned_action.value,
                        "create_basis": cr.plan.create_basis.value if cr.plan.create_basis else None,
                        "reasons": cr.plan.reasons,
                    }
                    for cr in result.candidate_results
                ],
                "errors": result.errors,
            }
            output_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Saved dry-run JSON report to '{output_path}'."))

        # Write optional executable review manifest JSON artifact
        if options.get("output_manifest"):
            manifest_path = Path(options["output_manifest"]).resolve()
            plans = [cr.plan for cr in result.candidate_results]
            native_map = {cr.plan.candidate_reference: cr.native_identifier for cr in result.candidate_results}

            ext_prov = {
                "raw_artifact_hash": result.snapshot_meta.content_hash,
                "raw_artifact_reference": result.snapshot_meta.storage_path,
                "extractor_id": "toyota_pressroom_extractor",
                "extractor_version": "0.1.0",
                "extraction_mode": "manually_verified_transcription",
            }

            manifest = build_review_manifest(
                source_id=result.source_id,
                raw_artifact_hash=result.snapshot_meta.content_hash,
                raw_artifact_reference=result.snapshot_meta.storage_path,
                extraction_provenance=ext_prov,
                plans=plans,
                native_identifiers=native_map,
            )

            manifest_dict = manifest_to_dict(manifest)
            manifest_path.write_text(json.dumps(manifest_dict, indent=2, ensure_ascii=False), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Saved executable review manifest to '{manifest_path}'."))
