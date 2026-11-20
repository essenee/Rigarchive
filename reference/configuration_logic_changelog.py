"""Editable, non-authoritative Sheets projection of verified working history."""
import hashlib
import json

from django.core.management.base import CommandError

from reference.configuration_logic_google import api_call, entered, read_remote, remote_values, write_private
from reference.configuration_logic_layout import catalog
from reference.configuration_logic_revisions import revision_manifests, revision_root, scalar


NAME = "Change Log"
HEADERS = ("Revision", "Date", "Change origin", "Affected worksheets", "Change summary", "Author",
           "Description", "Additional notes")
MANAGED = 6


def log_path(registry):
    return registry.with_suffix(".change-log.json")


def verified_json(directory, manifest, name):
    try:
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["files"][name]:
            raise ValueError
        return json.loads(raw)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CommandError("Change Log cannot read a verified revision artifact.") from exc


def generated_rows(registry, state):
    entries = {}
    for manifest in reversed(list(revision_manifests(registry, state))):
        identifier = manifest["revision"]
        directory = revision_root(registry) / identifier
        changes = verified_json(directory, manifest, "changes.json")
        receipt = verified_json(directory, manifest, "receipt.json")
        summaries = []
        for name, change in changes.items():
            cells, notes = change.get("cells", []), change.get("notes", [])
            if not (cells or notes or change.get("semantic_metadata_changed")):
                continue
            fields = catalog(name)
            labels = sorted({fields[cell["column"] - 1][1] for cell in cells if 1 <= cell["column"] <= len(fields)})
            detail = ", ".join(labels[:3]) + (" and others" if len(labels) > 3 else "")
            adds = (len(change["working_rows_added"]) if "working_rows_added" in change
                    else sum(x[4] for x in change.get("row_changes", ()) if x[0] == "insert"))
            removals = (len(change["working_rows_removed"]) if "working_rows_removed" in change
                        else sum(x[2] for x in change.get("row_changes", ()) if x[0] == "delete"))
            parts = []
            if cells:
                parts.append(f"{len(cells)} value changes" + (f" ({detail})" if detail else ""))
            if notes:
                parts.append(f"{len(notes)} note changes")
            if adds or removals:
                parts.append(f"{adds} rows added, {removals} removed")
            if change.get("semantic_metadata_changed"):
                parts.append("cell interpretation metadata changed")
            summaries.append((name, ", ".join(parts)))
        if not summaries:
            continue
        operation = receipt.get("operation")
        origin = {"capture": "Human capture", "targeted-publication": "Agent publication",
                  "inactive-migration": "Canonical inventory migration"}.get(operation, "Not recorded")
        entries[identifier] = [
            identifier, receipt.get("time") or manifest.get("captured_at") or "Not recorded",
            origin, ", ".join(name for name, _ in summaries),
            " / ".join(f"{name} — {summary}" for name, summary in summaries),
            receipt.get("operator") or "Not recorded",
        ]
    return entries


def read_projection(path, state):
    try:
        record = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise CommandError("Change Log registry is unreadable. Restore its trusted copy.") from exc
    if (not isinstance(record, dict) or record.get("schema") != 1
            or record.get("spreadsheet") != state["spreadsheet"] or record.get("generation") != state["generation"]
            or type(record.get("sheet_id")) is not int or not isinstance(record.get("entries"), dict)
            or ("pending" in record and not isinstance(record["pending"], dict))
            or ("pending_before" in record and (
                "pending" not in record or (record["pending_before"] is not None
                                            and not isinstance(record["pending_before"], dict))))):
        raise CommandError("Change Log registry is invalid or belongs to another workbook.")
    return record


def observed_entries(sheet):
    values = remote_values(sheet)
    if [scalar(values.get((0, c))) for c in range(len(HEADERS))] != list(HEADERS):
        raise CommandError("Change Log header or column order differs.")
    if any(c >= len(HEADERS) or "formulaValue" in value for (_, c), value in values.items()):
        raise CommandError("Change Log contains an unsupported formula or column.")
    managed, annotations, positions = {}, {}, {}
    for row in sorted({r for r, _ in values if r >= 1}):
        fields = [scalar(values.get((row, c))) for c in range(len(HEADERS))]
        key = fields[0]
        if not isinstance(key, str) or not key or key in managed:
            raise CommandError("Change Log has missing or duplicate entry IDs.")
        managed[key] = fields[:MANAGED]
        annotations[key] = fields[MANAGED:]
        positions[key] = row
    return managed, annotations, positions, max((r for r, _ in values), default=0) + 1


def read_workbook(api, draft, state, sheet_id):
    remote = read_remote(api, state["spreadsheet"], draft.title)
    log = remote.pop(NAME, None)
    if list(remote) != list(state["sheets"]) or any(
        sheet["properties"]["sheetId"] != state["sheets"][name]["id"]
        or sheet["properties"].get("index", 0) != index
        for index, (name, sheet) in enumerate(remote.items())
    ):
        raise CommandError("Configuration worksheet identity changed; Change Log synchronization stopped.")
    if log is not None and (log["properties"]["sheetId"] != sheet_id
                            or log["properties"].get("index", 0) != len(remote)):
        raise CommandError("Conflicting or moved worksheet named Change Log.")
    return remote, log


