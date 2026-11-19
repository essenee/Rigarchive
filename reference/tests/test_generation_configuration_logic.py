from decimal import Decimal
from io import StringIO
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from reference.body_identity import canonical_json
from reference.configuration_logic import HEADERS, draft_year, generation_draft, select_generation
from reference.models import Engine, FactoryBodyConfiguration, Generation, Manufacturer, VehicleDefinition, VehicleModel


class GenerationConfigurationLogicTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Example")
        model = VehicleModel.objects.create(manufacturer=maker, name="Truck")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Fourth", generation_number=4,
                                                   start_year=2024)
        body = FactoryBodyConfiguration.objects.create(generation=cls.generation, cab_configuration="double-cab")
        engine = Engine.objects.create(
            manufacturer=maker, engine_code="EX", name="2.0L I4", engine_displacement_liters=Decimal("2.0"),
            engine_cylinders=4, engine_aspiration="turbocharged", fuel_type="gasoline", electrification_type="none",
        )
        VehicleDefinition.objects.create(generation=cls.generation, model_year=2024, trim_name="Legacy")
        for year, trim, drivetrain, price in (
            (2026, "Zulu", "2WD", 10), (2026, "Zulu", "4WD", 8),
            (2026, "Zulu", "AWD", None), (2026, "Alpha", "4WD", 20), (2025, "Beta", "2WD", 3),
        ):
            VehicleDefinition.objects.create(
                generation=cls.generation, model_year=year, trim_name=trim, drivetrain=drivetrain,
                base_msrp=price, engine=engine, engine_name=engine.name, factory_body_configuration=body,
            )

    def test_generation_draft_order_identity_and_provenance(self):
        original = list(VehicleDefinition.objects.order_by("pk").values())
        draft = generation_draft(select_generation("example", "truck", str(self.generation.pk)))
        self.assertEqual(draft, generation_draft(self.generation))
        self.assertEqual([s.name for s in draft.sheets], ["MY2026", "MY2025", "MY2024", "Source References"])
        latest, _, research, sources = draft.sheets
        self.assertEqual([row[11] for row in latest.rows[4:]], [8, 10, None, 20])
        self.assertEqual([row[3] for row in latest.rows[4:]], ["Zulu", "Zulu", "Zulu", "Alpha"])
        for row in latest.rows[4:]:
            vehicle = VehicleDefinition.objects.get(pk=row[1])
            self.assertEqual(row[12], vehicle.slug)
            self.assertEqual((row[3], row[5], row[10]), (vehicle.trim_name, "Double Cab", "2.0L I4"))
            self.assertIsNone(row[2])
        self.assertIn("awaiting research", research.rows[1][0])
        self.assertEqual(research.rows[3:], (HEADERS,))
        self.assertEqual([row[0] for row in sources.rows[4:]], [2026, 2025, 2024])
        self.assertEqual(sources.rows[-1][7], "Evidence gap")
        self.assertEqual(list(VehicleDefinition.objects.order_by("pk").values()), original)

    def test_pending_reservation_inspection_is_local_and_read_only(self):
        before = list(VehicleDefinition.objects.order_by("pk").values())
        draft = generation_draft(self.generation)
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch(
            "reference.management.commands.publish_configuration_logic.connect",
        ) as connect:
            state_directory = Path(directory, ".configuration-logic")
            state_directory.mkdir()
            registry = state_directory / f"{draft.key}.json"
            payload = json.dumps({"schema": 1, "generation": draft.key, "mode": "draft",
                                  "spreadsheet": None, "sheets": {}})
            registry.write_text(payload)
            output = StringIO()
            args = dict(manufacturer="Example", model="Truck", generation=str(self.generation.pk))
            call_command("publish_configuration_logic", **args, inspect_reservation=True, stdout=output)
            for label in ("pending creation", "spreadsheet ID: no", "publication fingerprints: no",
                          draft.title, "--recover-id", "--release-no-spreadsheet", "cannot guarantee"):
                self.assertIn(label, output.getvalue())
            self.assertEqual(registry.read_text(), payload)
            self.assertEqual(list(state_directory.iterdir()), [registry])
            connect.assert_not_called()
        self.assertEqual(list(VehicleDefinition.objects.order_by("pk").values()), before)

    def test_release_requires_a_separate_initialization_command(self):
        before = list(VehicleDefinition.objects.order_by("pk").values())
        draft = generation_draft(self.generation)
        publisher = "reference.management.commands.publish_configuration_logic"
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch(
            f"{publisher}.connect",
        ) as connect, patch(f"{publisher}.create") as create, patch(f"{publisher}.publish", return_value=[]):
            state_directory = Path(directory, ".configuration-logic")
            state_directory.mkdir()
            registry = state_directory / f"{draft.key}.json"
            registry.write_text(json.dumps({"schema": 1, "generation": draft.key, "mode": "draft",
                                            "spreadsheet": None, "sheets": {}}))
            args = dict(manufacturer="Example", model="Truck", generation=str(self.generation.pk), stdout=StringIO())
            with self.assertRaisesMessage(CommandError, "--confirm-recovery"):
                call_command("publish_configuration_logic", **args, release_no_spreadsheet=True)
            call_command("publish_configuration_logic", **args, release_no_spreadsheet=True, confirm_recovery=True)
            with self.assertRaisesMessage(CommandError, "separate --publish --initialize"):
                call_command("publish_configuration_logic", **args, publish=True)
            connect.assert_not_called()
            create.assert_not_called()
            create.return_value = {"spreadsheet": "mock-existing-id"}
            call_command("publish_configuration_logic", **args, publish=True, initialize=True)
            create.assert_called_once()
        self.assertEqual(list(VehicleDefinition.objects.order_by("pk").values()), before)

    def test_research_draft_interface_is_independent_of_database_insertion(self):
        example = (1, None, "ABC", "Demo")
        sheet, _ = draft_year("Research", 2024, (), authored_rows=[example])
        self.assertEqual(sheet.rows[4:], (example,))
        self.assertIn("supplied research", sheet.rows[1][0])

    def test_receipt_pinned_alternative_does_not_change_canonical_engine(self):
        vehicle = VehicleDefinition.objects.get(generation=self.generation, model_year=2025)
        observation = {
            "selected_toyota_model": {"code": "0101", "transmission": "Automatic",
                                     "variant": vehicle.engine.internal_variant_key},
            "alternate_toyota_models": [{"code": "0102", "transmission": "Manual",
                                        "variant": "manual-output", "price": "2.00"}],
            "engine_options": [],
        }
        artifact = {
            "record_type": "human-reviewed-factory-observations", "configurations": [observation],
            "sources": [{"title": "Independent source title", "url": "https://example.com/source"}],
        }
        raw = json.dumps(artifact).encode()
        snapshot = {"observation": observation}
        snapshot["snapshot_hash"] = "sha256:" + hashlib.sha256(canonical_json(snapshot).encode()).hexdigest()
        receipt = SimpleNamespace(pk=8, raw_artifact_reference="evidence.json", resolution_snapshot_json=snapshot,
                                  raw_artifact_hash="sha256:" + hashlib.sha256(raw).hexdigest())
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch(
            "reference.configuration_logic.authored_observations", return_value={vehicle.pk: receipt},
        ):
            Path(directory, "evidence.json").write_bytes(raw)
            sheet, sources = draft_year("Research", 2025, [vehicle])
            self.assertEqual(sheet.rows[0], ("Research",))
            self.assertEqual(sources[-1][2], "Independent source title")
            primary, alternative = sheet.rows[4:]
            self.assertEqual((primary[2], primary[10], primary[14]), ("0101", "2.0L I4", "Automatic"))
            self.assertEqual((alternative[1], *alternative[14:18]),
                             (vehicle.pk, "Manual", "manual-output", "0102", 2))
            self.assertIsNone(alternative[9])
            snapshot["snapshot_hash"] = "invalid"
            rejected, _ = draft_year("Research", 2025, [vehicle])
            self.assertEqual(len(rejected.rows), 5)
            self.assertIsNone(rejected.rows[4][2])

    @skipUnless(importlib.util.find_spec("openpyxl"), "optional XLSX export dependency is unavailable")
    def test_xlsx_and_offline_plan(self):
        from openpyxl import load_workbook

        with TemporaryDirectory() as directory:
            path = Path(directory) / "logic.xlsx"
            args = dict(manufacturer="Example", model="Truck", generation=str(self.generation.pk))
            call_command("export_configuration_logic", **args, output=path)
            workbook = load_workbook(path)
            self.assertEqual(workbook.sheetnames, ["MY2026", "MY2025", "MY2024", "Source References"])
            self.assertEqual(workbook["MY2026"]["L5"].value, 8)
            self.assertEqual(workbook["MY2024"].max_row, 4)
            self.assertEqual(workbook["MY2026"].freeze_panes, "A5")
            call_command("publish_configuration_logic", **args, dry_run=True, stdout=Mock())
