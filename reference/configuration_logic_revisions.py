"""Capture and resume local Configuration Logic working revisions."""
import csv
from difflib import SequenceMatcher
import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from django.core.management.base import CommandError
from django.utils.timezone import now

from reference.configuration_logic import GenerationDraft, HEADERS, SOURCE_HEADERS, Sheet, WIDTHS, generation_draft
from reference.configuration_logic_google import (
    FIELDS, api_call, desired_values, digest, entered, fingerprint,
    read_remote, remote_values, write_private,
)


def revision_root(path):
    return path.parent / "revisions" / path.stem


def load_revision(state, path):
    pin = state.get("working_revision") if state else None
    if pin is None:
        if revision_root(path).exists() and not state:
            raise CommandError("Working revision history exists without its registry. Restore the registry.")
        return None
    try:
        identifier = pin["id"]
        if UUID(identifier).hex != identifier:
            raise ValueError
        directory = revision_root(path) / identifier
        raw = (directory / "manifest.json").read_bytes()
        manifest = json.loads(raw)
        if (hashlib.sha256(raw).hexdigest() != pin["manifest_sha256"]
                or manifest["revision"] != identifier or manifest["schema"] != 1 or manifest["status"] != "working-draft"
                or manifest["generation"] != state["generation"]
                or manifest["spreadsheet"] != state["spreadsheet"]):
            raise ValueError
        workbook = (directory / "workbook.json").read_bytes()
        if hashlib.sha256(workbook).hexdigest() != manifest["files"]["workbook.json"]:
            raise ValueError
        remote = json.loads(workbook)
        if {name: fingerprint(sheet) for name, sheet in remote.items()} != {
            name: item["fingerprint"] for name, item in state["sheets"].items()
        }:
            raise ValueError
        return remote
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise CommandError("Working revision or registry pin is invalid. Restore the trusted local files.") from exc


def working_history(path, state):
    load_revision(state, path)
    pin = state.get("working_revision")
    seen = set()
    while pin:
        try:
            identifier = pin["id"]
            if UUID(identifier).hex != identifier or identifier in seen:
                raise ValueError
            raw = (revision_root(path) / identifier / "manifest.json").read_bytes()
            manifest = json.loads(raw)
            if (hashlib.sha256(raw).hexdigest() != pin["manifest_sha256"]
                    or manifest["revision"] != identifier or manifest["generation"] != state["generation"]
                    or manifest["spreadsheet"] != state["spreadsheet"] or manifest["status"] != "working-draft"):
                raise ValueError
            seen.add(identifier)
            pin = manifest["previous"]
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise CommandError("Working revision history is incomplete or invalid.") from exc
        yield identifier, manifest["captured_at"]


def sheet_cells(sheet):
    return {
        (block.get("startRow", 0) + r, block.get("startColumn", 0) + c): cell
        for block in sheet.get("data", ())
        for r, row in enumerate(block.get("rowData", ()))
        for c, cell in enumerate(row.get("values", ())) if cell
    }


def scalar(entry):
    return next(iter(entry.values())) if entry else None


def validated_rows(table, sheet):
    values = remote_values(sheet)
    width = len(table.widths)
    height = max((r + 1 for r, _ in values), default=4)
    if sheet.get("protectedRanges"):
        raise CommandError(f"{table.name} is protected.")
    if any(merge.get("endRowIndex", 0) > 3 for merge in sheet.get("merges", ())):
        raise CommandError(f"{table.name} contains a merge intersecting the column headers or data.")
    if any(c >= width or "formulaValue" in item for (r, c), item in values.items()):
        raise CommandError(f"{table.name} contains formulas or values outside the working schema.")
    rows = tuple(tuple(scalar(values.get((r, c))) for c in range(width)) for r in range(height))
    if len(rows) < 4 or rows[3] != table.rows[3]:
        raise CommandError(f"{table.name} column headers are missing, duplicated, reordered, or renamed.")
    if rows[0][0] != table.rows[0][0] or not str(rows[1][0]).startswith("Draft"):
        raise CommandError(f"{table.name} must retain its title and draft status.")
    if table.name == "Source References":
        if any(any(value is not None and value != "" for value in row)
               and (type(row[0]) is not int or not row[2]) for row in rows[4:]):
            raise CommandError("Source References rows require a model year and source title.")
    else:
        parents, identifiers = {}, set()
        for row in rows[4:]:
            if not any(value is not None and value != "" for value in row):
                continue
            number, pk = row[:2]
            if type(number) is not int or number < 1 or (pk is not None and (type(pk) is not int or pk < 1)):
                raise CommandError(f"{table.name} requires a positive configuration number and an optional positive PK.")
            if row[3]:
                if not row[7] or number in parents or (pk is not None and pk in identifiers):
                    raise CommandError(f"{table.name} has missing drivetrain or duplicate configuration identity.")
                parents[number] = pk
                if pk is not None:
                    identifiers.add(pk)
            elif number not in parents or pk != parents[number] or not any(row[14:20]):
                raise CommandError(f"{table.name} has an alternative without a matching parent and applicability.")
    return rows


