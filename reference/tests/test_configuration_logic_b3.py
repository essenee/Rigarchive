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

    def test_trim_rename_retains_working_identity_and_rejects_identity_changes(self):
        cells = self.data("MY2025")[4]["values"]
        cells[2] = {"userEnteredValue": {"stringValue": "8628"}}
        self.save(enroll=True)
        row_id = load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][0]["id"]
        cells[3]["userEnteredValue"]["stringValue"] = "Base i-FORCE MAX"
        self.save()
        self.assertEqual(load_layout(self.state, self.path)["sheets"]["MY2025"]["rows"][0]["id"], row_id)
        for index, value in ((1, {"numberValue": 42}), (7, {"stringValue": "2WD"}), (12, {"stringValue": "replaced"})):
            with self.subTest(index=index):
                original = cells[index]
                cells[index] = {"userEnteredValue": value}
                with self.assertRaises(CommandError):
                    self.save()
                cells[index] = original

    def test_blank_correspondence_publication_requires_the_exact_creation_receipt(self):
        from types import SimpleNamespace
        from reference.configuration_logic_google import entered

        name = "MY2025"
        cells = self.data(name)[4]["values"]
        row = [1, None, "8628", "Base", None, None, None, "4WD", "T24A-FTS", "hybrid",
               "Hybrid", 500, None, "United States", "8-Spd Auto"]
        for i, value in enumerate(row):
            cells[i] = {"userEnteredValue": entered(value)} if value is not None else {}
        first = self.save(enroll=True)
        binding = load_layout(self.state, self.path)["sheets"][name]
        row_id = binding["rows"][0]["id"]
        vehicle = SimpleNamespace(pk=101, uuid="vehicle-uuid", slug="immutable-slug", model_year=2025,
                                  generation=self.generation, market="US", is_active=True, engine_id=1,
                                  trim_name="Base", drivetrain="4WD", transmission="8-spd Auto",
                                  base_msrp=500, factory_body_configuration_id=None,
                                  engine=SimpleNamespace(engine_code="T24A-FTS", internal_variant_key="hybrid"))
        proof = {"working_revision": self.state["working_revision"], "row_id": "unrelated", "parent_row_id": None}
        receipt = SimpleNamespace(
            created_vehicle_definition=vehicle, created_vehicle_definition_pk_snapshot=101,
            created_vehicle_definition_uuid_snapshot="vehicle-uuid",
            created_vehicle_definition_slug_snapshot="immutable-slug",
            resolution_snapshot_json={"profile": "human-body-authoring/2",
                                      "observation": {"transmission_evidence": proof}},
        )
        plan = self.base / "correspondence.json"
        payload = {"schema": 2, "base_revision": first, "canonical_correspondences": [
            {"sheet": name, "row_id": row_id, "receipt_pk": 7},
        ]}
        plan.write_text(json.dumps(payload))

        def apply(**_):
            for request in self.api.batchUpdate.call_args.kwargs["body"]["requests"]:
                update = request["updateCells"]
                cells[update["start"]["columnIndex"]] = update["rows"][0]["values"][0]

        self.api.batchUpdate.return_value.execute.side_effect = apply
        with patch("reference.configuration_logic_correspondence.ImportExecutionReceipt.objects.select_related") as query:
            query.return_value.get.return_value = receipt
            with self.assertRaisesMessage(CommandError, "exact B3 creation receipt"):
                publish_working_edits(self.api, self.draft, self.path, self.state, plan)
            self.api.batchUpdate.assert_not_called()
            proof["row_id"] = row_id
            successor = publish_working_edits(self.api, self.draft, self.path, self.state, plan)
            state = read_registry(self.path, self.draft.key)
            self.assertEqual(cells[1]["userEnteredValue"], {"numberValue": 101})
            self.assertEqual(cells[12]["userEnteredValue"], {"stringValue": "immutable-slug"})
            self.assertEqual(load_layout(state, self.path)["sheets"][name]["rows"], binding["rows"])
            with self.assertRaisesMessage(CommandError, "current base_revision"):
                publish_working_edits(self.api, self.draft, self.path, state, plan)
            plan.write_text(json.dumps({**payload, "base_revision": successor}))
            with self.assertRaisesMessage(CommandError, "empty standalone"):
                publish_working_edits(self.api, self.draft, self.path, state, plan)

    def test_source_alias_preserves_document_hash_status_and_id(self):
        from reference.configuration_logic_layout import bind_rows
        from reference.configuration_logic_revisions import source_alias_bindings

        fingerprint = "sha256:" + "a" * 64
        header = ("Model Year", "Organization", "Source", "URL / Document ID", "Acquired / Reviewed",
                  "Source Type", "Evidence ID", "Verification Status", "Notes")
        source = (2025, "Toyota", "Pricing", "https://toyota.com/pricing", "2026-11-20", "Schedule",
                  fingerprint, "Original bytes not verified", "Pricing table.")
        after = (*source[:6], "T25-L", source[7], f"{source[8]} Previous Evidence ID: {fingerprint}.")
        old_rows, new_rows = (header, source), (header, after)
        before, _ = bind_rows("Source References", old_rows, (), header=0)
        rebased = source_alias_bindings(old_rows, new_rows, before, 0)
        new, removed = bind_rows("Source References", new_rows, rebased, header=0)
        self.assertEqual(new[0]["id"], before[0]["id"])
        self.assertEqual(removed, [])
        for unsafe in ((*after[:-1], "Pricing table."),
                       (*after[:7], "Original bytes verified", after[8])):
            with self.assertRaisesMessage(CommandError, "must preserve"):
                source_alias_bindings(old_rows, (header, unsafe), before, 0)
        with self.assertRaisesMessage(CommandError, "duplicate readable"):
            source_alias_bindings(old_rows, (header, after, after), before, 0)

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

    def test_registered_spreadsheet_title_can_differ_from_tab_preamble(self):
        from dataclasses import replace

        preamble = self.draft.title
        self.draft = replace(self.draft, title="Owner's standalone configuration workbook")
        self.save(enroll=True)
        draft = current_draft(self.generation, self.path, self.state)
        self.assertEqual(draft.title, self.draft.title)
        self.assertEqual(draft.sheets[0].title, preamble)
        self.assertEqual(check_working_remote(self.api, draft, self.state, load_revision(self.state, self.path),
                                              flexible=True), self.remote)

    def test_owner_removed_body_columns_survive_targeted_publish_with_stable_ids(self):
        name = "MY2025"
        cells = self.data(name)[4]["values"]
        cells[4:7] = [{"userEnteredValue": {"stringValue": value}}
                      for value in ("Double Cab, 5-ft Bed", "Double Cab", "5-ft")]
        revision = self.save(enroll=True)
        before = load_layout(self.state, self.path)["sheets"][name]["rows"]
        for row in self.data(name):
            values = row["values"]
            del values[5:7]
        self.data(name)[3]["values"][1]["userEnteredValue"]["stringValue"] = "Vehicle Definition PK"
        grid = self.remote[name]["data"][0]
        grid["columnMetadata"] = [{} for _ in range(4)] + [{"hiddenByUser": True, "pixelSize": 167}]
        cell = self.data(name)[4]["values"][9]
        cell["userEnteredFormat"] = {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"}
        plan = self.base / "compact-body.json"
        plan.write_text(json.dumps({"schema": 2, "base_revision": revision, "edits": [
            {"sheet_id": 1, "row_id": before[0]["id"], "field_id": "configuration.base_msrp",
             "before": 500, "value": 510},
        ]}))

        def apply(**_):
            request, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            update = request["updateCells"]
            self.assertEqual(update["start"]["columnIndex"], 9)
            self.assertEqual(update["fields"], "userEnteredValue")
            cell.update(update["rows"][0]["values"][0])

        self.api.batchUpdate.return_value.execute.side_effect = apply
        self.assertTrue(publish_working_edits(self.api, self.draft, self.path, self.state, plan))
        self.state = read_registry(self.path, self.draft.key)
        binding = load_layout(self.state, self.path)["sheets"][name]
        self.assertEqual([row["id"] for row in binding["rows"]], [row["id"] for row in before])
        self.assertNotIn("configuration.cab", binding["columns"])
        self.assertNotIn("configuration.nominal_bed", binding["columns"])
        snapshot = load_revision(self.state, self.path)[name]["data"][0]
        self.assertEqual(snapshot["columnMetadata"][4], {"hiddenByUser": True, "pixelSize": 167})
        self.assertEqual(snapshot["rowData"][4]["values"][9], cell)

    def test_numbering_migration_and_row_moves_preserve_identity_and_formula(self):
        from reference.configuration_logic_google import entered
        from reference.configuration_logic_numbering import plan_numbering
        from reference.configuration_logic_revisions import validated_rows

        name = "MY2025"
        grid = self.data(name)
        grid[4]["values"][2] = {"userEnteredValue": entered("111")}
        other = deepcopy(grid[4])
        for index, value in ((0, 2), (1, 22), (2, "222"), (3, "Other"), (11, 550)):
            other["values"][index] = {"userEnteredValue": entered(value)}
        grid.append(other)
        self.save(enroll=True)
        baseline = load_revision(self.state, self.path)
        bindings = load_layout(self.state, self.path)["sheets"][name]["rows"]
        grid[4:6] = reversed(grid[4:6])
        projected, requests = plan_numbering(self.draft, baseline, self.remote)
        self.assertTrue(all(req["updateCells"]["fields"] == "userEnteredValue" for req in requests))
        self.remote = projected
        revision = save_remote(self.api, self.draft, self.path, self.state, self.remote, baseline,
                               operation="numbering-migration")
        self.state = read_registry(self.path, self.draft.key)
        rows = load_layout(self.state, self.path)["sheets"][name]["rows"]
        self.assertEqual([row["id"] for row in rows], [row["id"] for row in reversed(bindings)])
        numbered = current_draft(self.generation, self.path, self.state)
        self.assertEqual([r[:3] for r in numbered.sheets[0].rows[4:]], [(1, 22, "222"), (2, 21, "111")])
        cells = self.data(name)
        formula = deepcopy(cells[3]["values"][0])
        cells[4:6] = reversed(cells[4:6])
        plan = self.base / "moved-row.json"
        plan.write_text(json.dumps({"schema": 2, "base_revision": revision, "edits": [
            {"sheet_id": 1, "row_id": bindings[0]["id"], "field_id": "configuration.base_msrp",
             "before": 500, "value": 525},
        ]}))

        def apply(**_):
            request, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            update = request["updateCells"]
            self.assertEqual(update["start"]["rowIndex"], 4)
            self.assertEqual(update["start"]["columnIndex"], 11)
            cells[4]["values"][11].update(update["rows"][0]["values"][0])

        self.api.batchUpdate.return_value.execute.side_effect = apply
        self.assertTrue(publish_working_edits(self.api, numbered, self.path, self.state, plan))
        self.assertEqual(cells[3]["values"][0], formula)
        self.assertEqual([r[:3] for r in validated_rows(numbered.sheets[0], self.remote[name], flexible=True)[4:]],
                         [(1, 21, "111"), (2, 22, "222")])
        self.state = read_registry(self.path, self.draft.key)
        registered = load_revision(self.state, self.path)
        cells[4:6] = reversed(cells[4:6])
        old_code = cells[4]["values"][2]["userEnteredValue"]
        cells[4]["values"][2]["userEnteredValue"] = entered("333")
        with self.assertRaisesMessage(CommandError, "Unexpected external change"):
            check_working_remote(self.api, numbered, self.state, registered, flexible=True)
        cells[4]["values"][2]["userEnteredValue"] = old_code
        cells[4:6] = reversed(cells[4:6])
        cells.insert(5, {"values": []})
        self.assertEqual([r[0] for r in validated_rows(numbered.sheets[0], self.remote[name], flexible=True)[4:]],
                         [1, None, 2])
        cells.pop(4)
        self.assertEqual([r[0] for r in validated_rows(numbered.sheets[0], self.remote[name], flexible=True)[4:]],
                         [None, 1])
        duplicate = deepcopy(cells[-1])
        duplicate["values"][1] = {"userEnteredValue": entered(23)}
        duplicate["values"][3] = {"userEnteredValue": entered("Duplicate")}
        cells.append(duplicate)
        with self.assertRaisesMessage(CommandError, "duplicate manufacturer"):
            validated_rows(numbered.sheets[0], self.remote[name], flexible=True)

    def test_numbering_command_previews_publishes_and_verifies_successor(self):
        from io import StringIO

        from django.core.management import call_command
        from reference.configuration_logic_google import entered, remote_values
        from reference.configuration_logic_layout import column_order, numbering_formula, uses_numbering

        name = "MY2025"
        self.data(name)[4]["values"][0]["userEnteredFormat"] = {"backgroundColor": {"red": 1}}
        self.data(name)[4]["values"][2] = {"userEnteredValue": entered("111")}
        self.data(name)[4]["values"][20] = {"userEnteredValue": entered("MSRP: TT-P p. 2"), "note": "Keep evidence"}
        already = self.remote["MY2024"]
        self.data("MY2024")[3]["values"][0]["userEnteredValue"] = {
            "formulaValue": numbering_formula(column_order("MY2024", already)),
        }
        first = self.save(enroll=True)
        baseline = load_revision(self.state, self.path)
        ids = load_layout(self.state, self.path)["sheets"][name]["rows"]
        command = "reference.management.commands.migrate_configuration_logic_numbering"
        args = {"manufacturer": "Maker", "model": "Truck", "generation": "4"}

        def apply(**_):
            request, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            update = request["updateCells"]
            self.assertEqual(update["start"]["sheetId"], 1)
            self.assertEqual(update["fields"], "userEnteredValue")
            for i, row in enumerate(update["rows"], update["start"]["rowIndex"]):
                cell = self.data(name)[i]["values"][update["start"]["columnIndex"]]
                cell.pop("userEnteredValue")
                cell.update(row["values"][0])

        self.api.batchUpdate.return_value.execute.side_effect = apply
        with override_settings(BASE_DIR=self.base), patch(f"{command}.select_generation", return_value=self.generation), patch(
            f"{command}.connect", return_value=self.api,
        ):
            output = StringIO()
            call_command("migrate_configuration_logic_numbering", **args, dry_run=True, stdout=output)
            self.assertIn(f"Base {first}, 1 model-year tabs", output.getvalue())
            token = output.getvalue().strip().splitlines()[-1].split()[-1]
            self.api.batchUpdate.assert_not_called()
            self.assertEqual(read_registry(self.path, self.draft.key)["working_revision"]["id"], first)
            with self.assertRaisesMessage(CommandError, "preview is stale"):
                call_command("migrate_configuration_logic_numbering", **args, apply="stale")
            self.api.batchUpdate.assert_not_called()
            output = StringIO()
            call_command("migrate_configuration_logic_numbering", **args, apply=token, stdout=output)
            successor = read_registry(self.path, self.draft.key)
            self.assertIn(successor["working_revision"]["id"], output.getvalue())
            self.assertNotEqual(successor["working_revision"]["id"], first)
            recorded = load_revision(successor, self.path)
            self.assertTrue(uses_numbering(name, recorded[name]))
            self.assertEqual(load_layout(successor, self.path)["sheets"][name]["rows"], ids)
            self.assertEqual(recorded["MY2024"], baseline["MY2024"])
            self.assertEqual(recorded["Source References"], baseline["Source References"])
            before = remote_values(baseline[name])
            after = remote_values(recorded[name])
            self.assertEqual({k: v for k, v in before.items() if k[1] != 0},
                             {k: v for k, v in after.items() if k[1] != 0})
            self.assertEqual(self.data(name)[4]["values"][0]["userEnteredFormat"], {"backgroundColor": {"red": 1}})
            self.assertEqual(self.data(name)[4]["values"][20]["note"], "Keep evidence")
            output = StringIO()
            call_command("migrate_configuration_logic_numbering", **args, apply=token, stdout=output)
            self.assertIn("already use automatic numbering", output.getvalue())
            self.api.batchUpdate.assert_called_once()

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

    def test_my2024_transmission_move_and_formatting_do_not_block_value_publication(self):
        from reference.configuration_logic_google import entered

        name = "MY2024"
        row = deepcopy(self.data("MY2025")[4])
        row["values"].extend({} for _ in range(21 - len(row["values"])))
        row["values"][14] = {"userEnteredValue": entered("8-speed automatic")}
        self.data(name).append(row)
        self.save(enroll=True)
        self.move(name, 14, 15)
        baseline = self.save()
        binding = load_layout(self.state, self.path)["sheets"][name]
        row_id = binding["rows"][0]["id"]
        self.assertEqual(binding["columns"]["configuration.transmission"], 16)

        self.move(name, 15, 11)
        before_format = {"horizontalAlignment": "LEFT", "wrapStrategy": "WRAP",
                         "numberFormat": {"type": "TEXT"}, "textFormat": {"bold": True}}
        cell = self.data(name)[4]["values"][11]
        cell["userEnteredFormat"] = before_format.copy()
        grid = self.remote[name]["data"][0]
        grid["columnMetadata"] = [{} for _ in range(11)] + [{"pixelSize": 134}]
        plan = self.base / "transmission.json"
        edit = {"sheet_id": binding["sheet_id"], "row_id": row_id, "field_id": "configuration.transmission",
                "before": "8-speed automatic", "value": "8-speed automatic"}
        plan.write_text(json.dumps({"schema": 2, "base_revision": baseline, "edits": [edit]}))
        pin = self.path.read_bytes()
        self.assertIsNone(publish_working_edits(self.api, self.draft, self.path, self.state, plan))
        self.assertEqual(self.path.read_bytes(), pin)
        self.api.batchUpdate.assert_not_called()

        edit["value"] = "8-Spd Auto"
        plan.write_text(json.dumps({"schema": 2, "base_revision": baseline, "edits": [edit]}))

        def apply(**_):
            request, = self.api.batchUpdate.call_args.kwargs["body"]["requests"]
            update = request["updateCells"]
            self.assertEqual(update["start"], {"sheetId": binding["sheet_id"], "rowIndex": 4, "columnIndex": 11})
            self.assertEqual(update["fields"], "userEnteredValue")
            cell.update(update["rows"][0]["values"][0])
            # Formatting can also change while a value publication is in progress.
            cell["userEnteredFormat"]["wrapStrategy"] = "CLIP"
            grid["columnMetadata"][11]["pixelSize"] = 160

        self.api.batchUpdate.return_value.execute.side_effect = apply
        reads = 0

        def read(**_):
            nonlocal reads
            reads += 1
            if reads == 4:
                grid["columnMetadata"][11]["pixelSize"] = 166
            return self.response()

        self.api.get.return_value.execute.side_effect = read
        successor = publish_working_edits(self.api, self.draft, self.path, self.state, plan)
        self.state = read_registry(self.path, self.draft.key)
        final_binding = load_layout(self.state, self.path)["sheets"][name]
        self.assertEqual(final_binding["rows"], binding["rows"])
        self.assertEqual(final_binding["columns"]["configuration.transmission"], 12)
        snapshot = load_revision(self.state, self.path)[name]["data"][0]
        self.assertEqual(snapshot["rowData"][4]["values"][11], {
            "userEnteredValue": entered("8-Spd Auto"),
            "userEnteredFormat": {**before_format, "wrapStrategy": "CLIP"},
        })
        self.assertEqual(snapshot["columnMetadata"][11]["pixelSize"], 160)
        self.assertEqual(grid["columnMetadata"][11]["pixelSize"], 166)
        self.assertEqual(generated_rows(self.path, self.state)[successor][4], "MY2024 — 1 value changes (Transmission)")

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


class StandaloneConversionTests(SimpleTestCase):
    setUp = b2.WorkingRevisionTests.setUp
    response = b2.WorkingRevisionTests.response
    data = b2.WorkingRevisionTests.data

    def test_revision_bound_conversion_keeps_ids_and_protects_unrelated_pks(self):
        from types import SimpleNamespace

        from reference.configuration_logic_conversion import APPROVED, TACOMA_GENERATION
        from reference.configuration_logic_google import entered
        from reference.configuration_logic_revisions import revision_root

        parent_template = [None] * 21
        parent_template[4:11] = ["Double Cab, 5-ft Bed", "Double Cab", "5-ft", "4WD",
                                 "T24A-FTS", "original-variant", "2.4L 4-Cyl Turbo"]
        parent_template[13:15] = ["United States", "8-speed automatic"]
        parents = []
        pins = []
        vehicles = {}
        for number in range(1, 25):
            parent = parent_template.copy()
            parent[:4] = [number, number, str(8000 + number), f"Trim {number}"]
            parent[11:13] = [100, f"original-{number}"]
            parents.append(parent)
            if number <= 3:
                row_id, (parent_id, code, transmission) = list(APPROVED.items())[number - 1]
                alternative = [None] * 21
                alternative[:2] = [number, number]
                alternative[14:18] = [transmission, f"alternative-{number}", code, 200]
                alternative[19:21] = ["Reviewed alternative", f"Evidence {code}"]
                parents.append(alternative)
                pins.append({"row_id": row_id, "vehicle_pk": 100 + number, "receipt_pk": 200 + number,
                             "vehicle_uuid": f"uuid-{number}"})
                vehicles[code] = SimpleNamespace(
                    pk=100 + number, slug=f"created-{number}", trim_name=parent[3], drivetrain="4WD",
                    engine=SimpleNamespace(engine_code="T24A-FTS", internal_variant_key=alternative[15]),
                    base_msrp=200, transmission=transmission, factory_body_configuration_id=1,
                    factory_body_configuration=object(),
                )
        self.data("MY2025")[4:] = [
            {"values": [{"userEnteredValue": entered(value)} if entered(value) else {} for value in row]}
            for row in parents
        ]
        first = save_remote(self.api, self.draft, self.path, self.state,
                            capture_remote(self.api, self.draft, self.state), None, enroll=True)
        state = read_registry(self.path, self.draft.key)
        # The fixture's predecessor carries the same stable IDs as the approved scope.
        import hashlib
        directory = revision_root(self.path) / first
        layout_file = directory / "layout.json"
        layout = load_layout(state, self.path)
        for number, (row_id, (parent_id, _, _)) in enumerate(APPROVED.items()):
            parent, alternative = layout["sheets"]["MY2025"]["rows"][number * 2:number * 2 + 2]
            parent["id"] = parent_id
            alternative.update(id=row_id, parent_id=parent_id)
        layout_file.write_text(json.dumps(layout))
        manifest_file = directory / "manifest.json"
        manifest = json.loads(manifest_file.read_text())
        manifest["files"]["layout.json"] = hashlib.sha256(layout_file.read_bytes()).hexdigest()
        manifest["generation"] = state["generation"] = TACOMA_GENERATION
        manifest_file.write_text(json.dumps(manifest))
        state["working_revision"]["manifest_sha256"] = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        plan = self.base / "conversion.json"
        payload = {"schema": 2, "base_revision": first, "standalone_conversions": pins}

        def apply(**_):
            for request in self.api.batchUpdate.call_args.kwargs["body"]["requests"]:
                update = request["updateCells"]
                start = update["start"]
                cell = self.data("MY2025")[start["rowIndex"]]["values"][start["columnIndex"]]
                cell.clear()
                cell.update(update["rows"][0]["values"][0])

        self.api.batchUpdate.return_value.execute.side_effect = apply
        with patch("reference.configuration_logic_conversion.created_vehicle",
                   side_effect=lambda pin, revision, row_id, parent_id, code: vehicles[code]), patch(
            "reference.configuration_logic_conversion.factory_body_configuration_label",
            return_value=parent_template[4],
        ):
            plan.write_text(json.dumps({**payload, "base_revision": "stale"}))
            with self.assertRaisesMessage(CommandError, "current base_revision"):
                publish_working_edits(self.api, self.draft, self.path, state, plan)
            plan.write_text(json.dumps({**payload, "edits": [{"field_id": "configuration.pk"}]}))
            with self.assertRaisesMessage(CommandError, "dedicated schema 2"):
                publish_working_edits(self.api, self.draft, self.path, state, plan)
            plan.write_text(json.dumps({**payload, "standalone_conversions": [
                {**pins[0], "row_id": "unrelated"}, *pins[1:],
            ]}))
            with self.assertRaisesMessage(CommandError, "three approved Tacoma rows"):
                publish_working_edits(self.api, self.draft, self.path, state, plan)
            self.api.batchUpdate.assert_not_called()
            plan.write_text(json.dumps(payload))
            revision = publish_working_edits(self.api, self.draft, self.path, state, plan)

        successor = read_registry(self.path, TACOMA_GENERATION)
        self.assertEqual(successor["working_revision"]["id"], revision)
        bindings = load_layout(successor, self.path)["sheets"]["MY2025"]["rows"]
        self.assertEqual([row["id"] for row in bindings],
                         [row["id"] for row in layout["sheets"]["MY2025"]["rows"]])
        self.assertTrue(all(row["parent_id"] is None for row in bindings))
        rows = self.data("MY2025")[4:]
        self.assertEqual([row["values"][0]["userEnteredValue"]["numberValue"] for row in rows],
                         list(range(1, 28)))
        for number, (_, code, transmission) in enumerate(APPROVED.values()):
            values = rows[number * 2 + 1]["values"]
            self.assertEqual(values[1]["userEnteredValue"]["numberValue"], 101 + number)
            self.assertEqual(values[2]["userEnteredValue"]["stringValue"], code)
            self.assertEqual(values[10]["userEnteredValue"]["stringValue"], "2.4L 4-Cyl Turbo")
            self.assertEqual(values[14]["userEnteredValue"]["stringValue"], transmission)
            self.assertEqual(values[20]["userEnteredValue"]["stringValue"], f"Evidence {code}")
            self.assertEqual(values[15:18], [{}, {}, {}])
        self.assertTrue(load_revision(state, self.path))
