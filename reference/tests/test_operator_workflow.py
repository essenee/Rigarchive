"""
Tests for Operator Workflow Hardening Management Commands (RA-040).

Verifies plan_generation_population non-canonical-writing safety, file output handling,
deterministic manifest generation, and inspect_reference_state --by-year grouping logic.
"""

import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from reference.models import (
    CanonicalRecordCorrection,
    Generation,
    ImportExecutionReceipt,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class OperatorWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.mfr, _ = Manufacturer.objects.get_or_create(name="Toyota", defaults={"is_active": True})
        self.vmodel, _ = VehicleModel.objects.get_or_create(manufacturer=self.mfr, name="4Runner", defaults={"is_active": True})
        self.gen5, _ = Generation.objects.get_or_create(
            vehicle_model=self.vmodel,
            start_year=2010,
            defaults={"name": "Fifth Generation", "end_year": 2024, "is_active": True},
        )
        self.vd, _ = VehicleDefinition.objects.get_or_create(
            generation=self.gen5,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
            defaults={"is_active": True},
        )

    def test_plan_generation_population_performs_zero_db_writes(self) -> None:
        """1 & 2. plan_generation_population performs zero canonical DB writes and zero receipt/correction writes."""
        vd_count_before = VehicleDefinition.objects.count()
        receipt_count_before = ImportExecutionReceipt.objects.count()
        correction_count_before = CanonicalRecordCorrection.objects.count()

        out = StringIO()
        call_command(
            "plan_generation_population",
            manufacturer="Toyota",
            model="4Runner",
            market="US",
            start_year=2020,
            end_year=2020,
            stdout=out,
        )

        self.assertEqual(VehicleDefinition.objects.count(), vd_count_before)
        self.assertEqual(ImportExecutionReceipt.objects.count(), receipt_count_before)
        self.assertEqual(CanonicalRecordCorrection.objects.count(), correction_count_before)
        self.assertIn("RIGARCHIVE POPULATION BATCH REVIEW MANIFEST", out.getvalue())

    def test_plan_generation_population_file_output_and_overwrite_protection(self) -> None:
        """3. Explicit output path receives manifest; existing file is not silently overwritten without --overwrite."""
        with TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "manifest.json"

            # First run: writes manifest file
            call_command(
                "plan_generation_population",
                manufacturer="Toyota",
                model="4Runner",
                market="US",
                model_year=2020,
                output=str(out_file),
            )
            self.assertTrue(out_file.exists())
            with open(out_file, "r") as f:
                data = json.load(f)
            self.assertEqual(data["manufacturer_name"], "Toyota")
            self.assertEqual(data["vehicle_model_name"], "4Runner")
            self.assertEqual(data["start_year"], 2020)
            self.assertIn("batch_manifest_hash", data)

            # Second run without --overwrite: raises CommandError
            with self.assertRaises(CommandError):
                call_command(
                    "plan_generation_population",
                    manufacturer="Toyota",
                    model="4Runner",
                    market="US",
                    model_year=2020,
                    output=str(out_file),
                )

            # Third run with --overwrite: succeeds
            out2 = StringIO()
            call_command(
                "plan_generation_population",
                manufacturer="Toyota",
                model="4Runner",
                market="US",
                model_year=2020,
                output=str(out_file),
                overwrite=True,
                stdout=out2,
            )
            self.assertIn("Saved PopulationBatchManifest", out2.getvalue())

    def test_plan_generation_population_invalid_arguments(self) -> None:
        """4. Invalid manufacturer/model/year arguments fail clearly."""
        with self.assertRaises(CommandError):
            call_command("plan_generation_population", manufacturer="Toyota", model="4Runner")

        with self.assertRaises(CommandError):
            call_command(
                "plan_generation_population",
                manufacturer="Toyota",
                model="4Runner",
                start_year=2025,
                end_year=2020,
            )

    def test_inspect_reference_state_by_year(self) -> None:
        """5. inspect_reference_state --by-year groups matching records by model year without DB writes."""
        out = StringIO()
        call_command(
            "inspect_reference_state",
            model="4Runner",
            by_year=True,
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("INVENTORY BY MODEL YEAR", output)
        self.assertIn("Year 2020: 1 active / 0 inactive", output)

    def test_inspect_reference_state_by_year_json(self) -> None:
        """6. inspect_reference_state --by-year --json returns machine-readable JSON structure."""
        out = StringIO()
        call_command(
            "inspect_reference_state",
            model="4Runner",
            by_year=True,
            json=True,
            stdout=out,
        )

        data = json.loads(out.getvalue())
        self.assertIn("years", data)
        self.assertEqual(data["total_records"], 1)
        self.assertEqual(data["years"][0]["model_year"], 2020)
        self.assertEqual(data["years"][0]["active_count"], 1)