def current_draft(generation, path, state):
    remote = load_revision(state, path)
    if remote is None:
        return generation_draft(generation)
    from reference.configuration_logic import generation_title

    title = generation_title(generation)
    tables = []
    for name, sheet in sorted(remote.items(), key=lambda item: item[1]["properties"].get("index", 0)):
        headers, widths, prices = (HEADERS, WIDTHS, (11, 17))
        if name == "Source References":
            headers, widths, prices = SOURCE_HEADERS, (14, 18, 32, 60, 20, 29, 42, 28, 65), ()
        template = Sheet(name, ((title,), ("Draft",), (), headers), widths, prices)
        tables.append(Sheet(name, validated_rows(template, sheet), widths, prices))
    return GenerationDraft(str(generation.uuid), title, tuple(tables))


def changes_between(before, remote, tables):
    changes = {}
    for table in tables:
        name = table.name
        new = remote[name]
        old = before[name] if before else None
        if old is None:
            changes[name] = {"baseline": "unavailable", "captured_values": len(remote_values(new))}
            continue
        a, b = remote_values(old), remote_values(new)
        notes = lambda sheet: {position: cell["note"] for position, cell in sheet_cells(sheet).items() if "note" in cell}
        old_notes, new_notes = notes(old), notes(new)
        old_rows, new_rows = data_rows(a), data_rows(b)
        row_edits = SequenceMatcher(a=old_rows, b=new_rows, autojunk=False).get_opcodes()
        changes[name] = {
            "cells": cell_changes(a, b), "notes": cell_changes(old_notes, new_notes),
            "row_changes": [[kind, a1 + 5, a2 - a1, b1 + 5, b2 - b1]
                            for kind, a1, a2, b1, b2 in row_edits if kind != "equal"],
            "headers_changed": any(a.get(p) != b.get(p) for p in a.keys() | b.keys() if p[0] == 3),
            "sheet_metadata_changed": {k: v for k, v in old.items() if k != "data"} !=
                                      {k: v for k, v in new.items() if k != "data"},
            "fingerprint_changed": fingerprint(old) != fingerprint(new),
        }
    return changes


def cell_changes(old, new):
    return [{"row": r + 1, "column": c + 1, "before": old.get((r, c)), "after": new.get((r, c))}
            for r, c in sorted(old.keys() | new.keys()) if old.get((r, c)) != new.get((r, c))]


def data_rows(values):
    height = max((r for r, _ in values), default=3)
    return [digest(sorted((c, v) for (line, c), v in values.items() if line == r))
            for r in range(4, height + 1)]


# Keep Milestone A's field mask and full fingerprints intact. Working revisions
# compare the captured grid and explicitly request additional structural metadata.
WORKING_FIELDS = FIELDS.replace(
    "filterViews,charts,data", "filterViews,charts,conditionalFormats,rowGroups,columnGroups,data",
).replace("(pixelSize)", "(pixelSize,hiddenByUser,hiddenByFilter)")
COSMETIC_CELL_FORMAT = {
    "wrapStrategy", "backgroundColor", "backgroundColorStyle", "borders",
    "horizontalAlignment", "verticalAlignment", "padding", "textRotation", "textDirection",
}
COSMETIC_TEXT_FORMAT = {
    "fontFamily", "fontSize", "bold", "italic", "strikethrough", "underline",
    "foregroundColor", "foregroundColorStyle",
}


def classify_sheet(sheet, name):
    """Return semantic, structural and presentation views of captured Sheets data."""
    semantic, cosmetics = {}, {}
    values = remote_values(sheet)
    structure = {key: value for key, value in sheet.items() if key != "data"}
    for key in ("conditionalFormats", "rowGroups", "columnGroups"):
        if not structure.get(key):
            structure.pop(key, None)
    headers = {position: value for position, value in values.items() if position[0] == 3}
    row_identity = {} if name == "Source References" else {
        position: value for position, value in values.items()
        if position[0] >= 4 and position[1] in (0, 1, 12)
    }
    occupied_rows = {r for r, _ in values if r >= 4}
    for position, cell in sheet_cells(sheet).items():
        content = {key: value for key, value in cell.items() if key != "userEnteredFormat"}
        fmt = cell.get("userEnteredFormat", {})
        paint = {key: value for key, value in fmt.items() if key in COSMETIC_CELL_FORMAT}
        other = {key: value for key, value in fmt.items()
                 if key not in COSMETIC_CELL_FORMAT and key != "textFormat"}
        font = fmt.get("textFormat", {})
        paint_font = {key: value for key, value in font.items() if key in COSMETIC_TEXT_FORMAT}
        other_font = {key: value for key, value in font.items() if key not in COSMETIC_TEXT_FORMAT}
        if paint_font:
            paint["textFormat"] = paint_font
        if other_font:
            other["textFormat"] = other_font
        if other:
            content["userEnteredFormat"] = other
        if content:
            semantic[position] = content
        if paint:
            cosmetics[position] = paint

    dimensions, sizes = {}, {}
    for block in sheet.get("data", ()):
        for axis, offset in (("row", "startRow"), ("column", "startColumn")):
            for index, item in enumerate(block.get(f"{axis}Metadata", ())):
                position = (axis, block.get(offset, 0) + index)
                other = {key: value for key, value in item.items() if key != "pixelSize"
                         and not (key in ("hiddenByUser", "hiddenByFilter") and value is False)}
                if other:
                    dimensions[position] = other
                if "pixelSize" in item:
                    sizes[position] = item["pixelSize"]
    return semantic, (structure, headers, occupied_rows, row_identity, dimensions), (cosmetics, sizes)