def sync_change_log(api, draft, registry, state, *, enable=False, rebuild=False):
    path = log_path(registry)
    record = read_projection(path, state)
    if record is None and not enable:
        return None
    entries = generated_rows(registry, state)
    remote, sheet = read_workbook(api, draft, state, record["sheet_id"] if record else None)
    if record is None:
        record = {"schema": 1, "spreadsheet": state["spreadsheet"], "generation": state["generation"],
                  "sheet_id": max(s["properties"]["sheetId"] for s in remote.values()) + 1, "entries": {}}
    prior = record["entries"]
    target = record.get("pending")
    if sheet is None and (prior or record.get("through_revision")):
        raise CommandError("Registered Change Log is missing. Restore it to preserve manual annotations.")
    observed, notes, positions, start = observed_entries(sheet) if sheet else ({}, {}, {}, 1)
    repair = {}
    if target is not None and any(entries.get(key) != value for key, value in target.items()):
        raise CommandError("Pending Change Log entries differ from verified local history.")
    if target is not None and sheet is not None and observed == target:
        # The previous request landed. Keep human annotations outside managed state.
        prior = target
        record = {k: v for k, v in record.items() if k not in ("pending", "pending_before")} | {"entries": prior}
        write_private(path, json.dumps(record, indent=2))
    elif target is not None and "pending_before" in record:
        if (observed if sheet is not None else None) != record["pending_before"]:
            raise CommandError("Change Log differs from both pending recovery states. Inspect and reconcile before retrying.")
        if set(observed) != set(prior):
            raise CommandError("Pending Change Log repair has different revision IDs. Inspect before retrying.")
        repair = {key: prior[key] for key in prior if observed[key] != prior[key]}
    elif observed != prior:
        if not rebuild or target is not None or set(observed) != set(prior):
            raise CommandError("Change Log managed fields were changed or its update is ambiguous. Inspect before retrying.")
        repair = {key: prior[key] for key in prior if observed[key] != prior[key]}
    if any(entries.get(key) != value for key, value in prior.items()):
        raise CommandError("Registered Change Log entries differ from verified local history.")
    if sheet is not None and observed == entries:
        acknowledge_projection(path, record, state)
        return "Change Log already matches."

    requests = []
    sheet_id = record["sheet_id"]
    if sheet is None:
        requests.append({"addSheet": {"properties": {
            "sheetId": sheet_id, "title": NAME, "index": len(remote),
            "gridProperties": {"frozenRowCount": 1, "rowCount": max(100, len(entries) + 1), "columnCount": len(HEADERS)},
        }}})
        requests.append(update_log_cells(sheet_id, 0, [HEADERS]))
        requests.append({"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                                        "fields": "userEnteredFormat.textFormat.bold"}})
        # Warn on manual edits to machine fields; the managed contents are still verified on every sync.
        requests.append({"addProtectedRange": {"protectedRange": {
            "range": {"sheetId": sheet_id, "startColumnIndex": 0, "endColumnIndex": MANAGED},
            "description": "RigArchive managed Change Log fields", "warningOnly": True,
        }}})
    requests.extend(update_log_cells(sheet_id, positions[key], [row]) for key, row in repair.items())
    missing = [row for key, row in entries.items() if key not in prior]
    if missing:
        if sheet is not None and start + len(missing) > sheet["properties"]["gridProperties"]["rowCount"]:
            requests.append({"appendDimension": {"sheetId": sheet_id, "dimension": "ROWS", "length": len(missing)}})
        requests.append(update_log_cells(sheet_id, start, missing))
    record["pending"] = entries
    record["pending_before"] = observed if sheet is not None else None
    write_private(path, json.dumps(record, indent=2))
    checked_remote, checked_sheet = read_workbook(api, draft, state, sheet_id)
    if checked_sheet != sheet or checked_remote != remote:
        raise CommandError("Workbook changed while planning Change Log synchronization.")
    api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=state["spreadsheet"], body={"requests": requests})
    _, result = read_workbook(api, draft, state, sheet_id)
    if result is None:
        raise CommandError("Change Log creation was not verified.")
    actual, actual_notes, _, _ = observed_entries(result)
    if actual != entries or any(actual_notes.get(key) != value for key, value in notes.items()):
        raise CommandError("Change Log synchronization was not verified. Preserve the local revision and inspect the tab.")
    record["entries"] = entries
    acknowledge_projection(path, record, state)
    return "Change Log synchronized."


def acknowledge_projection(path, record, state):
    current = {k: v for k, v in record.items() if k not in ("pending", "pending_before", "stale")}
    current["through_revision"] = state["working_revision"]["id"]
    if current != record:
        write_private(path, json.dumps(current, indent=2))


def update_log_cells(sheet_id, start, rows):
    return {"updateCells": {
        "start": {"sheetId": sheet_id, "rowIndex": start, "columnIndex": 0},
        "rows": [{"values": [{"userEnteredValue": entered(value)} for value in row]} for row in rows],
        "fields": "userEnteredValue",
    }}


def sync_after_revision(api, draft, registry, state, report):
    try:
        message = sync_change_log(api, draft, registry, state)
        if message:
            report(message)
    except (CommandError, OSError) as exc:
        try:
            path = log_path(registry)
            record = read_projection(path, state)
            if record and not record.get("stale"):
                write_private(path, json.dumps({**record, "stale": True}, indent=2))
        except (CommandError, OSError):
            pass  # Preserve unreadable state; the last acknowledged revision is still stale.
        report(f"Working revision preserved. Change Log is pending synchronization: {exc}")
