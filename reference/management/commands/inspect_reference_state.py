"""
Safe Read-Only Reference State Inspection Management Command (RA-031 Part 2).

Provides a purpose-built, strictly read-only management command for inspecting canonical
Reference database state, entity counts, generation inventory, execution receipts,
and canonical correction records.

Guarantees 0 database writes, 0 file writes, and 0 ingestion execution.
"""

import json
from typing import Any, Dict, List

from django.core.management.base import BaseCommand
from reference.models import (
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class Command(BaseCommand):
    help = "Safely inspect canonical Reference repository state, database counts, and configuration inventory (STRICTLY READ-ONLY)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print summary of Reference domain entity counts.",
        )
        parser.add_argument(
            "--inventory",
            action="store_true",
            help="Report detailed configuration inventory for matching records.",
        )
        parser.add_argument(
            "--manufacturer",
            type=str,
            default=None,
            help="Filter by Manufacturer name or slug (e.g. 'Toyota').",
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Filter by VehicleModel name or slug (e.g. '4Runner').",
        )
        parser.add_argument(
            "--generation",
            type=str,
            default=None,
            help="Filter by Generation slug or name (e.g. 'fourth-generation').",
        )
        parser.add_argument(
            "--model-year",
            type=int,
            default=None,
            help="Filter by model year integer (e.g. 2009).",
        )
        parser.add_argument(
            "--trim",
            type=str,
            default=None,
            help="Filter by trim name (e.g. 'Sport Edition').",
        )
        parser.add_argument(
            "--engine",
            type=str,
            default=None,
            help="Filter by engine name (e.g. '4.7L V8').",
        )
        parser.add_argument(
            "--drivetrain",
            type=str,
            default=None,
            help="Filter by drivetrain (e.g. '4WD').",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include superseded or inactive VehicleDefinitions in output.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Format output as machine-readable JSON.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        is_json = options["json"]

        # Build base VehicleDefinition queryset based on filters
        qs = VehicleDefinition.objects.all()

        if not options["include_inactive"]:
            qs = qs.filter(is_active=True)

        if options["manufacturer"]:
            mfr_val = options["manufacturer"].strip()
            qs = qs.filter(generation__vehicle_model__manufacturer__name__iexact=mfr_val) | qs.filter(generation__vehicle_model__manufacturer__slug__iexact=mfr_val)

        if options["model"]:
            model_val = options["model"].strip()
            qs = qs.filter(generation__vehicle_model__name__iexact=model_val) | qs.filter(generation__vehicle_model__slug__iexact=model_val)

        if options["generation"]:
            gen_val = options["generation"].strip()
            qs = qs.filter(generation__slug__iexact=gen_val) | qs.filter(generation__name__iexact=gen_val)

        if options["model_year"]:
            qs = qs.filter(model_year=options["model_year"])

        if options["trim"]:
            qs = qs.filter(trim_name__iexact=options["trim"].strip())

        if options["engine"]:
            qs = qs.filter(engine_name__iexact=options["engine"].strip())

        if options["drivetrain"]:
            qs = qs.filter(drivetrain__iexact=options["drivetrain"].strip())

        qs = qs.order_by("model_year", "trim_name", "engine_name", "drivetrain")

        # Handle Summary Mode
        if options["summary"]:
            summary_data = {
                "active_vehicle_definitions": VehicleDefinition.objects.filter(is_active=True).count(),
                "inactive_superseded_vehicle_definitions": VehicleDefinition.objects.filter(is_active=False).count(),
                "total_vehicle_definitions": VehicleDefinition.objects.count(),
                "import_execution_receipts": ImportExecutionReceipt.objects.count(),
                "canonical_record_corrections": CanonicalRecordCorrection.objects.count(),
                "manufacturers": Manufacturer.objects.count(),
                "vehicle_models": VehicleModel.objects.count(),
                "generations": {
                    "active": Generation.objects.filter(is_active=True).count(),
                    "inactive": Generation.objects.filter(is_active=False).count(),
                    "total": Generation.objects.count(),
                },
                "filtered_matching_definitions": qs.count(),
            }

            if is_json:
                self.stdout.write(json.dumps(summary_data, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS("=== RIGARCHIVE REFERENCE STATE SUMMARY ==="))
                self.stdout.write(f"Active VehicleDefinitions:               {summary_data['active_vehicle_definitions']}")
                self.stdout.write(f"Inactive/Superseded VehicleDefinitions:  {summary_data['inactive_superseded_vehicle_definitions']}")
                self.stdout.write(f"Total VehicleDefinitions:                {summary_data['total_vehicle_definitions']}")
                self.stdout.write(f"Import Execution Receipts:               {summary_data['import_execution_receipts']}")
                self.stdout.write(f"Canonical Record Corrections:            {summary_data['canonical_record_corrections']}")
                self.stdout.write(f"Manufacturers:                           {summary_data['manufacturers']}")
                self.stdout.write(f"Vehicle Models:                          {summary_data['vehicle_models']}")
                self.stdout.write(f"Generations (Active / Inactive / Total): {summary_data['generations']['active']} / {summary_data['generations']['inactive']} / {summary_data['generations']['total']}")
                self.stdout.write(f"Filtered Matching VehicleDefinitions:    {summary_data['filtered_matching_definitions']}")
            return

        # Handle Inventory Mode / Default Inspection
        records: List[Dict[str, Any]] = []
        for vd in qs:
            records.append({
                "pk": vd.pk,
                "uuid": str(vd.uuid),
                "manufacturer": vd.generation.vehicle_model.manufacturer.name,
                "model": vd.generation.vehicle_model.name,
                "generation": vd.generation.name,
                "generation_slug": vd.generation.slug,
                "model_year": vd.model_year,
                "trim_name": vd.trim_name,
                "engine_name": vd.engine_name,
                "drivetrain": vd.drivetrain,
                "market": vd.market,
                "slug": vd.slug,
                "is_active": vd.is_active,
            })

        if is_json:
            self.stdout.write(json.dumps({"count": len(records), "records": records}, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f"=== RIGARCHIVE CANONICAL INVENTORY ({len(records)} matching records) ==="))
            for r in records:
                active_str = "ACTIVE" if r["is_active"] else "SUPERSEDED"
                self.stdout.write(
                    f"[{r['pk']}] {r['model_year']} {r['manufacturer']} {r['model']} {r['trim_name']} | "
                    f"Engine: {r['engine_name']} | Drive: {r['drivetrain']} | Market: {r['market']} | "
                    f"Status: {active_str} | Slug: {r['slug']}"
                )