def check_working_remote(api, draft, state, previous, *, report=None):
    remote = capture_remote(api, draft, state)
    if set(remote) != set(previous):
        raise CommandError("Working revision worksheet identity differs from the remote workbook.")
    presentation = []
    for table in draft.sheets:
        name = table.name
        validated_rows(table, remote[name])
        old_semantic, old_structure, old_presentation = classify_sheet(previous[name], name)
        semantic, structure, appearance = classify_sheet(remote[name], name)
        if structure != old_structure:
            raise CommandError(f"Unexpected external change in {name}: structural differences; publication stopped.")
        if semantic != old_semantic:
            raise CommandError(f"Unexpected external change in {name}: values, notes, or noncosmetic cell metadata differ.")
        if appearance != old_presentation:
            presentation.append(name)
    if report and presentation:
        report("Nonblocking presentation changes detected and preserved in: " + ", ".join(presentation) + ".")
    return remote


def capture_remote(api, draft, state):
    remote = read_remote(api, state["spreadsheet"], draft.title, fields=WORKING_FIELDS)
    if list(remote) != [table.name for table in draft.sheets] or set(remote) != set(state["sheets"]):
        raise CommandError("Remote worksheet names or order differ from the registered generation.")
    for index, (name, sheet) in enumerate(remote.items()):
        props = sheet["properties"]
        if props["sheetId"] != state["sheets"][name]["id"] or props.get("index", 0) != index:
            raise CommandError(f"{name} has a changed worksheet ID or index.")
    return remote


def csv_value(value):
    # CSV readers can interpret text as formulas even when Sheets stored it literally.
    return "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value


def nonvalue_state(sheet):
    cells = {position: {k: v for k, v in cell.items() if k != "userEnteredValue"}
             for position, cell in sheet_cells(sheet).items()}
    dimensions = [{k: v for k, v in block.items() if k != "rowData"}
                  for block in sheet.get("data", ())]
    return ({k: v for k, v in sheet.items() if k != "data"},
            {p: metadata for p, metadata in cells.items() if metadata}, [block for block in dimensions if block])


