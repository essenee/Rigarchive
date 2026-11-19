from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from reference.configuration_logic import GenerationDraft, Sheet
from reference.configuration_logic_google import api_call, connect, create, publish, read_registry, recover_registry, release_reservation, write_private


def table(name, *values):
    return Sheet(name, (("Title",), ("Draft",), (), ("Header",), *((v,) for v in values)), (15,))


class GooglePublicationTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "registry.json"
        self.draft = GenerationDraft("generation", "Title", (table("MY2026", "value"), table("Source References")))
        self.remote = []
        self.api = Mock()
        self.api.create.return_value.execute.side_effect = self.create_remote
        self.api.get.return_value.execute.side_effect = lambda **_: {
            "spreadsheetId": "file-id", "properties": {"title": "Title"}, "sheets": deepcopy(self.remote),
        }
        self.api.batchUpdate.side_effect = self.batch

    def add(self, properties):
        index = properties.pop("index", len(self.remote))
        self.remote.insert(index, {"properties": properties})

    def create_remote(self, **kwargs):
        for table in self.api.create.call_args.kwargs["body"]["sheets"]:
            self.add(deepcopy(table["properties"]))
        return {"spreadsheetId": "file-id"}

    def batch(self, *, spreadsheetId, body):
        def apply(**kwargs):
            for request in deepcopy(body["requests"]):
                action, params = next(iter(request.items()))
                if action == "addSheet":
                    self.add(params["properties"])
                elif action in ("updateSheetProperties", "updateCells", "setBasicFilter"):
                    sheet_id = params["properties"]["sheetId"] if action == "updateSheetProperties" else (
                        params["range"]["sheetId"] if action == "updateCells" else params["filter"]["range"]["sheetId"])
                    sheet = next(s for s in self.remote if s["properties"]["sheetId"] == sheet_id)
                    if action == "updateCells":
                        sheet["data"] = [{"rowData": params["rows"]}]
                    elif action == "setBasicFilter":
                        sheet["basicFilter"] = params["filter"]
                    elif params["fields"] == "index":
                        self.remote.remove(sheet)
                        self.remote.insert(params["properties"]["index"], sheet)
                    else:
                        sheet["properties"].update(params["properties"])
            for index, sheet in enumerate(self.remote):
                sheet["properties"]["index"] = index
            return {}
        return Mock(execute=apply)

    def initial_publish(self):
        state = create(self.api, self.draft, self.path)
        publish(self.api, self.draft, self.path, state)
        return read_registry(self.path, self.draft.key)

    def test_repeated_publish_reuses_file_and_tabs_and_is_no_op(self):
        state = self.initial_publish()
        self.assertEqual(state["spreadsheet"], "file-id")
        self.assertEqual({name: p["id"] for name, p in state["sheets"].items()},
                         {"MY2026": 1, "Source References": 2})
        self.assertEqual(publish(self.api, self.draft, self.path, state), [])
        self.api.create.assert_called_once()
        self.api.batchUpdate.assert_called_once()

    def test_publish_creates_missing_year_and_preserves_existing_ids(self):
        state = self.initial_publish()
        expanded = GenerationDraft("generation", "Title",
                                   (self.draft.sheets[0], table("MY2025"), self.draft.sheets[1]))
        before = self.path.read_bytes()
        self.assertIn("Create MY2025", publish(self.api, expanded, self.path, state, dry_run=True))
        self.assertEqual(self.path.read_bytes(), before)
        self.api.batchUpdate.assert_called_once()
        publish(self.api, expanded, self.path, state)
        self.assertEqual([(x["properties"]["title"], x["properties"]["sheetId"]) for x in self.remote],
                         [("MY2026", 1), ("MY2025", 3), ("Source References", 2)])

    def test_external_values_and_protection_block_changes(self):
        state = self.initial_publish()
        sheet = self.remote[0]
        sheet["data"][0]["rowData"].append({"values": [{"userEnteredValue": {"stringValue": "Edited"}}]})
        with self.assertRaisesMessage(CommandError, "Unexpected external change"):
            publish(self.api, self.draft, self.path, state)
        sheet["protectedRanges"] = [{"protectedRangeId": 1}]
        with self.assertRaisesMessage(CommandError, "Protected worksheet"):
            publish(self.api, self.draft, self.path, state)
        self.api.batchUpdate.assert_called_once()

    def test_missing_invalid_approved_and_unfingerprinted_registry(self):
        self.assertIsNone(read_registry(self.path, self.draft.key))
        self.path.write_text("malformed")
        with self.assertRaisesMessage(CommandError, "registry is unreadable"):
            read_registry(self.path, self.draft.key)
        state = self.initial_publish()
        write_private(self.path, json.dumps({**state, "mode": "approved"}))
        with self.assertRaisesMessage(CommandError, "Protected"):
            read_registry(self.path, self.draft.key)
        with self.assertRaisesMessage(CommandError, "without a trusted fingerprint"):
            publish(self.api, self.draft, self.path, {**state, "sheets": {}})

    def test_authentication_and_ambiguous_create_are_safe(self):
        with self.assertRaisesMessage(CommandError, "Google token missing"):
            connect(self.path.parent)
        with self.assertRaisesMessage(CommandError, "credentials.json is missing"):
            connect(self.path.parent, authorize=True)
        self.api.create.return_value.execute.side_effect = OSError("Sensitive OAuth detail")
        with self.assertRaisesMessage(CommandError, "Google request failed"):
            create(self.api, self.draft, self.path)
        with self.assertRaisesMessage(CommandError, "Incomplete or invalid registry"):
            read_registry(self.path, self.draft.key)

    def test_google_error_diagnostics_disclose_only_recognized_codes(self):
        for operation, status, payload, reason, action in (
            ("spreadsheets.create", 403, {"details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
                                                       "metadata": {"token": "sensitive-content"}}]},
             "ACCESS_TOKEN_SCOPE_INSUFFICIENT", "grant drive.file access"),
            ("spreadsheets.create", 403, {"errors": [{"reason": "insufficientPermissions"}]},
             "insufficientPermissions", "Preserve the creation reservation"),
            ("spreadsheets.create", 403, {"details": [{"reason": "SERVICE_DISABLED"}]},
             "SERVICE_DISABLED", "Enable the Google Sheets API"),
            ("spreadsheets.get", 403, {"status": "PERMISSION_DENIED"},
             "PERMISSION_DENIED", "access to the registered spreadsheet"),
            ("spreadsheets.batchUpdate", 401, {"status": "UNAUTHENTICATED"},
             "UNAUTHENTICATED", "Run --authorize"),
        ):
            with self.subTest(operation=operation, reason=reason):
                exc = OSError("sensitive-content")
                exc.resp = SimpleNamespace(status=status)
                exc.content = json.dumps({"error": {**payload, "message": "sensitive-content"}}).encode()
                method = Mock()
                method.return_value.execute.side_effect = exc
                with self.assertRaisesMessage(CommandError, f"Sheets {operation} (HTTP {status}, {reason})") as error:
                    api_call(operation, method)
                self.assertIn(action, str(error.exception))
                self.assertNotIn("sensitive-content", str(error.exception))
                method.return_value.execute.assert_called_once_with(num_retries=0)

    def test_denied_create_leaves_pending_registry_without_retries(self):
        error = OSError("sensitive-content")
        error.resp = SimpleNamespace(status=403)
        error.content = b'{"error":{"status":"PERMISSION_DENIED","details":[{"reason":"sensitive-content"}]}}'
        self.api.create.return_value.execute.side_effect = error
        with self.assertRaisesMessage(CommandError, "spreadsheets.create (HTTP 403, PERMISSION_DENIED)") as caught:
            create(self.api, self.draft, self.path)
        self.assertNotIn("sensitive-content", str(caught.exception))
        state = read_registry(self.path, self.draft.key, allow_pending=True)
        self.assertIsNone(state["spreadsheet"])
        self.assertEqual(state["sheets"], {})
        self.api.create.assert_called_once()
        self.api.batchUpdate.assert_not_called()

    def test_shrinking_requires_explicit_authorization(self):
        state = self.initial_publish()
        smaller = GenerationDraft("generation", "Title", (table("MY2026"), table("Source References")))
        with self.assertRaisesMessage(CommandError, "--allow-shrink"):
            publish(self.api, smaller, self.path, state)
        publish(self.api, smaller, self.path, state, allow_shrink=True)
        self.assertEqual(self.api.batchUpdate.call_count, 2)

    def test_recovery_requires_exact_existing_contents_and_never_updates_google(self):
        self.initial_publish()
        self.path.unlink()
        sheet = self.remote[0]
        original = deepcopy(sheet)
        sheet["data"][0]["rowData"][1]["values"][0]["userEnteredValue"]["stringValue"] = "Approved"
        with self.assertRaisesMessage(CommandError, "without a trusted fingerprint"):
            recover_registry(self.api, self.draft, self.path, "file-id", authorized=True)
        self.assertFalse(self.path.exists())
        self.remote[0] = original
        recover_registry(self.api, self.draft, self.path, "file-id", authorized=True)
        self.assertEqual(read_registry(self.path, self.draft.key)["spreadsheet"], "file-id")
        self.api.batchUpdate.assert_called_once()

    def pending(self):
        state = {"schema": 1, "generation": self.draft.key, "mode": "draft",
                 "spreadsheet": None, "sheets": {}}
        self.path.write_text(json.dumps(state))
        return state

    def test_release_requires_explicit_confirmation_and_preserves_audit(self):
        previous = self.pending()
        before = self.path.read_bytes()
        with self.assertRaisesMessage(CommandError, "--confirm-recovery"):
            release_reservation(self.draft, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        name = release_reservation(self.draft, self.path, authorized=True)
        audit = json.loads((self.path.parent / "recovery-audit" / name).read_text())
        self.assertEqual(audit["previous_reservation"], previous)
        self.assertEqual(audit["decision"], "owner-confirmed-no-spreadsheet")
        self.assertEqual(read_registry(self.path, self.draft.key, allow_pending=True)["release_audit"], name)
        with self.assertRaisesMessage(CommandError, "separate --publish --initialize"):
            read_registry(self.path, self.draft.key)
        with self.assertRaisesMessage(CommandError, "unreleased creation reservation"):
            release_reservation(self.draft, self.path, authorized=True)
        self.assertEqual(len(list((self.path.parent / "recovery-audit").iterdir())), 1)
        self.api.create.assert_not_called()
        self.api.get.assert_not_called()
        self.api.batchUpdate.assert_not_called()

    def test_pending_adoption_verifies_identity_and_does_not_publish(self):
        previous = self.pending()
        for index, draft_sheet in enumerate(self.draft.sheets):
            self.add({"title": draft_sheet.name, "sheetId": index + 1, "index": index})
            self.remote[index]["properties"]["index"] = index
        with self.assertRaisesMessage(CommandError, "--confirm-recovery"):
            recover_registry(self.api, self.draft, self.path, "file-id")
        self.api.get.assert_not_called()
        with self.assertRaisesMessage(CommandError, "identity or title differs"):
            recover_registry(self.api, self.draft, self.path, "wrong-file", authorized=True)
        self.assertEqual(read_registry(self.path, self.draft.key, allow_pending=True), previous)
        for _ in range(2):
            self.assertFalse(recover_registry(self.api, self.draft, self.path, "file-id", authorized=True))
        self.assertEqual(read_registry(self.path, self.draft.key)["spreadsheet"], "file-id")
        self.assertEqual(len(list((self.path.parent / "recovery-audit").iterdir())), 1)
        self.api.create.assert_not_called()
        self.api.batchUpdate.assert_not_called()

    def test_registered_workbook_cannot_be_released_or_replaced(self):
        self.initial_publish()
        before = self.path.read_bytes()
        self.api.get.reset_mock()
        with self.assertRaisesMessage(CommandError, "without a spreadsheet ID"):
            release_reservation(self.draft, self.path, authorized=True)
        with self.assertRaisesMessage(CommandError, "Trusted fingerprints already exist"):
            recover_registry(self.api, self.draft, self.path, "another-id", authorized=True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse((self.path.parent / "recovery-audit").exists())
        self.api.get.assert_not_called()
        self.api.create.assert_called_once()
        self.api.batchUpdate.assert_called_once()

    def test_missing_spreadsheet_field_is_not_a_pending_reservation(self):
        state = self.pending()
        del state["spreadsheet"]
        before = json.dumps(state)
        self.path.write_text(before)
        with self.assertRaisesMessage(CommandError, "Incomplete or invalid registry"):
            release_reservation(self.draft, self.path, authorized=True)
        self.assertEqual(self.path.read_text(), before)
        self.assertFalse((self.path.parent / "recovery-audit").exists())
