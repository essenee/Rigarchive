from copy import deepcopy
from dataclasses import replace
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch
import json

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from reference.configuration_logic_changelog import generated_rows
from reference.configuration_logic_google import entered, read_registry, remote_values
from reference.configuration_logic_inactive import MANUAL_TRIMS, canonical_status, plan_inactive, verify_inactive
from reference.configuration_logic_layout import INACTIVE_INDEX, column_order
from reference.configuration_logic_revisions import (
    capture_remote, current_draft, load_layout, load_revision, plan_updates, revision_root, save_remote,
)
from reference.tests import test_configuration_logic_revisions as b2


class InactiveTests(SimpleTestCase):
    response = b2.WorkingRevisionTests.response
    data = b2.WorkingRevisionTests.data

    def setUp(self):
        b2.WorkingRevisionTests.setUp(self)
        self.remote["MY2026"] = deepcopy(self.remote["MY2025"])
        sheet = self.remote["MY2026"]
        sheet["properties"].update(sheetId=4, index=3, title="MY2026")
        sheet["properties"]["gridProperties"].update(rowCount=100, columnCount=26)
        for name in ("MY2024", "MY2025"):
            self.remote[name]["properties"]["gridProperties"].update(rowCount=100, columnCount=26)
        self.state["sheets"]["MY2026"] = {"id": 4, "rows": 28, "columns": 21, "fingerprint": "unused"}
        self.path.write_text(json.dumps(self.state))
        self.draft = replace(self.draft, sheets=(*self.draft.sheets, replace(self.draft.sheets[0], name="MY2026")))
        attrs = ("Base", "Double Cab, 5-ft Bed", "Double Cab", "5-ft", "4WD", "T24A-FTS",
                 "i-force-278hp", "Turbo")
        self.vehicles = {}
        self.data("MY2026")[4:] = []
        for i in range(24):
            pk = i + 200
            vehicle = self.vehicle(pk, 2026, f"Trim {i}", True)
            row = (i + 1, pk, None, *vehicle.attrs, 500, vehicle.slug, "United States", *([None] * 7))
            encoded = {"values": [{"userEnteredValue": entered(v)} if entered(v) else {} for v in row]}
            self.data("MY2026").append(encoded)
        v = self.vehicle(21, 2025, "Base", True)
        v.attrs = (attrs[0], None, None, None, "4WD", None, None, None)
        v.slug = "base-truck"
        self.data("MY2025")[4]["values"][13] = {"userEnteredValue": entered("United States")}
        for pk, trim in MANUAL_TRIMS.items():
            self.vehicle(pk, 2026, trim, False)
        attributes = patch("reference.configuration_logic_inactive.canonical_attributes", side_effect=lambda v: v.attrs)
        attributes.start()
        self.addCleanup(attributes.stop)
        self.capture(enroll=True)

    def vehicle(self, pk, year, trim, active):
        attrs = (trim, "Double Cab, 5-ft Bed", "Double Cab", "5-ft", "4WD", "T24A-FTS",
                 "i-force-278hp" if active else "i-force-270hp", "Turbo")
        vehicle = SimpleNamespace(pk=pk, model_year=year, market="US", drivetrain="4WD", is_active=active,
                                  attrs=attrs, slug=f"truck-{pk}", base_msrp=500,
                                  get_market_display=lambda: "United States")
        self.vehicles[pk] = vehicle
        return vehicle

    def capture(self, *, enroll=False, operation="capture"):
        prior = load_revision(self.state, self.path)
        remote = capture_remote(self.api, self.draft, self.state)
        revision = save_remote(self.api, self.draft, self.path, self.state, remote, prior, enroll=enroll,
                               operation=operation)
        self.state = read_registry(self.path, self.draft.key)
        return revision

    def apply_mock(self, requests):
        by_id = {s["properties"]["sheetId"]: s for s in self.remote.values()}
        for request in requests:
            if "insertDimension" in request:
                span = request["insertDimension"]["range"]
                sheet = by_id[span["sheetId"]]
                sheet["properties"]["gridProperties"]["columnCount"] += 1
                for row in sheet["data"][0]["rowData"]:
                    if len(row["values"]) > span["startIndex"]:
                        row["values"].insert(span["startIndex"], {})
            elif "setBasicFilter" in request:
                spec = request["setBasicFilter"]["filter"]
                by_id[spec["range"]["sheetId"]]["basicFilter"] = deepcopy(spec)
            else:
                update = request["updateCells"]
                grid = by_id[update["start"]["sheetId"]]["data"][0]["rowData"]
                for r, line in enumerate(update["rows"], update["start"]["rowIndex"]):
                    while len(grid) <= r:
                        grid.append({"values": []})
                    cells = grid[r]["values"]
                    column = update["start"]["columnIndex"]
                    while len(cells) < column + len(line["values"]):
                        cells.append({})
                    for i, value in enumerate(line["values"], column):
                        cells[i].pop("userEnteredValue", None)
                        cells[i].update(value)

    def test_canonical_link_and_no_guess(self):
        row = (1, 200, None, *self.vehicles[200].attrs, 500, "truck-200", "United States")
        self.assertIsNone(canonical_status(row, self.vehicles, 2026))
        self.vehicles[200].is_active = False
        self.assertEqual(canonical_status(row, self.vehicles, 2026), "Yes")
        self.assertIsNone(canonical_status((1, None, *row[2:]), self.vehicles, 2026))
        with self.assertRaisesMessage(CommandError, "Stale or ambiguous"):
            canonical_status(row, self.vehicles, 2025)
        with self.assertRaisesMessage(CommandError, "outside the registered generation or missing"):
            canonical_status(row, {}, 2026)

    def test_reviewed_permutation_keeps_row_ids_and_rejects_changed_values(self):
        snapshot = load_revision(self.state, self.path)
        layout = load_layout(self.state, self.path)
        original = layout["sheets"]["MY2026"]["rows"]
        self.data("MY2026")[4:6] = reversed(self.data("MY2026")[4:6])
        def register():
            return save_remote(self.api, self.draft, self.path, self.state,
                               capture_remote(self.api, self.draft, self.state), snapshot,
                               approved_row_permutation="MY2026")
        price = self.data("MY2026")[4]["values"][11]["userEnteredValue"]
        price["numberValue"] = 501
        with self.assertRaisesMessage(CommandError, "changed values"):
            register()
        price["numberValue"] = 500
        revision = register()
        state = read_registry(self.path, self.draft.key)
        rows = load_layout(state, self.path)["sheets"]["MY2026"]["rows"]
        self.assertEqual([row["id"] for row in rows], [original[1]["id"], original[0]["id"],
                                                       *(row["id"] for row in original[2:])])
        self.assertNotIn(revision, generated_rows(self.path, state))
        self.api.batchUpdate.assert_not_called()

    def test_migration_refresh_and_revision_history(self):
        initial = self.state["working_revision"]["id"]
        initial_file = revision_root(self.path) / initial / "manifest.json"
        initial_bytes = initial_file.read_bytes()
        original_ids = load_layout(self.state, self.path)["sheets"]["MY2026"]["rows"]
        self.data("MY2026")[4]["values"][11]["userEnteredFormat"] = {"wrapStrategy": "WRAP"}
        before = deepcopy(self.remote)
        requests, expected = plan_inactive(self.draft, before, self.vehicles, migrate=True)
        self.apply_mock(requests)
        verify_inactive(before, self.remote, expected)
        revision = self.capture(operation="inactive-migration")
        layout = load_layout(self.state, self.path)
        self.assertEqual(layout["schema"], 2)
        self.assertEqual(layout["sheets"]["MY2026"]["rows"][:24], original_ids)
        self.assertEqual(len(layout["sheets"]["MY2026"]["rows"]), 27)
        self.assertEqual(initial_bytes, initial_file.read_bytes())
        self.assertIn(revision, generated_rows(self.path, self.state))
        for name in ("MY2024", "MY2025", "MY2026"):
            self.assertEqual(column_order(name, self.remote[name])[12], INACTIVE_INDEX)
        statuses = {r: cell["stringValue"] for (r, c), cell in remote_values(self.remote["MY2026"]).items() if c == 12}
        self.assertEqual(statuses, {3: "Inactive", 28: "Yes", 29: "Yes", 30: "Yes"})
        self.draft = current_draft(self.generation, self.path, self.state)
        self.assertEqual(plan_inactive(self.draft, self.remote, self.vehicles)[0], [])
        before = deepcopy(self.remote)
        self.vehicles[1170].is_active = True
        requests, expected = plan_inactive(self.draft, before, self.vehicles)
        self.assertEqual(len(requests), 1)
        self.apply_mock(requests)
        verify_inactive(before, self.remote, expected)
        with self.assertRaisesMessage(CommandError, "controlled refresh"):
            self.capture()
        refreshed = self.capture(operation="inactive-refresh")
        self.assertNotIn(refreshed, generated_rows(self.path, self.state))
        self.assertEqual(plan_inactive(self.draft, self.remote, self.vehicles)[0], [])
        self.assertEqual(load_layout(self.state, self.path)["logical_content_hash"], layout["logical_content_hash"])
        self.assertEqual(initial_bytes, initial_file.read_bytes())

    def test_unexpected_post_state_stops_and_moved_field_is_machine_managed(self):
        before = deepcopy(self.remote)
        requests, expected = plan_inactive(self.draft, before, self.vehicles, migrate=True)
        self.apply_mock(requests[:-1])
        with self.assertRaisesMessage(CommandError, "differs from the reviewed"):
            verify_inactive(before, self.remote, expected)
        self.remote = deepcopy(before)
        self.apply_mock(requests)
        self.capture(operation="inactive-migration")
        self.draft = current_draft(self.generation, self.path, self.state)
        for line in self.data("MY2026"):
            cells = line["values"]
            cells.extend({} for _ in range(22 - len(cells)))
            cells.insert(16, cells.pop(12))
        self.capture()
        layout = load_layout(self.state, self.path)
        status = next(r for r in layout["sheets"]["MY2026"]["rows"] if r["row"] == 29)
        with self.assertRaisesMessage(CommandError, "machine-managed"):
            plan_updates(self.draft, self.state, self.remote, [
                {"sheet_id": 4, "row_id": status["id"], "field_id": "configuration.inactive", "before": "Yes", "value": None},
            ], layout, 2)
        self.vehicles[1170].is_active = True
        requests, _ = plan_inactive(self.draft, self.remote, self.vehicles)
        self.assertEqual(requests[0]["updateCells"]["start"]["columnIndex"], 16)

    def test_preview_stale_approval_and_idempotent_migration_command(self):
        class Definitions:
            def select_related(inner, *fields):
                return self.vehicles.values()

        self.generation.vehicle_definitions = Definitions()
        self.api.batchUpdate.return_value.execute.side_effect = lambda **_: self.apply_mock(
            self.api.batchUpdate.call_args.kwargs["body"]["requests"],
        )
        old_pin = self.path.read_bytes()
        command = "reference.management.commands.refresh_configuration_inactive"
        with override_settings(BASE_DIR=self.base), patch(f"{command}.select_generation", return_value=self.generation), patch(
            f"{command}.connect", return_value=self.api,
        ):
            stdout = StringIO()
            call_command("refresh_configuration_inactive", migrate=True, stdout=stdout)
            tag = stdout.getvalue().split("Reviewed preview hash: ")[1].strip()
            self.assertEqual(self.path.read_bytes(), old_pin)
            with self.assertRaisesMessage(CommandError, "preview is stale"):
                call_command("refresh_configuration_inactive", migrate=True, apply="stale")
            self.api.batchUpdate.assert_not_called()
            call_command("refresh_configuration_inactive", migrate=True, apply=tag, stdout=StringIO())
            new_pin = self.path.read_bytes()
            self.assertNotEqual(old_pin, new_pin)
            call_command("refresh_configuration_inactive", migrate=True, apply=tag, stdout=StringIO())
            self.assertEqual(self.path.read_bytes(), new_pin)
            self.api.batchUpdate.assert_called_once()