def persist_revision(path, state, draft, remote, rows, changes, operation, recheck):
    root = revision_root(path)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    identifier = uuid4().hex
    previous = state.get("working_revision")
    captured = now().isoformat()
    files = {}
    with TemporaryDirectory(dir=root) as staging:
        staging = Path(staging)
        directory = staging / identifier
        directory.mkdir(mode=0o700)
        for name, payload in (
            ("workbook.json", remote), ("changes.json", changes),
            ("receipt.json", {"operation": operation, "time": captured, "revision": identifier,
                              "generation": draft.key, "spreadsheet": state["spreadsheet"],
                              "authorization": "Explicit command confirmation", "approval": False}),
        ):
            write_private(directory / name, json.dumps(payload, indent=2, ensure_ascii=False))
        for table in draft.sheets:
            with (directory / f"{table.name}.csv").open("x", encoding="utf-8", newline="") as stream:
                csv.writer(stream).writerows(
                    [csv_value(value) for value in row] for row in rows[table.name]
                )
        for file in directory.iterdir():
            files[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest = {"schema": 1, "revision": identifier, "previous": previous, "generation": draft.key,
                    "title": draft.title, "spreadsheet": state["spreadsheet"], "captured_at": captured,
                    "status": "working-draft", "files": files,
                    "content_hash": digest({name: sorted((r, c, v) for (r, c), v in remote_values(sheet).items())
                                            for name, sheet in remote.items()}),
                    "structure_hash": digest({table.name: {"headers": table.rows[3],
                                               "sheet_id": remote[table.name]["properties"]["sheetId"],
                                               "index": remote[table.name]["properties"].get("index", 0)}
                                              for table in draft.sheets}),
                    "sheet_fingerprints": {name: fingerprint(sheet) for name, sheet in remote.items()}}
        manifest_path = directory / "manifest.json"
        write_private(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
        pin = {"id": identifier, "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
        directory.rename(root / identifier)
    # Recheck after file persistence to narrow the interval before registration.
    recheck()
    # The prior pointer and prior remote fingerprints are replaced in one local operation.
    pins = {table.name: {"id": remote[table.name]["properties"]["sheetId"], "rows": len(rows[table.name]),
                        "columns": len(table.widths), "fingerprint": fingerprint(remote[table.name])}
            for table in draft.sheets}
    write_private(path, json.dumps({**state, "sheets": pins, "working_revision": pin}, indent=2))
    return identifier


def save_remote(api, draft, path, state, remote, previous, *, operation="capture"):
    rows = {table.name: validated_rows(table, remote[table.name]) for table in draft.sheets}
    def recheck():
        if capture_remote(api, draft, state) != remote:
            raise CommandError("Remote workbook changed during capture. No working revision was registered.")

    if previous == remote:
        recheck()
        return None
    return persist_revision(path, state, draft, remote, rows, changes_between(previous, remote, draft.sheets),
                            operation, recheck)


def publish_working_edits(api, draft, path, state, edit_path, *, report=None):
    previous = load_revision(state, path)
    if previous is None:
        raise CommandError("Register a working revision before publishing a targeted edit.")
    try:
        plan = json.loads(Path(edit_path).read_text())
        edits = plan["edits"]
        if plan["base_revision"] != state["working_revision"]["id"] or not isinstance(edits, list) or not edits:
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise CommandError("Edit plan requires the current base_revision and a nonempty edits list.") from exc
    remote = check_working_remote(api, draft, state, previous, report=report)
    tables = {table.name: table for table in draft.sheets}
    expected = {name: remote_values(sheet) for name, sheet in previous.items()}
    desired_rows = {name: [list(row) for row in validated_rows(tables[name], sheet)] for name, sheet in previous.items()}
    cell_metadata = {name: sheet_cells(sheet) for name, sheet in remote.items()}
    requests, seen = [], set()
    for edit in edits:
        try:
            name, row, column = edit["sheet"], edit["row"], edit["column"]
            table = tables[name]
            value = edit["value"]
            if (type(row) is not int or type(column) is not int or not 5 <= row <= len(desired_rows[name])
                    or not 1 <= column <= len(table.widths) or (name, row, column) in seen
                    or type(value) not in (str, int, float, bool, type(None))
                    or (type(value) is float and not math.isfinite(value))
                    or (expected[name].get((row - 1, column - 1)) or {}) != entered(edit["before"])):
                raise ValueError
        except (ValueError, TypeError, KeyError) as exc:
            raise CommandError("Invalid, duplicate, out-of-range, or stale cell edit.") from exc
        seen.add((name, row, column))
        desired_rows[name][row - 1][column - 1] = value
        position = (row - 1, column - 1)
        if name != "Source References" and column in (1, 2, 13):
            raise CommandError("Targeted edits cannot change configuration numbers, canonical PKs, or slugs.")
        if cell_metadata[name].get(position, {}).get("textFormatRuns"):
            raise CommandError("This cell has rich text runs. Edit it in Sheets and capture a working revision.")
        encoded = entered(value)
        if encoded:
            expected[name][position] = encoded
        else:
            expected[name].pop(position, None)
        requests.append({"updateCells": {
            "start": {"sheetId": state["sheets"][name]["id"], "rowIndex": row - 1, "columnIndex": column - 1},
            "rows": [{"values": [{"userEnteredValue": encoded} if encoded else {}]}],
            "fields": "userEnteredValue",
        }})
    for name, rows in desired_rows.items():
        synthetic = {"data": [{"rowData": [
            {"values": [{"userEnteredValue": entered(value)} for value in row]} for row in rows
        ]}]}
        validated_rows(tables[name], synthetic)
    if all(expected[name] == remote_values(sheet) for name, sheet in remote.items()):
        return None
    # Read again immediately before writing; retained cosmetic edits are allowed
    # on this read too, but semantic and structural checks still use the revision.
    latest = check_working_remote(api, draft, state, previous)
    if latest != remote and report:
        report("Rechecked the workbook before writing and will preserve the latest presentation.")
    remote = latest
    api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=state["spreadsheet"], body={"requests": requests})
    result = capture_remote(api, draft, state)
    if any(remote_values(sheet) != expected[name] or nonvalue_state(sheet) != nonvalue_state(remote[name])
           for name, sheet in result.items()):
        raise CommandError("Post-write values or captured metadata differ. Inspect and explicitly capture the remote draft.")
    return save_remote(api, draft, path, state, result, previous, operation="targeted-publication")
