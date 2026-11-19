import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from reference.management.commands.export_configuration_logic import source_rows
from reference.models import FactoryBodyConfiguration, Generation, Manufacturer, VehicleDefinition, VehicleModel


@skipUnless(importlib.util.find_spec("openpyxl"), "optional XLSX export dependency is unavailable")
class ConfigurationLogicWorkbookTests(TestCase):
    def test_numbered_inventory_and_merged_options(self):
        from openpyxl import load_workbook

        manufacturer = Manufacturer.objects.create(name="Test Maker")
        model = VehicleModel.objects.create(manufacturer=manufacturer, name="Test Model")
        generation = Generation.objects.create(vehicle_model=model, name="First", start_year=2020)
        body = FactoryBodyConfiguration.objects.create(generation=generation, door_configuration="four-door")
        base = dict(generation=generation, model_year=2020, factory_body_configuration=body)
        beta = VehicleDefinition.objects.create(**base, trim_name="Beta", base_msrp="30000.50")
        alpha_4wd = VehicleDefinition.objects.create(**base, trim_name="Alpha", drivetrain="4WD", base_msrp="40000.00")
        alpha_2wd = VehicleDefinition.objects.create(**base, trim_name="Alpha", drivetrain="2WD")
        unknown = VehicleDefinition.objects.create(**base, trim_name="Aardvark")
        VehicleDefinition.objects.create(**base, trim_name="Alpha", drivetrain="AWD",
                                         base_msrp="20000.00", is_active=False)
        option_rows = {
            alpha_2wd.pk: [
                ("8-speed automatic", None, None, None, None, "Standard", "Transmission record"),
                (None, None, None, None, "Tow Package", "Optional", "Equipment record"),
            ],
        }
        module = "reference.management.commands.export_configuration_logic"
        with TemporaryDirectory() as directory, patch(f"{module}.catalogue_options") as load_options:
            from collections import defaultdict

            load_options.return_value = defaultdict(list, option_rows)
            path = Path(directory) / "logic.xlsx"
            args = dict(manufacturer="test maker", model="test model", year=2020, output=path)
            call_command("export_configuration_logic", **args)
            original = path.read_bytes()
            with self.assertRaisesMessage(CommandError, "Cannot create"):
                call_command("export_configuration_logic", **args)
            self.assertEqual(path.read_bytes(), original)
            workbook = load_workbook(path)

        inventory, options, logic, sources = workbook.worksheets
        self.assertEqual(inventory["A3"].value, "4 canonical configurations  ·  3 trim/body groups")
        data = list(inventory.iter_rows(min_row=6, values_only=True))
        expected = [beta, alpha_4wd, alpha_2wd, unknown]
        self.assertEqual([(row[0], row[7], row[8]) for row in data],
                         [(n, v.pk, v.slug) for n, v in enumerate(expected, 1)])
        self.assertEqual(data[0][5], "Unresolved")
        self.assertEqual([row[10] for row in data], [30000.50, 40000, None, None])
        self.assertEqual(inventory.auto_filter.ref, "A5:K9")
        self.assertFalse(inventory.merged_cells)
        self.assertFalse(options.merged_cells)
        self.assertEqual([cell[0].value for cell in options["A6:A10"]], [1, 2, 3, 3, 4])
        self.assertEqual({str(item) for item in logic.merged_cells.ranges},
                         {f"{column}8:{column}9" for column in "ABCDEFGHIJK"})
        self.assertEqual([cell[0].value for cell in logic["A6:A10"]], [1, 2, 3, None, 4])
        self.assertEqual((logic["L8"].value, logic["P9"].value), ("8-speed automatic", "Tow Package"))
        self.assertIsNone(logic["P8"].value)
        self.assertIsNone(logic["L9"].value)
        self.assertEqual(sources["E6"].value, 4)
        self.assertEqual(VehicleDefinition.objects.count(), 5)

    def test_year_comparison_counts_selected_models_without_counting_alternatives(self):
        review = {
            "observed_on": "2026-11-18", "scope": "Reviewed scope", "sources": [],
            "configurations": [
                {"selected_toyota_model": {"trim": "SR", "cab": "Double Cab", "bed": "5-ft"},
                 "alternate_toyota_models": [{"code": "7547"}]},
                {"manufacturer_marketed_trim": "SR", "cab": "Double Cab", "bed": "5-ft"},
            ],
        }
        raw = json.dumps(review).encode()
        receipt = SimpleNamespace(raw_artifact_hash="sha256:" + hashlib.sha256(raw).hexdigest(),
                                  raw_artifact_reference="review.json")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            path.write_bytes(raw)
            rows = list(source_rows(2025, 2, 1, path, {1: receipt}))
        self.assertEqual(rows[1][4:6], (2, 1))
        self.assertEqual(rows[2][4:6], (0, 0))
