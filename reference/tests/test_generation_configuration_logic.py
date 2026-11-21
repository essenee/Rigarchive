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
from reference.models import (
    Engine, FactoryBodyConfiguration, Generation, Manufacturer, NominalBedLength, VehicleDefinition, VehicleModel,
)


class GenerationConfigurationLogicTests(TestCase):
    def test_source_descriptor_includes_scope_and_preserves_reviewed_document_range(self):
        from reference.configuration_logic_provenance import source_descriptor

        self.assertEqual(source_descriptor(2024, "2024 Tacoma Product Information", organization="Toyota",
                                           url="https://example.com/product-information.pdf"),
                         "2024 Toyota Tacoma Product Information PDF")
        self.assertEqual(source_descriptor(2025, "2024–2025 Toyota Full-Line Pricing", organization="Toyota",
                                           url="https://example.com/pricing.pdf"),
                         "2024–2025 Toyota Full-Line Pricing PDF")
        self.assertEqual(source_descriptor(2024, "Toyota Full-Line Pricing", organization="Toyota",
                                           reviewed="2024–2025 Toyota Full-Line Pricing (mirrored text)"),
                         "2024–2025 Toyota Full-Line Pricing (mirrored text)")

    def test_provenance_groups_reviewed_support_and_keeps_lineage_separate(self):
        from reference.configuration_logic_provenance import provenance

        citations = [
            {"assertion": "Model code", "source_id": "T24-S", "locator": "p. 1"},
            {"assertion": "Transmission", "source_id": "T24-S", "locator": "p. 1"},
            {"assertion": "Model code", "source_id": "T24-S", "locator": "p. 1"},
            {"assertion": "Engine output", "source_id": "T24-P", "locator": "p. 1"},
        ]
        expected = "Model code/Transmission: T24-S p. 1; Engine output: T24-P p. 1; Lineage: Authoring receipt 1"
        self.assertEqual(provenance(citations, {"T24-S", "T24-P"}, lineage="Authoring receipt 1"), expected)
        self.assertEqual(provenance(citations, {"T24-S"}),
                         "Model code/Transmission: T24-S p. 1; Evidence gap: Unresolved manufacturer citation")

    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Example")
        model = VehicleModel.objects.create(manufacturer=maker, name="Truck")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Fourth", generation_number=4,
                                                   start_year=2024)
        short_bed = NominalBedLength.objects.create(designation="5-ft")
        long_bed = NominalBedLength.objects.create(designation="6-ft")
        body = FactoryBodyConfiguration.objects.create(generation=cls.generation, cab_configuration="double-cab",
                                                        bed_length=short_bed)
        other_body = FactoryBodyConfiguration.objects.create(generation=cls.generation, cab_configuration="xtracab",
                                                              bed_length=long_bed)
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
                base_msrp=price, engine=engine, engine_name=engine.name,
                factory_body_configuration=other_body if price == 8 else body,
            )

    def test_generation_draft_order_identity_and_provenance(self):
        original = list(VehicleDefinition.objects.order_by("pk").values())
        draft = generation_draft(select_generation("example", "truck", str(self.generation.pk)))
        self.assertEqual(draft, generation_draft(self.generation))
        self.assertEqual([s.name for s in draft.sheets], ["MY2026", "MY2025", "MY2024", "Source References"])
        latest, _, research, sources = draft.sheets
        headers = latest.rows[3]
        self.assertNotIn("Cab", headers)
        self.assertNotIn("Nominal Bed", headers)
        price = headers.index("Base MSRP")
        self.assertEqual(headers[price - 1], "Transmission")
        self.assertEqual(latest.hidden_columns, ())
        self.assertEqual([row[price] for row in latest.rows[4:]], [8, 10, None, 20])
        self.assertEqual([row[4] for row in latest.rows[4:]], ["XtraCab, 6-ft Bed", *(["Double Cab, 5-ft Bed"] * 3)])
        self.assertEqual([row[3] for row in latest.rows[4:]], ["Zulu", "Zulu", "Zulu", "Alpha"])
        for row in latest.rows[4:]:
            vehicle = VehicleDefinition.objects.get(pk=row[1])
            self.assertEqual(row[headers.index("Slug")], vehicle.slug)
            self.assertEqual((row[3], row[headers.index("Registered Engine Name")]), (vehicle.trim_name, "2.0L I4"))
            self.assertIsNone(row[2])
        self.assertIn("awaiting research", research.rows[1][0])
        self.assertEqual(research.rows[3:], (headers,))
        self.assertEqual([row[0] for row in sources.rows[4:]], [2026, 2025, 2024])
        self.assertEqual(sources.rows[-1][7], "Evidence gap")
        self.assertEqual(list(VehicleDefinition.objects.order_by("pk").values()), original)

    def test_generation_source_aliases_match_documents_across_years(self):
        source = {"title": "Toyota Truck Pricing", "organization": "Toyota",
                  "url": "https://toyota.com/truck/pricing.pdf",
                  "revision_date": "2025-10-01", "evidence_id": "TT-P"}

        def build(source_2025):
            receipts = {
                vehicle.pk: SimpleNamespace(pk=vehicle.model_year, raw_artifact_hash=f"review-{vehicle.model_year}",
                                            raw_artifact_reference=f"{vehicle.model_year}.json",
                                            resolution_snapshot_json={"observation": {"engine_options": []}},
                                            engine_variant=vehicle.engine.internal_variant_key)
                for vehicle in self.generation.vehicle_definitions.filter(engine__isnull=False)
            }
            reviews = {
                "2025.json": {"observed_on": "2025-11-01", "sources": [{**source_2025, "observation": "2025 page"}]},
                "2026.json": {"observed_on": "2025-11-02", "sources": [{**source, "observation": "2026 page"}]},
            }

            def observation(receipt, review):
                return {"selected_toyota_model": {
                    "variant": receipt.engine_variant,
                    "citations": [{"assertion": "MSRP", "source_id": "TT-P", "locator": f"p. {receipt.pk - 2024}"}],
                }}

            with patch("reference.configuration_logic.authored_observations",
                       side_effect=lambda configs: {v.pk: receipts[v.pk] for v in configs}), patch(
                "reference.configuration_logic.pinned_review",
                side_effect=lambda receipt: reviews[receipt.raw_artifact_reference],
            ), patch("reference.configuration_logic.verified_observation", side_effect=observation):
                return generation_draft(self.generation)

        draft = build(source)
        older, newer = draft.sheets[1], draft.sheets[0]
        self.assertIn("MSRP: TT-P p. 1", older.rows[4][-1])
        self.assertIn("MSRP: TT-P p. 2", newer.rows[4][-1])
        entry, = [row for row in draft.sheets[-1].rows[4:] if row[6] == "TT-P"]
        self.assertEqual(entry[5], "2025–2026 Toyota Truck Pricing PDF")
        self.assertIn("MY2025 (reviewed 2025-11-01)", entry[8])
        self.assertIn("MY2026 (reviewed 2025-11-02)", entry[8])
        described = build({**source, "descriptor": "Toyota Truck Pricing Schedule PDF"}).sheets[-1]
        reviewed_entry, = [row for row in described.rows[4:] if row[6] == "TT-P"]
        self.assertEqual(reviewed_entry[5], "Toyota Truck Pricing Schedule PDF")
        for conflict in ({"url": "https://toyota.com/truck/other.pdf"}, {"revision_date": "2025-09-01"}):
            with self.subTest(conflict=conflict):
                with self.assertRaisesMessage(CommandError, "Conflicting Source References identity for Evidence ID TT-P"):
                    build({**source, **conflict})

    def test_generation_without_body_variants_keeps_cells_blank_and_hides_column(self):
        from reference.configuration_logic_google import desired_values, sheet_requests

        model = VehicleModel.objects.create(manufacturer=self.generation.vehicle_model.manufacturer, name="SUV")
        generation = Generation.objects.create(vehicle_model=model, name="Sixth", generation_number=6, start_year=2025)
        engine = Engine.objects.get(engine_code="EX")
        VehicleDefinition.objects.create(generation=generation, model_year=2025, trim_name="SR5",
                                         drivetrain="4WD", engine=engine, engine_name=engine.name)
        table = generation_draft(generation).sheets[0]
        self.assertEqual(table.hidden_columns, (4,))
        self.assertEqual(table.rows[3][4], "Body Configuration")
        self.assertIsNone(table.rows[4][4])
        requests = sheet_requests(table, 1, None, None, 0)
        hidden = [request["updateDimensionProperties"] for request in requests
                  if request.get("updateDimensionProperties", {}).get("properties", {}).get("hiddenByUser")]
        self.assertEqual([request["range"]["startIndex"] for request in hidden], [4])
        values = desired_values(table)
        self.assertIn("SCAN(", values[3, 0]["formulaValue"])
        self.assertNotIn((4, 0), values)

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
                                     "citations": [{"assertion": "Model code", "source_id": "EX-L", "locator": "p. 2"}],
                                     "variant": vehicle.engine.internal_variant_key},
            "alternate_toyota_models": [{"code": "0102", "transmission": "Manual",
                                        "variant": "manual-output", "price": "2.00"}],
            "engine_options": [],
        }
        artifact = {
            "record_type": "human-reviewed-factory-observations", "configurations": [observation],
            "sources": [{"title": "Independent source title", "url": "https://example.com/source",
                         "evidence_id": "EX-L"}],
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
            self.assertEqual(sources[-1][5], "2025 Independent source title")
            self.assertEqual(sources[-1][6:8], ("EX-L", "Original bytes not verified"))
            self.assertIn(receipt.raw_artifact_hash, sources[-1][8])
            primary, alternative = sheet.rows[4:]
            self.assertEqual((primary[2], primary[10], primary[14]), ("0101", "2.0L I4", "Automatic"))
            self.assertEqual((alternative[1], *alternative[14:18]),
                             (vehicle.pk, "Manual", "manual-output", "0102", 2))
            self.assertIsNone(alternative[9])
            self.assertEqual(primary[-1], "Model code: EX-L p. 2; Lineage: Authoring receipt 8")
            self.assertTrue(alternative[-1].startswith("Evidence gap:"))
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
            self.assertEqual(workbook["MY2026"]["K5"].value, 8)
            self.assertEqual(workbook["MY2024"].max_row, 4)
            self.assertEqual(workbook["MY2026"].freeze_panes, "A5")
            call_command("publish_configuration_logic", **args, dry_run=True, stdout=Mock())
