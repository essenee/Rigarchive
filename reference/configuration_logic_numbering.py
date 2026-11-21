"""Controlled migration of enrolled model-year tabs to a calculated number column."""
from copy import deepcopy

from django.core.management.base import CommandError

from reference.configuration_logic_google import api_call, digest, read_registry, remote_values
from reference.configuration_logic_layout import column_order, header_index, numbering_formula, uses_numbering
from reference.configuration_logic_revisions import (
    capture_remote, check_working_remote, load_layout, load_revision, save_remote, verify_working_remote,
    working_nonvalue_state,
)


def plan_numbering(draft, before, live):
    """Project a single value-only update per model-year tab, then prove correspondence."""
    projected = deepcopy(live)
    requests = []
    for name, sheet in projected.items():
        if not name.startswith("MY"):
            continue
        if uses_numbering(name, before[name]) != uses_numbering(name, sheet):
            raise CommandError(f"{name} numbering differs from the registered revision. Inspect before retrying.")
        if uses_numbering(name, sheet):
            continue
        header = header_index(name, sheet)
        order = column_order(name, sheet)
        column = order.index(0)
        formula = {"formulaValue": numbering_formula(order)}
        last = max(r for r, _ in remote_values(sheet))
        anchor_found = False
        for block in sheet.get("data", ()):
            for i, row in enumerate(block.get("rowData", ()), block.get("startRow", 0)):
                cells = row.get("values", ())
                index = column - block.get("startColumn", 0)
                if header <= i and 0 <= index < len(cells):
                    cell = cells[index]
                    if cell.get("textFormatRuns"):
                        raise CommandError(f"{name} has rich-text data in the number column.")
                    if i == header:
                        anchor_found = True
                        cell["userEnteredValue"] = formula
                    else:
                        cell.pop("userEnteredValue", None)
        if not anchor_found:
            raise CommandError(f"{name} number-column header is missing.")
        requests.append({"updateCells": {
            "start": {"sheetId": sheet["properties"]["sheetId"], "rowIndex": header, "columnIndex": column},
            "rows": [{"values": [{"userEnteredValue": formula}]}, *({"values": [{}]} for _ in range(last - header))],
            "fields": "userEnteredValue",
        }})
    verify_working_remote(draft, before, projected, flexible=True, numbering_migration=bool(requests))
    return projected, requests


def publish_numbering(api, draft, path, state, *, apply_hash=None):
    if load_layout(state, path) is None:
        raise CommandError("Automatic numbering requires an enrolled B3 revision.")
    before = load_revision(state, path)
    live = capture_remote(api, draft, state)
    expected, requests = plan_numbering(draft, before, live)
    preview_hash = digest({"base": state["working_revision"], "requests": requests})
    if not requests or apply_hash is None:
        return len(requests), preview_hash, None
    if apply_hash != preview_hash:
        raise CommandError("Numbering preview is stale. Run a new dry-run before applying.")
    latest = capture_remote(api, draft, state)
    if any(remote_values(latest[name]) != remote_values(sheet)
           or working_nonvalue_state(latest[name], name, flexible=True)
           != working_nonvalue_state(sheet, name, flexible=True) for name, sheet in live.items()):
        raise CommandError("Workbook changed during numbering preflight. Nothing was written.")
    api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=state["spreadsheet"],
             body={"requests": requests})
    result = capture_remote(api, draft, state)
    if any(remote_values(result[name]) != remote_values(sheet)
           or working_nonvalue_state(result[name], name, flexible=True)
           != working_nonvalue_state(sheet, name, flexible=True) for name, sheet in expected.items()):
        raise CommandError("Numbering verification failed after writing. Inspect the workbook before retrying.")
    revision = save_remote(api, draft, path, state, result, before, operation="numbering-migration")
    successor = read_registry(path, draft.key)
    if not revision or successor["working_revision"]["id"] != revision:
        raise CommandError("Numbering successor could not be verified. Inspect the registry before retrying.")
    check_working_remote(api, draft, successor, load_revision(successor, path), flexible=True)
    return len(requests), preview_hash, revision
