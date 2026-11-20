import json
from copy import deepcopy
from unittest.mock import Mock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from reference.configuration_logic_changelog import generated_rows, log_path, read_workbook, sync_after_revision, sync_change_log
from reference.configuration_logic import export_generation
from reference.configuration_logic_revisions import (
    capture_remote, check_working_remote, current_draft, load_layout, load_revision, publish_working_edits,
    save_remote, working_history,
)
from reference.configuration_logic_google import read_registry
from reference.tests import test_configuration_logic_revisions as b2


class LayoutAndLogTests(SimpleTestCase):
    setUp = b2.WorkingRevisionTests.setUp
    response = b2.WorkingRevisionTests.response
    data = b2.WorkingRevisionTests.data
    register = b2.WorkingRevisionTests.register
    edit_plan = b2.WorkingRevisionTests.edit_plan

    def save(self, *, enroll=False):
        old = load_revision(self.state, self.path)
        remote = capture_remote(self.api, self.draft, self.state)
        identifier = save_remote(self.api, self.draft, self.path, self.state, remote, old, enroll=enroll)
        self.state = read_registry(self.path, self.draft.key)
        return identifier

    def move(self, name, old, new):
        for row in self.data(name):
            cells = row["values"]
            width = 9 if name == "Source References" else 21
            cells.extend({} for _ in range(width - len(cells)))
            cells.insert(new, cells.pop(old))

    def test_legacy_enrollment_and_capture_of_a_complete_permutation(self):
        old_revision = self.register()
        self.assertIsNone(load_layout(self.state, self.path))
        legacy = self.path.parent / "revisions" / self.path.stem / old_revision / "manifest.json"
        legacy_bytes = legacy.read_bytes()
        self.data("MY2025")[4]["values"][11]["note"] = "Keep evidence"
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {"numberFormat": {"type": "CURRENCY", "pattern": "$0"}}
        first = self.save(enroll=True)
        initial = load_layout(self.state, self.path)
        self.move("MY2025", 11, 7)
        second = self.save()
        layout = load_layout(self.state, self.path)
        self.assertEqual(layout["logical_content_hash"], initial["logical_content_hash"])
        self.assertEqual(layout["sheets"]["MY2025"]["rows"], initial["sheets"]["MY2025"]["rows"])
        self.assertEqual(layout["sheets"]["MY2025"]["columns"]["configuration.base_msrp"], 8)
        self.assertEqual(current_draft(self.generation, self.path, self.state).sheets[0].rows[4][7], 500)
        self.assertEqual(self.data("MY2025")[4]["values"][7]["note"], "Keep evidence")
        self.assertEqual(legacy.read_bytes(), legacy_bytes)
        self.assertEqual([key for key, _ in working_history(self.path, self.state)], [second, first, old_revision])
        self.assertNotIn(second, generated_rows(self.path, self.state))

    def test_compact_header_capture_preserves_identity_and_resolves_physical_rows(self):
        initial = self.save(enroll=True)
        row_id = load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][0]["id"]
        rows = self.data("MY2025")
        del rows[:3]
        rows[0]["values"][1]["userEnteredValue"]["stringValue"] = "Vehicle Definition PK"
        state = load_revision(self.state, self.path)
        with self.assertRaisesMessage(CommandError, "header row changed"):
            check_working_remote(self.api, self.draft, self.state, state, flexible=True)
        values = rows[1]["values"][11]["userEnteredValue"]
        values["numberValue"] = 501
        with self.assertRaisesMessage(CommandError, "changes data during a header-row transition"):
            self.save()
        values["numberValue"] = 500
        with self.assertRaisesMessage(CommandError, "changes structural bindings"):
            self.save()
        self.remote["MY2025"]["properties"]["gridProperties"]["frozenRowCount"] = 1
        revision = self.save()
        layout = load_layout(self.state, self.path)
        self.assertEqual(layout["sheets"]["MY2025"]["header_row"], 1)
        self.assertEqual(layout["sheets"]["MY2025"]["rows"][0]["row"], 2)
        self.assertEqual(layout["sheets"]["MY2025"]["rows"][0]["id"], row_id)
        self.assertNotIn(revision, generated_rows(self.path, self.state))
        self.assertNotEqual(revision, initial)
        draft = current_draft(self.generation, self.path, self.state)
        self.assertEqual(draft.sheets[0].rows[0][1], "Vehicle Definition PK")
        plan = self.base / "compact.json"
        plan.write_text(json.dumps({"schema": 2, "base_revision": revision, "edits": [
            {"sheet_id": 1, "row_id": row_id, "field_id": "configuration.base_msrp", "before": 500, "value": 510},
        ]}))
        def apply(**_):
            update, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            self.assertEqual(update["updateCells"]["start"], {"sheetId": 1, "rowIndex": 1, "columnIndex": 11})
            values["numberValue"] = 510
        self.api.batchUpdate.return_value.execute.side_effect = apply
        self.assertTrue(publish_working_edits(self.api, draft, self.path, self.state, plan))

    def test_partial_moves_unknown_columns_and_mixed_edits_refused(self):
        self.save(enroll=True)
        original = deepcopy(self.remote)
        for kind in ("partial", "unknown", "populated extra", "duplicate", "missing", "other sheet", "merge"):
            self.remote = deepcopy(original)
            self.remote["MY2025"]["data"][0]["columnMetadata"] = [{"pixelSize": 178}]
            row = self.data("MY2025")[3]["values"]
            if kind == "unknown":
                row.append({"userEnteredValue": {"stringValue": "Unknown"}})
            elif kind == "partial":
                row[8], row[11] = row[11], row[8]
            elif kind == "populated extra":
                self.data("MY2025")[4]["values"].append({"userEnteredValue": {"stringValue": "Extra data"}})
            elif kind == "duplicate":
                row[8] = row[11]
            elif kind == "missing":
                row.pop()
            elif kind == "other sheet":
                self.data("MY2024")[3]["values"].append(row.pop())
            else:
                self.remote["MY2025"]["merges"] = [{"startRowIndex": 4, "endRowIndex": 5,
                                                   "startColumnIndex": 8, "endColumnIndex": 10}]
            with self.subTest(kind=kind), self.assertRaises(CommandError):
                self.save()
        self.api.batchUpdate.assert_not_called()

    def test_capture_records_presentation_with_and_without_semantic_edits(self):
        grid = self.remote["MY2025"]["data"][0]
        grid["columnMetadata"] = [{"pixelSize": 192}]
        self.save(enroll=True)
        initial = load_layout(self.state, self.path)
        cell = self.data("MY2025")[4]["values"][11]
        presentation = {"horizontalAlignment": "LEFT", "wrapStrategy": "WRAP",
                        "numberFormat": {"type": "CURRENCY", "pattern": "$0"}}
        cell["userEnteredFormat"] = dict(presentation)
        grid["columnMetadata"][0]["pixelSize"] = 178
        width_revision = self.save()
        snapshot = load_revision(self.state, self.path)
        width_layout = load_layout(self.state, self.path)
        self.assertEqual(snapshot["MY2025"]["data"][0]["columnMetadata"][0]["pixelSize"], 178)
        self.assertEqual(snapshot["MY2025"]["data"][0]["rowData"][4]["values"][11]["userEnteredFormat"], presentation)
        self.assertEqual(width_layout["structure_hash"], initial["structure_hash"])
        self.assertEqual(width_layout["logical_content_hash"], initial["logical_content_hash"])
        self.assertNotEqual(width_layout["presentation_hash"], initial["presentation_hash"])
        self.assertNotIn(width_revision, generated_rows(self.path, self.state))

        grid["columnMetadata"][0]["pixelSize"] = 170
        cell["userEnteredFormat"]["wrapStrategy"] = "CLIP"
        cell["userEnteredValue"]["numberValue"] = 510
        mixed_revision = self.save()
        snapshot = load_revision(self.state, self.path)
        self.assertEqual(snapshot["MY2025"]["data"][0]["columnMetadata"][0]["pixelSize"], 170)
        self.assertEqual(snapshot["MY2025"]["data"][0]["rowData"][4]["values"][11]["userEnteredFormat"],
                         {**presentation, "wrapStrategy": "CLIP"})
        entries = generated_rows(self.path, self.state)
        self.assertEqual(list(entries), [mixed_revision])
        self.assertEqual(entries[mixed_revision][4], "MY2025 — 1 value changes (Base MSRP)")
        self.api.batchUpdate.assert_not_called()

    def assert_move_compatible(self, compatible):
        previous = load_revision(self.state, self.path)
        def preflight():
            check_working_remote(self.api, self.draft, self.state, previous, flexible=True)
        if compatible:
            preflight()
            self.assertIsNotNone(self.save())
        else:
            with self.assertRaisesMessage(CommandError, "column move"):
                preflight()
            with self.assertRaisesMessage(CommandError, "column move"):
                self.save()
        self.api.batchUpdate.assert_not_called()

    def test_moves_preserve_logical_filter_and_sort_bindings(self):
        sheet = self.remote["MY2025"]
        basic = sheet["basicFilter"] = {
            "range": {"startColumnIndex": 0, "endColumnIndex": 21},
            "sortSpecs": [{"dimensionIndex": 11, "sortOrder": "ASCENDING"}],
            "criteria": {"11": {"hiddenValues": ["500"]}},
            "filterSpecs": [{"columnIndex": 11, "filterCriteria": {"hiddenValues": ["500"]}}],
        }
        self.save(enroll=True)
        self.move("MY2025", 11, 7)
        self.assert_move_compatible(False)
        basic["sortSpecs"][0]["dimensionIndex"] = 7
        self.assert_move_compatible(False)
        basic["criteria"]["7"] = basic["criteria"].pop("11")
        self.assert_move_compatible(False)
        basic["filterSpecs"][0]["columnIndex"] = 7
        self.assert_move_compatible(True)

    def test_moves_preserve_frozen_field_membership_and_provenance_swap(self):
        sheet = self.remote["MY2025"]
        sheet["properties"]["gridProperties"] = {"frozenColumnCount": 20}
        sheet["basicFilter"] = {"range": {"startColumnIndex": 0, "endColumnIndex": 21}}
        self.save(enroll=True)
        self.move("MY2025", 20, 19)
        self.assert_move_compatible(False)
        self.move("MY2025", 19, 20)
        sheet["properties"]["gridProperties"]["frozenColumnCount"] = 4
        self.save()
        self.move("MY2025", 20, 19)
        self.assert_move_compatible(True)

    def test_moves_fail_closed_on_unsupported_position_dependent_metadata(self):
        self.remote["MY2025"]["charts"] = [{"chartId": 42}]
        self.save(enroll=True)
        self.move("MY2025", 20, 19)
        self.assert_move_compatible(False)

    def test_logical_plan_re_resolves_and_legacy_coordinates_refuse_moved_columns(self):
        revision = self.save(enroll=True)
        row_id = load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][0]["id"]
        self.move("MY2025", 11, 7)
        self.remote["MY2025"]["data"][0]["columnMetadata"] = [{"pixelSize": 178}]
        with self.assertRaisesMessage(CommandError, "exact registered column layout"):
            publish_working_edits(self.api, self.draft, self.path, self.state, self.edit_plan(revision))
        plan = self.base / "logical.json"
        edit = {"sheet_id": 1, "row_id": row_id, "field_id": "configuration.base_msrp", "before": 499, "value": 600}
        def write():
            plan.write_text(json.dumps({"schema": 2, "base_revision": revision, "edits": [edit]}))
        write()
        with self.assertRaisesMessage(CommandError, "stale cell edit"):
            publish_working_edits(self.api, self.draft, self.path, self.state, plan)
        edit["before"] = 500
        write()
        def apply(**_):
            request, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            update = request["updateCells"]
            self.assertEqual(update["start"], {"sheetId": 1, "rowIndex": 4, "columnIndex": 7})
            self.assertEqual(update["fields"], "userEnteredValue")
            self.data("MY2025")[4]["values"][7]["userEnteredValue"]["numberValue"] = 600
        self.api.batchUpdate.return_value.execute.side_effect = apply
        successor = publish_working_edits(self.api, self.draft, self.path, self.state, plan)
        self.state = read_registry(self.path, self.draft.key)
        snapshot = load_revision(self.state, self.path)
        self.assertEqual(snapshot["MY2025"]["data"][0]["columnMetadata"][0]["pixelSize"], 178)
        self.assertEqual(load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][0]["id"], row_id)
        self.assertIn("Agent publication", generated_rows(self.path, self.state)[successor])
        with self.assertRaisesMessage(CommandError, "current base_revision"):
            publish_working_edits(self.api, self.draft, self.path, self.state, plan)

    def test_working_row_continuity_alternatives_additions_and_removals(self):
        cells = [{} for _ in range(21)]
        for index, value in ((0, 1), (1, 21), (14, "Manual")):
            cells[index] = {"userEnteredValue": {"numberValue" if isinstance(value, int) else "stringValue": value}}
        self.data("MY2025").append({"values": cells})
        self.save(enroll=True)
        initial = load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"]
        self.assertEqual(initial[1]["parent_id"], initial[0]["id"])
        self.data("MY2025")[5]["values"][20] = {"userEnteredValue": {"stringValue": "Evidence"}}
        self.save()
        self.assertEqual(load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"], initial)
        self.data("MY2025")[4]["values"][3]["userEnteredValue"]["stringValue"] = "Different configuration"
        with self.assertRaisesMessage(CommandError, "Owner adjudication"):
            self.save()
        self.data("MY2025")[4]["values"][3]["userEnteredValue"]["stringValue"] = "Base"
        self.data("MY2025").pop()
        removed = self.save()
        self.assertEqual(load_layout(self.state, self.path)["sheets"]["MY2025"]["removed_row_ids"], [initial[1]["id"]])
        self.assertIn("1 removed", generated_rows(self.path, self.state)[removed][4])
        self.data("MY2025").append({"values": cells})
        added = self.save()
        self.assertNotEqual(load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][1]["id"], initial[1]["id"])
        self.assertIn("1 rows added", generated_rows(self.path, self.state)[added][4])

    def add_log_mock(self):
        def apply(**_):
            for request in self.api.batchUpdate.call_args.kwargs["body"]["requests"]:
                if "addSheet" in request:
                    self.remote["Change Log"] = {"properties": deepcopy(request["addSheet"]["properties"]),
                                                 "data": [{"rowData": []}]}
                if "updateCells" in request:
                    patch_cells = request["updateCells"]
                    for row, values in enumerate(patch_cells["rows"], patch_cells["start"]["rowIndex"]):
                        grid = self.data("Change Log")
                        while len(grid) <= row:
                            grid.append({"values": []})
                        old = grid[row]["values"]
                        old[:len(values["values"])] = deepcopy(values["values"])
        self.api.batchUpdate.return_value.execute.side_effect = apply
        return apply

    def test_log_sync_keeps_manual_descriptions_and_notes_and_rebuilds_only_managed_fields(self):
        self.save(enroll=True)
        self.data("Source References")[4]["values"][2]["note"] = "Owner annotation"
        first = self.save()
        digest = self.path.read_bytes()
        self.add_log_mock()
        self.assertEqual(sync_change_log(self.api, self.draft, self.path, self.state, enable=True), "Change Log synchronized.")
        self.assertEqual(self.path.read_bytes(), digest)
        self.assertEqual(self.data("Change Log")[1]["values"][0]["userEnteredValue"]["stringValue"], first)
        annotations = [{"userEnteredValue": {"stringValue": "Human description"}},
                       {"userEnteredValue": {"stringValue": "Additional note"}}]
        self.data("Change Log")[1]["values"].extend(annotations)
        self.data("MY2025")[4]["values"][11]["userEnteredValue"]["numberValue"] = 510
        second = self.save()
        report = Mock()
        sync_after_revision(self.api, self.draft, self.path, self.state, report)
        report.assert_called_once_with("Change Log synchronized.")
        self.assertEqual(self.data("Change Log")[1]["values"][6:], annotations)
        self.assertEqual(self.data("Change Log")[2]["values"][0]["userEnteredValue"]["stringValue"], second)
        self.assertEqual(sync_change_log(self.api, self.draft, self.path, self.state), "Change Log already matches.")
        self.assertEqual(self.api.batchUpdate.call_count, 2)
        self.data("Change Log")[1]["values"][4]["userEnteredValue"]["stringValue"] = "Unexpected machine edit"
        with self.assertRaisesMessage(CommandError, "managed fields"):
            sync_change_log(self.api, self.draft, self.path, self.state)
        sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True)
        self.assertEqual(self.data("Change Log")[1]["values"][6:], annotations)

    def test_lost_response_recovers_without_duplicate_or_recursive_revision(self):
        revision = self.save(enroll=True)
        self.data("MY2025")[4]["values"][11]["note"] = "New observation"
        self.save()
        put = self.add_log_mock()
        def interrupted(**kwargs):
            put(**kwargs)
            raise OSError("response lost")
        self.api.batchUpdate.return_value.execute.side_effect = interrupted
        with self.assertRaises(CommandError):
            sync_change_log(self.api, self.draft, self.path, self.state, enable=True)
        self.assertIn("pending", json.loads(log_path(self.path).read_text()))
        self.assertEqual(sync_change_log(self.api, self.draft, self.path, self.state), "Change Log already matches.")
        self.assertEqual(self.api.batchUpdate.call_count, 1)
        self.assertEqual(len(list(working_history(self.path, self.state))), 2)
        self.assertEqual(len(self.data("Change Log")), 2)
        self.assertNotIn(revision, generated_rows(self.path, self.state))

    def test_interrupted_rebuild_recovers_only_from_known_machine_states(self):
        self.save(enroll=True)
        self.data("MY2025")[4]["values"][11]["note"] = "Evidence"
        self.save()
        apply = self.add_log_mock()
        sync_change_log(self.api, self.draft, self.path, self.state, enable=True)
        original = deepcopy(self.remote)
        sidecar = log_path(self.path).read_bytes()
        for outcome in ("not dispatched", "not applied", "applied", "independent change"):
            with self.subTest(outcome=outcome):
                self.remote = deepcopy(original)
                log_path(self.path).write_bytes(sidecar)
                cells = self.data("Change Log")[1]["values"]
                cells[4]["userEnteredValue"]["stringValue"] = "Original tampering"
                def lost(**kwargs):
                    if outcome == "applied":
                        apply(**kwargs)
                    raise OSError("Lost response")
                self.api.batchUpdate.reset_mock()
                self.api.batchUpdate.return_value.execute.side_effect = lost
                path = "reference.configuration_logic_changelog.read_workbook"
                if outcome == "not dispatched":
                    sheet_id = self.remote["Change Log"]["properties"]["sheetId"]
                    preflight = read_workbook(self.api, self.draft, self.state, sheet_id)
                    with patch(path, side_effect=[preflight, CommandError("Read failed")]), self.assertRaises(CommandError):
                        sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True)
                    self.api.batchUpdate.assert_not_called()
                else:
                    with self.assertRaises(CommandError):
                        sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True)
                cells.extend([{"userEnteredValue": {"stringValue": "New description"}},
                              {"userEnteredValue": {"stringValue": "New note"}}])
                annotations = deepcopy(cells[6:])
                self.api.batchUpdate.reset_mock()
                self.api.batchUpdate.return_value.execute.side_effect = apply
                if outcome == "independent change":
                    cells[4]["userEnteredValue"]["stringValue"] = "Different tampering"
                    with self.assertRaisesMessage(CommandError, "both pending recovery states"):
                        sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True)
                else:
                    expected = "Change Log already matches." if outcome == "applied" else "Change Log synchronized."
                    self.assertEqual(sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True), expected)
                    self.assertEqual(sync_change_log(self.api, self.draft, self.path, self.state, rebuild=True),
                                     "Change Log already matches.")
                self.assertEqual(self.api.batchUpdate.call_count, int(outcome in ("not dispatched", "not applied")))
                self.assertEqual(cells[6:], annotations)

    def test_xlsx_uses_registered_field_order_number_format_width_and_notes(self):
        try:
            from openpyxl import load_workbook
        except ImportError:
            self.skipTest("optional XLSX dependency unavailable")
        self.data("MY2025")[4]["values"][11]["note"] = "Evidence note"
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {"numberFormat": {"type": "CURRENCY", "pattern": "$0"}}
        self.save(enroll=True)
        self.move("MY2025", 11, 7)
        self.remote["MY2025"]["data"][0]["columnMetadata"] = [{} for _ in range(7)] + [{"pixelSize": 160}]
        self.save()
        output = self.base / "review.xlsx"
        with override_settings(BASE_DIR=self.base), patch("reference.configuration_logic.select_generation", return_value=self.generation):
            export_generation({"manufacturer": "Maker", "model": "Truck", "generation": "4",
                               "output": output, "reviewed_observations": None})
        workbook = load_workbook(output)
        sheet = workbook["MY2025"]
        self.assertEqual(workbook.sheetnames, ["MY2025", "MY2024", "Source References"])
        self.assertEqual((sheet["H4"].value, sheet["H5"].value), ("Base MSRP", 500))
        self.assertEqual(sheet["H5"].number_format, "$0")
        self.assertEqual(sheet["H5"].comment.text, "Evidence note")
        self.assertEqual(sheet.column_dimensions["H"].width, 20)

    def test_generated_summary_bounds_field_list_and_handles_missing_attribution(self):
        self.save(enroll=True)
        manifest = {"revision": "fixture", "captured_at": None}
        changes = {"MY2025": {"cells": [{"column": i % 20 + 1} for i in range(120)]}}
        with patch("reference.configuration_logic_changelog.revision_manifests", return_value=[manifest]), patch(
            "reference.configuration_logic_changelog.verified_json", side_effect=[changes, {"operation": "capture"}],
        ):
            row = generated_rows(self.path, self.state)["fixture"]
        self.assertEqual((row[1], row[2], row[5]), ("Not recorded", "Human capture", "Not recorded"))
        self.assertIn("120 value changes", row[4])
        self.assertLess(len(row[4]), 110)

    def test_conflicting_log_identity_does_not_prevent_capture(self):
        self.save(enroll=True)
        self.remote["Change Log"] = {"properties": {"title": "Change Log", "sheetId": 55, "index": 3}}
        with self.assertRaisesMessage(CommandError, "Conflicting"):
            sync_change_log(self.api, self.draft, self.path, self.state, enable=True)
        self.data("MY2025")[4]["values"][11]["note"] = "New evidence"
        self.assertIsNotNone(self.save())
        self.api.batchUpdate.assert_not_called()
