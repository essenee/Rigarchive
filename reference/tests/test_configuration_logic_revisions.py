from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from reference.configuration_logic import GenerationDraft, HEADERS, Sheet, SOURCE_HEADERS, WIDTHS
from reference.configuration_logic_google import entered, fingerprint, publish, read_registry
from reference.configuration_logic_revisions import (
    capture_remote, changes_between, current_draft, load_revision, publish_working_edits,
    revision_root, save_remote, validated_rows, working_history,
)


class WorkingRevisionTests(SimpleTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.path = self.base / ".configuration-logic" / "generation.json"
        self.path.parent.mkdir()
        self.generation = SimpleNamespace(uuid="generation", name="Fourth Generation", slug="fourth-generation",
                                          vehicle_model=SimpleNamespace(name="Truck", manufacturer=SimpleNamespace(name="Maker")))
        title = "Maker Truck — 4th Generation — Configuration Logic"
        parent = [None] * len(HEADERS)
        parent[0], parent[1], parent[3], parent[7], parent[11], parent[12] = 1, 21, "Base", "4WD", 500, "base-truck"
        self.draft = GenerationDraft("generation", title, (
            Sheet("MY2025", ((title,), ("Draft",), (), HEADERS, tuple(parent)), WIDTHS, (11, 17)),
            Sheet("MY2024", ((title,), ("Draft — awaiting research and review",), (), HEADERS), WIDTHS, (11, 17)),
            Sheet("Source References", ((title,), ("Draft provenance",), (), SOURCE_HEADERS,
                                        (2025, "Maker", "Original")), (14, 18, 32, 60, 20, 29, 42, 28, 65)),
        ))
        self.remote = {
            t.name: {
                "properties": {"sheetId": i + 1, "index": i, "title": t.name, "gridProperties": {"frozenRowCount": 4}},
                "data": [{"rowData": [{"values": [{"userEnteredValue": entered(v)} if entered(v) else {}
                                                 for v in row]} for row in t.rows]}],
            } for i, t in enumerate(self.draft.sheets)
        }
        self.api = Mock()
        self.api.get.return_value.execute.side_effect = lambda **kwargs: self.response()
        self.state = {
            "schema": 1, "generation": self.draft.key, "spreadsheet": "file-id", "mode": "draft",
            "sheets": {t.name: {"id": i + 1, "rows": len(t.rows), "columns": len(t.widths),
                               "fingerprint": fingerprint(self.remote[t.name])} for i, t in enumerate(self.draft.sheets)},
        }
        self.path.write_text(json.dumps(self.state))

    def response(self):
        return {"spreadsheetId": "file-id", "properties": {"title": self.draft.title},
                "sheets": deepcopy(list(self.remote.values()))}

    def data(self, name):
        return self.remote[name]["data"][0]["rowData"]

    def register(self, previous=None):
        remote = capture_remote(self.api, self.draft, self.state)
        revision = save_remote(self.api, self.draft, self.path, self.state, remote, previous)
        self.state = read_registry(self.path, self.draft.key)
        return revision

    def test_inspect_is_read_only_and_does_not_invent_comparison(self):
        checksum = self.path.read_bytes()
        output = StringIO()
        command = "reference.management.commands.save_configuration_logic"
        with override_settings(BASE_DIR=self.base), patch(f"{command}.select_generation", return_value=self.generation), patch(
            f"{command}.current_draft", return_value=self.draft,
        ), patch(f"{command}.connect", return_value=self.api) as connect:
            call_command("save_configuration_logic", manufacturer="Maker", model="Truck", generation="4",
                         inspect=True, stdout=output)
        self.assertIn("No trustworthy local comparison baseline", output.getvalue())
        self.assertEqual(self.path.read_bytes(), checksum)
        self.assertFalse(revision_root(self.path).exists())
        connect.assert_called_once_with(self.path.parent, persist=False)
        self.api.batchUpdate.assert_not_called()

    def test_capture_registers_changes_sources_annotations_and_keeps_prior_files(self):
        first = self.register()
        old_folder = revision_root(self.path) / first
        original = {file.name: file.read_bytes() for file in old_folder.iterdir()}
        before = load_revision(self.state, self.path)
        self.data("MY2025")[4]["values"][11] = {"userEnteredValue": {"numberValue": 525}, "note": "Check price"}
        self.data("Source References")[4]["values"][2]["userEnteredValue"]["stringValue"] = "Edited source"
        second = self.register(before)
        self.assertNotEqual(first, second)
        self.assertEqual({file.name: file.read_bytes() for file in old_folder.iterdir()}, original)
        new_folder = revision_root(self.path) / second
        changes = json.loads((new_folder / "changes.json").read_text())
        self.assertEqual(changes["MY2025"]["notes"][0]["after"], "Check price")
        self.assertEqual(changes["Source References"]["cells"][0]["after"], {"stringValue": "Edited source"})
        self.assertEqual(len((new_folder / "MY2024.csv").read_text().splitlines()), 4)
        self.assertEqual(self.state["working_revision"]["id"], second)
        self.assertEqual(self.state["sheets"]["MY2025"]["fingerprint"], fingerprint(self.remote["MY2025"]))
        self.assertEqual([r[0] for r in working_history(self.path, self.state)], [second, first])
        self.assertIsNone(self.register(load_revision(self.state, self.path)))
        self.api.batchUpdate.assert_not_called()

    def test_added_removed_rows_and_format_only_changes(self):
        self.register()
        before = load_revision(self.state, self.path)
        row = deepcopy(self.data("MY2025")[4])
        row["values"][0]["userEnteredValue"]["numberValue"] = 2
        row["values"][1]["userEnteredValue"]["numberValue"] = 22
        self.data("MY2025").append(row)
        added = capture_remote(self.api, self.draft, self.state)
        self.assertEqual(changes_between(before, added, self.draft.sheets)["MY2025"]["row_changes"][0][0], "insert")
        self.data("MY2025").pop()
        self.assertEqual(changes_between(added, self.remote, self.draft.sheets)["MY2025"]["row_changes"][0][0], "delete")
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {"textFormat": {"bold": True}}
        change = changes_between(before, self.remote, self.draft.sheets)["MY2025"]
        self.assertFalse(change["cells"])
        self.assertTrue(change["fingerprint_changed"])
        self.assertIsNotNone(self.register(before))

    def test_missing_duplicate_reordered_headers_and_data_merges_fail_closed(self):
        table = self.draft.sheets[0]
        for kind in ("missing", "duplicate", "reordered"):
            sheet = deepcopy(self.remote[table.name])
            headers = sheet["data"][0]["rowData"][3]["values"]
            if kind == "missing":
                headers.pop()
            elif kind == "duplicate":
                headers[1] = headers[0]
            else:
                headers[1], headers[0] = headers[0], headers[1]
            with self.subTest(kind=kind), self.assertRaisesMessage(CommandError, "column headers"):
                validated_rows(table, sheet)
        sheet = deepcopy(self.remote[table.name])
        sheet["merges"] = [{"startRowIndex": 0, "endRowIndex": 1, "endColumnIndex": 3}]
        validated_rows(table, sheet)
        sheet["merges"][0]["endRowIndex"] = 5
        with self.assertRaisesMessage(CommandError, "merge intersecting"):
            validated_rows(table, sheet)

    def test_interrupted_persistence_and_remote_race_leave_prior_pointer_usable(self):
        self.register()
        old = load_revision(self.state, self.path)
        checksum = self.path.read_bytes()
        self.data("MY2025")[4]["values"][11]["userEnteredValue"]["numberValue"] = 525
        remote = capture_remote(self.api, self.draft, self.state)
        self.data("MY2025")[4]["values"][11]["userEnteredValue"]["numberValue"] = 550
        with self.assertRaisesMessage(CommandError, "changed during capture"):
            save_remote(self.api, self.draft, self.path, self.state, remote, old)
        import reference.configuration_logic_revisions as revisions
        write = revisions.write_private
        def fail_pointer(path, text):
            if path == self.path:
                raise OSError("Interrupted pointer update")
            return write(path, text)
        with patch.object(revisions, "write_private", side_effect=fail_pointer), self.assertRaises(OSError):
            self.register(old)
        self.assertEqual(self.path.read_bytes(), checksum)
        self.assertEqual(load_revision(self.state, self.path), old)

    def test_resume_only_writes_targeted_values_and_stale_django_cannot_overwrite(self):
        self.data("MY2025")[4]["values"][3]["userEnteredValue"]["stringValue"] = "Human trim"
        self.data("MY2025")[4]["values"][11]["note"] = "Keep this note"
        first = self.register()
        with patch("reference.configuration_logic_revisions.generation_draft", side_effect=AssertionError("ORM fallback")):
            draft = current_draft(self.generation, self.path, self.state)
        self.assertEqual(draft.sheets[0].rows[4][3], "Human trim")
        with self.assertRaisesMessage(CommandError, "revision-bound"):
            publish(self.api, self.draft, self.path, self.state)
        self.assertEqual(publish(self.api, draft, self.path, self.state), [])
        self.api.batchUpdate.assert_not_called()
        plan = self.base / "edits.json"
        plan.write_text(json.dumps({"base_revision": first, "edits": [
            {"sheet": "MY2025", "row": 5, "column": 12, "before": 500, "value": 600},
        ]}))
        def apply(**kwargs):
            requests = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            self.assertEqual(requests, [{"updateCells": {
                "start": {"sheetId": 1, "rowIndex": 4, "columnIndex": 11},
                "rows": [{"values": [{"userEnteredValue": {"numberValue": 600}}]}],
                "fields": "userEnteredValue",
            }}])
            self.data("MY2025")[4]["values"][11]["userEnteredValue"]["numberValue"] = 600
            return {}
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {
            "wrapStrategy": "WRAP", "horizontalAlignment": "RIGHT", "borders": {"bottom": {"style": "SOLID"}},
            "textFormat": {"fontFamily": "Arial", "bold": True},
        }
        self.remote["MY2025"]["data"][0]["columnMetadata"] = [{"pixelSize": 145}]
        self.remote["MY2025"]["data"][0]["rowMetadata"] = [{}, {}, {}, {}, {"pixelSize": 41}]
        formatted = deepcopy(self.remote["MY2025"])
        self.api.batchUpdate.return_value.execute.side_effect = apply
        report = Mock()
        revision = publish_working_edits(self.api, draft, self.path, self.state, plan, report=report)
        report.assert_called_once_with("Nonblocking presentation changes detected and preserved in: MY2025.")
        formatted["data"][0]["rowData"][4]["values"][11]["userEnteredValue"]["numberValue"] = 600
        self.assertEqual(self.remote["MY2025"], formatted)
        new_state = read_registry(self.path, self.draft.key)
        self.assertEqual(new_state["working_revision"]["id"], revision)
        self.assertEqual(current_draft(self.generation, self.path, new_state).sheets[0].rows[4][3], "Human trim")
        self.assertEqual(self.data("MY2025")[4]["values"][11]["note"], "Keep this note")
        self.api.batchUpdate.assert_called_once()
        with self.assertRaisesMessage(CommandError, "current base_revision"):
            publish_working_edits(self.api, draft, self.path, new_state, plan)

    def test_authorized_save_command_and_history_do_not_write_remote(self):
        command = "reference.management.commands.save_configuration_logic"
        args = dict(manufacturer="Maker", model="Truck", generation="4")
        with override_settings(BASE_DIR=self.base), patch(
            f"{command}.select_generation", return_value=self.generation,
        ), patch(f"{command}.current_draft", return_value=self.draft), patch(
            f"{command}.connect", return_value=self.api,
        ) as connect:
            with self.assertRaisesMessage(CommandError, "--save --confirm"):
                call_command("save_configuration_logic", **args, save=True, stdout=StringIO())
            connect.assert_not_called()
            call_command("save_configuration_logic", **args, save=True, confirm=True, stdout=StringIO())
            history = StringIO()
            call_command("save_configuration_logic", **args, history=True, stdout=history)
        state = read_registry(self.path, self.draft.key)
        self.assertIn(state["working_revision"]["id"], history.getvalue())
        self.assertIn("working draft", history.getvalue())
        self.api.batchUpdate.assert_not_called()

    def test_unregistered_remote_change_blocks_targeted_publication(self):
        identifier = self.register()
        self.data("MY2025")[4]["values"][3]["userEnteredValue"]["stringValue"] = "Not captured"
        plan = self.base / "edits.json"
        plan.write_text(json.dumps({"base_revision": identifier, "edits": [
            {"sheet": "MY2025", "row": 5, "column": 12, "before": 500, "value": 600},
        ]}))
        with self.assertRaisesMessage(CommandError, "Unexpected external change"):
            publish_working_edits(self.api, self.draft, self.path, self.state, plan)
        self.api.batchUpdate.assert_not_called()

    def edit_plan(self, revision, *, before=500, value=600):
        plan = self.base / "edits.json"
        plan.write_text(json.dumps({"base_revision": revision, "edits": [
            {"sheet": "MY2025", "row": 5, "column": 12, "before": before, "value": value},
        ]}))
        return plan

    def test_presentation_only_noop_does_not_register_a_revision_or_write_to_sheets(self):
        revision = self.register()
        pointer = self.path.read_bytes()
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {"wrapStrategy": "WRAP"}
        remote = deepcopy(self.remote)
        report = Mock()
        self.assertEqual(publish(self.api, self.draft, self.path, self.state, dry_run=True, report=report), [])
        self.assertIsNone(publish_working_edits(
            self.api, self.draft, self.path, self.state, self.edit_plan(revision, value=500), report=report,
        ))
        self.assertEqual(report.call_count, 2)
        self.assertEqual(self.remote, remote)
        self.assertEqual(self.path.read_bytes(), pointer)
        self.assertEqual([r[0] for r in working_history(self.path, self.state)], [revision])
        self.api.batchUpdate.assert_not_called()
        self.assertIsNotNone(self.register(load_revision(self.state, self.path)))

    def test_unsafe_changes_block_targeted_publication(self):
        revision = self.register()
        snapshot = deepcopy(self.remote)
        plan = self.edit_plan(revision)
        for kind in ("note", "renamed header", "column move", "added row", "removed row", "data merge",
                     "decorative merge", "hidden", "conditional format", "freeze", "filter", "sort", "number format"):
            self.remote = deepcopy(snapshot)
            sheet = self.remote["MY2025"]
            headers = self.data("MY2025")[3]["values"]
            cell = self.data("MY2025")[4]["values"][11]
            if kind == "note":
                cell["note"] = "Unregistered research"
            elif kind == "renamed header":
                headers[11]["userEnteredValue"]["stringValue"] = "Modified"
            elif kind == "column move":
                headers[10], headers[11] = headers[11], headers[10]
            elif kind == "added row":
                row = deepcopy(self.data("MY2025")[4])
                row["values"][0]["userEnteredValue"]["numberValue"] = 2
                row["values"][1]["userEnteredValue"]["numberValue"] = 22
                self.data("MY2025").append(row)
            elif kind == "removed row":
                self.data("MY2025").pop()
            elif kind == "data merge":
                sheet["merges"] = [{"startRowIndex": 4, "endRowIndex": 5, "endColumnIndex": 2}]
            elif kind == "decorative merge":
                sheet["merges"] = [{"startRowIndex": 0, "endRowIndex": 1, "endColumnIndex": 3}]
            elif kind == "hidden":
                sheet["data"][0]["columnMetadata"] = [{"hiddenByUser": True}]
            elif kind == "conditional format":
                sheet["conditionalFormats"] = [{"ranges": [{"sheetId": 1, "startRowIndex": 4}]}]
            elif kind == "freeze":
                sheet["properties"]["gridProperties"]["frozenColumnCount"] = 1
            elif kind == "filter":
                sheet["basicFilter"] = {"range": {"sheetId": 1}}
            elif kind == "sort":
                sheet["basicFilter"] = {"sortSpecs": [{"dimensionIndex": 3, "sortOrder": "ASCENDING"}]}
            else:
                cell["userEnteredFormat"] = {"numberFormat": {"type": "PERCENT"}}
            with self.subTest(kind=kind), self.assertRaises(CommandError):
                publish_working_edits(self.api, self.draft, self.path, self.state, plan)
        self.api.batchUpdate.assert_not_called()

    def test_cosmetics_do_not_allow_wrong_prior_value_or_stale_revision(self):
        revision = self.register()
        self.data("MY2025")[4]["values"][11]["userEnteredFormat"] = {"wrapStrategy": "WRAP"}
        with self.assertRaisesMessage(CommandError, "stale cell edit"):
            publish_working_edits(self.api, self.draft, self.path, self.state, self.edit_plan(revision, before=499))
        with self.assertRaisesMessage(CommandError, "current base_revision"):
            publish_working_edits(self.api, self.draft, self.path, self.state, self.edit_plan("stale"))
        self.api.batchUpdate.assert_not_called()
