import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

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
        expected = [beta, alpha_2wd, alpha_4wd, unknown]
        self.assertEqual([(row[0], row[7], row[8]) for row in data],
                         [(n, v.pk, v.slug) for n, v in enumerate(expected, 1)])
        self.assertEqual(data[0][5], "Unresolved")
        self.assertEqual([row[10] for row in data], [30000.50, None, 40000, None])
        self.assertEqual(inventory.auto_filter.ref, "A5:K9")
        self.assertFalse(inventory.merged_cells)
        self.assertFalse(options.merged_cells)
        self.assertEqual([cell[0].value for cell in options["A6:A10"]], [1, 2, 2, 3, 4])
        self.assertEqual({str(item) for item in logic.merged_cells.ranges},
                         {f"{column}7:{column}8" for column in "ABCDEFGHIJK"})
        self.assertEqual([cell[0].value for cell in logic["A6:A10"]], [1, 2, None, 3, 4])
        self.assertEqual((logic["L7"].value, logic["P8"].value), ("8-speed automatic", "Tow Package"))
        self.assertIsNone(logic["P7"].value)
        self.assertIsNone(logic["L8"].value)
        self.assertEqual(sources["E6"].value, 4)
        self.assertEqual(VehicleDefinition.objects.count(), 5)
