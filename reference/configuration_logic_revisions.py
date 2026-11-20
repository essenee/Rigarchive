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
from reference.configuration_logic_layout import (
    INACTIVE_FIELD, INACTIVE_INDEX, bind_rows, canonical_row, catalog, column_order, header_index,
)
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
                or manifest["revision"] != identifier or manifest["schema"] not in (1, 2) or manifest["status"] != "working-draft"
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
        if manifest["schema"] == 2:
            load_layout(state, path, manifest=manifest)
        return remote
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise CommandError("Working revision or registry pin is invalid. Restore the trusted local files.") from exc


def revision_manifests(path, state):
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
        yield manifest


def working_history(path, state):
    for manifest in revision_manifests(path, state):
        yield manifest["revision"], manifest.get("captured_at") or "Not recorded"


def load_layout(state, path, *, manifest=None):
    pin = state.get("working_revision")
    if not pin:
        return None
    try:
        identifier = pin["id"]
        if UUID(identifier).hex != identifier:
            raise ValueError
        directory = revision_root(path) / identifier
        if manifest is None:
            raw = (directory / "manifest.json").read_bytes()
            if hashlib.sha256(raw).hexdigest() != pin["manifest_sha256"]:
                raise ValueError
            manifest = json.loads(raw)
        if manifest["schema"] == 1:
            return None
        raw = (directory / "layout.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["files"]["layout.json"]:
            raise ValueError
        layout = json.loads(raw)
        if layout["schema"] not in (1, 2) or set(layout["sheets"]) != set(state["sheets"]):
            raise ValueError
        return layout
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise CommandError("Working revision layout is missing or invalid.") from exc


def sheet_cells(sheet):
    return {
        (block.get("startRow", 0) + r, block.get("startColumn", 0) + c): cell
        for block in sheet.get("data", ())
        for r, row in enumerate(block.get("rowData", ()))
        for c, cell in enumerate(row.get("values", ())) if cell
    }


def scalar(entry):
    return next(iter(entry.values())) if entry else None


def validated_rows(table, sheet, *, flexible=False, physical=False):
    values = remote_values(sheet)
    order = column_order(table.name, sheet) if flexible else tuple(range(len(table.widths)))
    width = len(order)
    header = header_index(table.name, sheet) if flexible else 3
    height = max((r + 1 for r, _ in values), default=header + 1)
    if sheet.get("protectedRanges"):
        raise CommandError(f"{table.name} is protected.")
    if any(merge.get("endRowIndex", 0) > header for merge in sheet.get("merges", ())):
        raise CommandError(f"{table.name} contains a merge intersecting the column headers or data.")
    if (any(c >= width or "formulaValue" in item for (r, c), item in values.items())
            or any(c >= width and any(k != "userEnteredFormat" for k in cell)
                   for (_, c), cell in sheet_cells(sheet).items())):
        raise CommandError(f"{table.name} contains formulas or values outside the working schema.")
    rows = tuple(tuple(scalar(values.get((r, c))) for c in range(width)) for r in range(height))
    headers = tuple(header for _, header in catalog(table.name)[:width])
    if len(rows) <= header or (not flexible and rows[header] != headers):
        raise CommandError(f"{table.name} column headers are missing, duplicated, reordered, or renamed.")
    sheet_rows = rows
    rows = tuple(canonical_row(row, order) for row in rows)
    if header and (rows[0][0] != table.title or not str(rows[1][0]).startswith("Draft")):
        raise CommandError(f"{table.name} must retain its title and draft status.")
    if table.name == "Source References":
        if any(any(value is not None and value != "" for value in row)
               and (type(row[0]) is not int or not row[2]) for row in rows[header + 1:]):
            raise CommandError("Source References rows require a model year and source title.")
    else:
        parents, identifiers = {}, set()
        for row in rows[header + 1:]:
            if not any(value is not None and value != "" for value in row):
                continue
            if len(row) > INACTIVE_INDEX and (row[INACTIVE_INDEX] not in (None, "Yes")
                                             or (row[INACTIVE_INDEX] and not row[3])):
                raise CommandError(f"{table.name} has an invalid Inactive value.")
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
    return sheet_rows if physical else rows


def current_draft(generation, path, state):
    remote = load_revision(state, path)
    if remote is None:
        return generation_draft(generation)
    from reference.configuration_logic import generation_title

    title = generation_title(generation)
    tables = []
    layout = load_layout(state, path)
    for name, sheet in sorted(remote.items(), key=lambda item: item[1]["properties"].get("index", 0)):
        headers, widths, prices = (HEADERS, WIDTHS, (11, 17))
        if name == "Source References":
            headers, widths, prices = SOURCE_HEADERS, (14, 18, 32, 60, 20, 29, 42, 28, 65), ()
        template = Sheet(name, ((title,), ("Draft",), (), headers), widths, prices)
        if layout:
            order = column_order(name, sheet)
            pixels = dimension_widths(sheet)
            widths = tuple(max(1, pixels[col] / 8) if col in pixels else (widths[index] if index < len(widths) else 12)
                           for col, index in enumerate(order))
            prices = tuple(col for col, index in enumerate(order) if index in prices)
        tables.append(Sheet(name, validated_rows(template, sheet, flexible=bool(layout), physical=True), widths, prices, header_index(name, sheet) + 1, title))
    return GenerationDraft(str(generation.uuid), title, tuple(tables))


def dimension_widths(sheet):
    return {block.get("startColumn", 0) + i: item["pixelSize"]
            for block in sheet.get("data", ()) for i, item in enumerate(block.get("columnMetadata", ()))
            if "pixelSize" in item}


def logical_position(position, order):
    row, col = position
    return (row, order[col]) if order and col < len(order) else position


def status_values(sheet, order):
    if order is None or INACTIVE_INDEX not in order:
        return {}
    column = order.index(INACTIVE_INDEX)
    return {row: v for (row, col), v in remote_values(sheet).items() if col == column}


def manufacturer_values(sheet, order):
    values = remote_values(sheet)
    if order is not None and INACTIVE_INDEX in order:
        column = order.index(INACTIVE_INDEX)
        return {position: value for position, value in values.items() if position[1] != column}
    return values


def changes_between(before, remote, tables, *, flexible=False):
    changes = {}
    for table in tables:
        name = table.name
        new = remote[name]
        old = before[name] if before else None
        if old is None:
            changes[name] = {"baseline": "unavailable", "captured_values": len(remote_values(new))}
            continue
        try:
            old_order = column_order(name, old) if flexible else None
            new_order = column_order(name, new) if flexible else None
        except CommandError:
            old_order = new_order = None  # Inspection still reports incompatible physical changes.
        old_header = header_index(name, old) if old_order is not None else 3
        header = header_index(name, new) if new_order is not None else 3
        layout_changed = old_header != header
        operational_changed = status_values(old, old_order) != status_values(new, new_order)
        def project(cells, order, current_header):
            return {(r - current_header + header, c): value
                    for position, value in cells.items()
                    for r, c in (logical_position(position, order),)
                    if not layout_changed or r > current_header}

        a, b = (project(manufacturer_values(sheet, order), order, current_header)
                for sheet, order, current_header in ((old, old_order, old_header), (new, new_order, header)))
        old_notes, new_notes = (project({p: cell["note"] for p, cell in sheet_cells(sheet).items() if "note" in cell and logical_position(p, order)[1] != INACTIVE_INDEX},
                                        order, current_header)
                                for sheet, order, current_header in ((old, old_order, old_header), (new, new_order, header)))
        old_semantic = project(classify_sheet(old, name, old_order, capture=True)[0], None, old_header)
        new_semantic = project(classify_sheet(new, name, new_order, capture=True)[0], None, header)
        old_headers = {c: v for (r, c), v in remote_values(old).items() if r == old_header}
        new_headers = {c: v for (r, c), v in remote_values(new).items() if r == header}
        if old_order is not None and new_order is not None:
            old_headers = {old_order[c]: v for c, v in old_headers.items()}
            new_headers = {new_order[c]: v for c, v in new_headers.items()}
        # A recognized alias is a label change, not a new field.
        def header_label(value):
            return {"stringValue": "VehicleDefinition PK"} if value == {"stringValue": "Vehicle Definition PK"} else value
        old_headers = {c: header_label(v) for c, v in old_headers.items()}
        new_headers = {c: header_label(v) for c, v in new_headers.items()}
        if name.startswith("MY") and old_order is not None and new_order is not None:
            for values, semantic in ((a, old_semantic), (b, new_semantic)):
                pos = (header, 1)
                if pos in values:
                    values[pos] = header_label(values[pos])
                if pos in semantic and "userEnteredValue" in semantic[pos]:
                    semantic[pos] = {**semantic[pos], "userEnteredValue": header_label(semantic[pos]["userEnteredValue"])}
        old_rows, new_rows = data_rows(a, header), data_rows(b, header)
        row_edits = SequenceMatcher(a=old_rows, b=new_rows, autojunk=False).get_opcodes()
        changes[name] = {
            "operational_status_changed": operational_changed,
            "cells": cell_changes(a, b), "notes": cell_changes(old_notes, new_notes),
            "column_order_changed": old_order != new_order,
            "semantic_metadata_changed": old_semantic != new_semantic and a == b and old_notes == new_notes,
            "row_changes": [[kind, a1 + header + 2, a2 - a1, b1 + header + 2, b2 - b1]
                            for kind, a1, a2, b1, b2 in row_edits if kind != "equal"],
            "headers_changed": layout_changed or old_headers != new_headers,
            "sheet_metadata_changed": {k: v for k, v in old.items() if k != "data"} !=
                                      {k: v for k, v in new.items() if k != "data"},
            "fingerprint_changed": fingerprint(old) != fingerprint(new),
        }
    return changes


def cell_changes(old, new):
    return [{"row": r + 1, "column": c + 1, "before": old.get((r, c)), "after": new.get((r, c))}
            for r, c in sorted(old.keys() | new.keys()) if old.get((r, c)) != new.get((r, c))]


def data_rows(values, header=3):
    height = max((r for r, _ in values), default=header)
    return [digest(sorted((c, v) for (line, c), v in values.items() if line == r))
            for r in range(header + 1, height + 1)]


# Keep Milestone A's field mask and full fingerprints intact. Working revisions
# compare the captured grid and explicitly request additional structural metadata.
WORKING_FIELDS = FIELDS.replace(
    "filterViews,charts,data",
    "filterViews,charts,conditionalFormats,rowGroups,columnGroups,bandedRanges,slicers,developerMetadata,tables,data",
).replace("(pixelSize)", "(pixelSize,hiddenByUser,hiddenByFilter)")
COSMETIC_CELL_FORMAT = {
    "wrapStrategy", "backgroundColor", "backgroundColorStyle", "borders",
    "horizontalAlignment", "verticalAlignment", "padding", "textRotation", "textDirection",
}
COSMETIC_TEXT_FORMAT = {
    "fontFamily", "fontSize", "bold", "italic", "strikethrough", "underline",
    "foregroundColor", "foregroundColorStyle",
}


def classify_sheet(sheet, name, order=None, *, capture=False):
    """Return semantic, structural and presentation views of captured Sheets data."""
    semantic, cosmetics = {}, {}
    values = {logical_position(p, order): v for p, v in manufacturer_values(sheet, order).items()}
    structure = {key: value for key, value in sheet.items() if key != "data"}
    for key in ("conditionalFormats", "rowGroups", "columnGroups"):
        if not structure.get(key):
            structure.pop(key, None)
    header = header_index(name, sheet) if order is not None else 3
    headers = {position: value for position, value in values.items() if position[0] == header}
    row_identity = {} if name == "Source References" else {
        position: value for position, value in values.items()
        if position[0] > header and position[1] in (0, 1, 12)
    }
    occupied_rows = {r for r, _ in values if r > header}
    cosmetic_format = COSMETIC_CELL_FORMAT | {"numberFormat"} if capture else COSMETIC_CELL_FORMAT
    for position, cell in sheet_cells(sheet).items():
        position = logical_position(position, order)
        content = {key: value for key, value in cell.items() if key != "userEnteredFormat"}
        if position[1] == INACTIVE_INDEX and order is not None:
            content.pop("userEnteredValue", None)
        fmt = cell.get("userEnteredFormat", {})
        paint = {key: value for key, value in fmt.items() if key in cosmetic_format}
        other = {key: value for key, value in fmt.items()
                 if key not in cosmetic_format and key != "textFormat"}
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
                physical = block.get(offset, 0) + index
                position = (axis, order[physical] if order and axis == "column" and physical < len(order) else physical)
                other = {key: value for key, value in item.items() if key != "pixelSize"
                         and not (key in ("hiddenByUser", "hiddenByFilter") and value is False)}
                if other:
                    dimensions[position] = other
                if "pixelSize" in item:
                    sizes[position] = item["pixelSize"]
    return semantic, (structure, headers, occupied_rows, row_identity, dimensions), (cosmetics, sizes)


def logical_move_metadata(metadata, order):
    """Normalize supported sheet-level bindings or fail closed on a move."""
    def field(index):
        if type(index) is not int or not 0 <= index < len(order):
            raise ValueError
        return order[index]

    def verify_condition(condition):
        if condition.get("type") == "CUSTOM_FORMULA" or any(
            str(value.get("userEnteredValue", "")).lstrip().startswith("=")
            for value in condition.get("values", ())
        ):
            raise ValueError

    def filter_binding(spec, *, view=False):
        allowed = {"range", "sortSpecs", "criteria", "filterSpecs"}
        if view:
            allowed |= {"filterViewId", "title"}
        if spec.keys() - allowed or "range" not in spec:
            raise ValueError
        grid = dict(spec["range"])
        if grid.keys() - {"sheetId", "startRowIndex", "endRowIndex", "startColumnIndex", "endColumnIndex"}:
            raise ValueError
        start = grid.pop("startColumnIndex", 0)
        end = grid.pop("endColumnIndex", len(order))
        if not 0 <= start < end <= len(order):
            raise ValueError
        grid["logicalFields"] = sorted(order[start:end])
        sorts = []
        for sort in spec.get("sortSpecs", ()):
            if sort.keys() - {"dimensionIndex", "sortOrder", "backgroundColor", "backgroundColorStyle",
                              "foregroundColor", "foregroundColorStyle"}:
                raise ValueError
            sorts.append({**sort, "dimensionIndex": field(sort["dimensionIndex"])})
        criteria = {field(int(index)): criterion for index, criterion in spec.get("criteria", {}).items()}
        filter_specs = {}
        for item in spec.get("filterSpecs", ()):
            index = field(item["columnIndex"])
            if item.keys() != {"columnIndex", "filterCriteria"} or index in filter_specs:
                raise ValueError
            filter_specs[index] = item["filterCriteria"]
        for criterion in (*criteria.values(), *filter_specs.values()):
            verify_condition(criterion.get("condition", {}))
        return {**spec, "range": grid, "sortSpecs": sorts, "criteria": criteria, "filterSpecs": filter_specs}

    if any(value for key, value in metadata.items() if key not in {"properties", "basicFilter", "filterViews"}):
        raise ValueError
    props = dict(metadata["properties"])
    grid = dict(props.get("gridProperties", {}))
    frozen = grid.pop("frozenColumnCount", 0)
    if type(frozen) is not int or not 0 <= frozen <= len(order):
        raise ValueError
    grid["frozenFields"] = sorted(order[:frozen])
    props["gridProperties"] = grid
    return (props, filter_binding(metadata["basicFilter"]) if metadata.get("basicFilter") else None,
            [filter_binding(view, view=True) for view in metadata.get("filterViews", ())])


def validate_move_structure(name, old_structure, structure, old_order, order, content):
    try:
        old_bindings = logical_move_metadata(old_structure[0], old_order)
        bindings = logical_move_metadata(structure[0], order)
        for cell in content.values():
            condition = cell.get("dataValidation", {}).get("condition", {})
            if condition.get("type") in {"CUSTOM_FORMULA", "ONE_OF_RANGE"}:
                raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError(f"{name} column move has unsupported position-dependent metadata.") from exc
    if old_bindings != bindings or old_structure[1:] != structure[1:]:
        raise CommandError(f"{name} column move changes logical structural bindings.")


def header_transition_metadata(metadata, header):
    """Compare the supported grid and filter geometry relative to the header."""
    if any(value for key, value in metadata.items() if key not in {"properties", "basicFilter"}):
        raise ValueError
    properties = dict(metadata["properties"])
    grid = dict(properties.get("gridProperties", {}))
    for key in ("rowCount", "frozenRowCount"):
        if key in grid:
            if grid[key] < header:
                raise ValueError
            grid[key] -= header
    properties["gridProperties"] = grid
    basic_filter = metadata.get("basicFilter")
    if basic_filter:
        if basic_filter.keys() != {"range"}:
            raise ValueError
        bounds = dict(basic_filter["range"])
        for key in ("startRowIndex", "endRowIndex"):
            if key not in bounds or bounds[key] < header:
                raise ValueError
            bounds[key] -= header
        basic_filter = {"range": bounds}
    return properties, basic_filter


def check_working_remote(api, draft, state, previous, *, report=None, flexible=False, coordinate_plan=False):
    remote = capture_remote(api, draft, state)
    if set(remote) != set(previous):
        raise CommandError("Working revision worksheet identity differs from the remote workbook.")
    presentation = []
    for table in draft.sheets:
        name = table.name
        validated_rows(table, remote[name], flexible=flexible)
        old_order = column_order(name, previous[name]) if flexible else None
        order = column_order(name, remote[name]) if flexible else None
        if coordinate_plan and old_order != order:
            raise CommandError("Legacy coordinate plan requires the exact registered column layout.")
        old_semantic, old_structure, old_presentation = classify_sheet(previous[name], name, old_order)
        semantic, structure, appearance = classify_sheet(remote[name], name, order)
        if status_values(previous[name], old_order) != status_values(remote[name], order):
            raise CommandError(f"{name} has unregistered Inactive values. Use the controlled refresh.")
        if flexible and header_index(name, previous[name]) != header_index(name, remote[name]):
            raise CommandError(f"{name} header row changed. Capture the layout before publishing.")
        if old_order != order:
            validate_move_structure(name, old_structure, structure, old_order, order, old_semantic)
        elif structure != old_structure:
            raise CommandError(f"Unexpected external change in {name}: structural differences; publication stopped.")
        if semantic != old_semantic:
            raise CommandError(f"Unexpected external change in {name}: values, notes, or noncosmetic cell metadata differ.")
        if appearance != old_presentation or old_order != order:
            presentation.append(name)
    if report and presentation:
        report("Nonblocking presentation changes detected and preserved in: " + ", ".join(presentation) + ".")
    return remote


def capture_remote(api, draft, state):
    remote = read_remote(api, state["spreadsheet"], draft.title, fields=WORKING_FIELDS)
    projection = remote.pop("Change Log", None)
    if list(remote) != [table.name for table in draft.sheets] or set(remote) != set(state["sheets"]):
        raise CommandError("Remote worksheet names or order differ from the registered generation.")
    for index, (name, sheet) in enumerate(remote.items()):
        props = sheet["properties"]
        physical_index = index
        if projection is not None and projection["properties"].get("index", 0) <= index:
            physical_index += 1
        if props["sheetId"] != state["sheets"][name]["id"] or props.get("index", 0) != physical_index:
            raise CommandError(f"{name} has a changed worksheet ID or index.")
        if physical_index != index:
            props["index"] = index  # Projection placement is outside working-revision authority.
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


def persist_revision(path, state, draft, remote, rows, changes, operation, recheck, layout):
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
        if layout is not None:
            write_private(directory / "layout.json", json.dumps(layout, indent=2, ensure_ascii=False))
        for table in draft.sheets:
            with (directory / f"{table.name}.csv").open("x", encoding="utf-8", newline="") as stream:
                csv.writer(stream).writerows(
                    [csv_value(value) for value in row] for row in rows[table.name]
                )
        for file in directory.iterdir():
            files[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
        manifest = {"schema": 2 if layout else 1, "revision": identifier, "previous": previous, "generation": draft.key,
                    "title": draft.title, "spreadsheet": state["spreadsheet"], "captured_at": captured,
                    "status": "working-draft", "files": files,
                    "content_hash": digest({name: sorted((r, c, v) for (r, c), v in remote_values(sheet).items())
                                            for name, sheet in remote.items()}),
                    "structure_hash": digest({table.name: {"headers": table.rows[table.header_row - 1],
                                               "sheet_id": remote[table.name]["properties"]["sheetId"],
                                               "index": remote[table.name]["properties"].get("index", 0)}
                                              for table in draft.sheets}),
                    "sheet_fingerprints": {name: fingerprint(sheet) for name, sheet in remote.items()}}
        if layout:
            manifest["content_hash"] = layout["logical_content_hash"]
            manifest["structure_hash"] = layout["structure_hash"]
            manifest["presentation_hash"] = layout["presentation_hash"]
        manifest_path = directory / "manifest.json"
        write_private(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))
        pin = {"id": identifier, "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}
        directory.rename(root / identifier)
    # Recheck after file persistence to narrow the interval before registration.
    recheck()
    # The prior pointer and prior remote fingerprints are replaced in one local operation.
    pins = {table.name: {"id": remote[table.name]["properties"]["sheetId"], "rows": len(rows[table.name]),
                        "columns": len(rows[table.name][0]), "fingerprint": fingerprint(remote[table.name])}
            for table in draft.sheets}
    write_private(path, json.dumps({**state, "sheets": pins, "working_revision": pin}, indent=2))
    return identifier


def verified_row_permutation(table, before, after, prior):
    """Rebind a reviewed parent-row permutation without guessing identities."""
    name = table.name
    header = header_index(name, before)
    if (header != header_index(name, after) or column_order(name, before) != column_order(name, after)
            or {k: v for k, v in before.items() if k != "data"} !=
               {k: v for k, v in after.items() if k != "data"}):
        raise CommandError(f"{name} row permutation changed worksheet structure.")
    old_cells, new_cells = sheet_cells(before), sheet_cells(after)
    def row_content(cells, position):
        return {c: content for (r, c), cell in cells.items() if r == position
                if (content := {k: v for k, v in cell.items() if k != "userEnteredFormat"})}
    if any(row_content(old_cells, r) != row_content(new_cells, r) for r in range(header + 1)):
        raise CommandError(f"{name} row permutation changed preamble or headers.")
    def positions(sheet, cells):
        rows = validated_rows(table, sheet, flexible=True)
        result = {}
        for position, row in enumerate(rows[header + 1:], header + 1):
            if not row[3] or row[1] is None or row[1] in result:
                raise CommandError(f"{name} row permutation needs unique PK-linked parent rows.")
            result[row[1]] = (position, row_content(cells, position))
        extra = {r for r, _ in cells if r >= len(rows) and row_content(cells, r)}
        if extra:
            raise CommandError(f"{name} row permutation has data or annotations outside the parent rows.")
        return result
    old, new = positions(before, old_cells), positions(after, new_cells)
    if old.keys() != new.keys() or any(old[pk][1] != new[pk][1] for pk in old):
        raise CommandError(f"{name} row permutation changed values, notes, or non-format cell metadata.")
    def structural_dimensions(sheet, rows):
        key_by_position = {position: pk for pk, (position, _) in rows.items()}
        dimensions = classify_sheet(sheet, name, column_order(name, sheet))[1][-1]
        return {("vehicle", key_by_position[position]) if axis == "row" and position in key_by_position
                else (axis, position): value for (axis, position), value in dimensions.items()}
    if structural_dimensions(before, old) != structural_dimensions(after, new):
        raise CommandError(f"{name} row permutation changed hidden or filtered dimensions.")
    by_position = {row["row"] - 1: row for row in prior}
    if set(by_position) != {position for position, _ in old.values()}:
        raise CommandError(f"{name} row permutation differs from the registered working-row bindings.")
    return [by_position[old[pk][0]] for pk in new]


def save_remote(api, draft, path, state, remote, previous, *, operation="capture", enroll=False,
                approved_row_permutation=None):
    prior_layout = load_layout(state, path)
    flexible = prior_layout is not None or enroll
    rows, logical, layout_sheets = {}, {}, {}
    if approved_row_permutation and (not prior_layout or previous is None or approved_row_permutation not in previous
                                    or any(remote[name] != sheet for name, sheet in previous.items()
                                           if name != approved_row_permutation)):
        raise CommandError("The approved row permutation requires an enrolled baseline and identical other tabs.")
    for table in draft.sheets:
        name = table.name
        rows[name] = validated_rows(table, remote[name], flexible=flexible, physical=True)
        if not flexible:
            continue
        order = column_order(name, remote[name])
        if previous is None and order != tuple(range(len(order))):
            raise CommandError(f"{name} needs an ordered, trusted baseline before layout enrollment.")
        old_order = column_order(name, previous[name]) if previous else order
        content, structure, _ = classify_sheet(remote[name], name, order, capture=True)
        migration = operation == "inactive-migration"
        if previous and (INACTIVE_INDEX in old_order) != (INACTIVE_INDEX in order) and not migration:
            raise CommandError(f"{name} Inactive schema changes require the controlled migration.")
        if (previous and name != approved_row_permutation
                and status_values(previous[name], old_order) != status_values(remote[name], order)
                and operation not in {"inactive-migration", "inactive-refresh"}):
            raise CommandError(f"{name} Inactive values require the controlled refresh.")
        if previous and order != old_order and not migration:
            old_content, old_structure, _ = classify_sheet(previous[name], name, old_order, capture=True)
            validate_move_structure(name, old_structure, structure, old_order, order, old_content)
            if operation != "targeted-publication" and old_content != content:
                raise CommandError(f"{name} changes logical content during a column move. Capture content and layout separately.")
        header = header_index(name, remote[name])
        if previous and header != header_index(name, previous[name]):
            old_header = header_index(name, previous[name])
            old_content, old_structure, _ = classify_sheet(previous[name], name, old_order, capture=True)
            old_data = {(r - old_header, c): cell for (r, c), cell in old_content.items() if r > old_header}
            data = {(r - header, c): cell for (r, c), cell in content.items() if r > header}
            if old_order != order or old_data != data:
                raise CommandError(f"{name} changes data during a header-row transition. Capture the layout separately.")
            def dimensions(items, index):
                return {(axis, position - index if axis == "row" else position): value
                        for (axis, position), value in items.items() if axis != "row" or position >= index}
            try:
                compatible = (header_transition_metadata(old_structure[0], old_header)
                              == header_transition_metadata(structure[0], header)
                              and dimensions(old_structure[4], old_header) == dimensions(structure[4], header))
            except (KeyError, TypeError, ValueError) as exc:
                raise CommandError(f"{name} header-row transition has unsupported structural metadata.") from exc
            if not compatible:
                raise CommandError(f"{name} header-row transition changes structural bindings.")
        prior_rows = prior_layout["sheets"][name]["rows"] if prior_layout else ()
        if name == approved_row_permutation:
            prior_rows = verified_row_permutation(table, previous[name], remote[name], prior_rows)
        bound, removed = bind_rows(name, validated_rows(table, remote[name], flexible=True), prior_rows, header=header)
        fields = catalog(name)[:len(order)]
        layout_sheets[name] = {
            "sheet_id": remote[name]["properties"]["sheetId"], "header_row": header + 1,
            "fields": dict(fields), "columns": {fields[i][0]: col + 1 for col, i in enumerate(order)},
            "display_order": [fields[i][0] for i in order], "rows": bound, "removed_row_ids": removed,
        }
        logical[name] = sorted((r, c, cell) for (r, c), cell in content.items())
    layout = None
    if flexible:
        operational = [INACTIVE_FIELD] if any(INACTIVE_FIELD in sheet["fields"] for sheet in layout_sheets.values()) else []
        layout = {"schema": 2 if operational else 1, "sheets": layout_sheets, "logical_content_hash": digest(logical),
                  "structure_hash": digest({name: {
                      "sheet_id": sheet["sheet_id"], "fields": sheet["fields"], "rows": sheet["rows"],
                  } for name, sheet in layout_sheets.items()}),
                  "presentation_hash": digest({name: nonvalue_state_for_hash(sheet) for name, sheet in remote.items()})}
        if operational:
            layout["operational_fields"] = operational

    def recheck():
        if capture_remote(api, draft, state) != remote:
            raise CommandError("Remote workbook changed during capture. No working revision was registered.")

    if previous == remote and not (enroll and prior_layout is None):
        recheck()
        return None
    changes = changes_between(previous, remote, draft.sheets, flexible=flexible)
    if approved_row_permutation:
        name = approved_row_permutation
        before = {row["id"]: row["row"] for row in prior_layout["sheets"][name]["rows"]}
        changes[name].update(cells=[], notes=[], row_changes=[], semantic_metadata_changed=False,
                             operational_status_changed=False, working_row_moves=[
                                 {"row_id": row["id"], "before": before[row["id"]], "after": row["row"]}
                                 for row in layout_sheets[name]["rows"] if before[row["id"]] != row["row"]
                             ])
    if prior_layout:
        for name, new_sheet in layout_sheets.items():
            previous_ids = {row["id"] for row in prior_layout["sheets"][name]["rows"]}
            changes[name]["working_rows_added"] = [
                row["id"] for row in new_sheet["rows"] if row["id"] not in previous_ids
            ]
            changes[name]["working_rows_removed"] = new_sheet["removed_row_ids"]
            by_position = {row["row"]: row["id"] for row in new_sheet["rows"]}
            for group in ("cells", "notes"):
                for change in changes[name].get(group, ()):
                    if 1 <= change["column"] <= len(catalog(name)):
                        change["field_id"] = catalog(name)[change["column"] - 1][0]
                    if not changes[name]["working_rows_added"] and not new_sheet["removed_row_ids"]:
                        change["row_id"] = by_position.get(change["row"])
    return persist_revision(path, state, draft, remote, rows, changes, operation, recheck, layout)


def nonvalue_state_for_hash(sheet):
    props, cells, dimensions = nonvalue_state(sheet)
    return props, sorted((r, c, cell) for (r, c), cell in cells.items()), dimensions


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
    layout = load_layout(state, path)
    schema = plan.get("schema", 1)
    if type(schema) is not int or schema not in (1, 2) or (schema == 2 and layout is None):
        raise CommandError("Logical edit plans require an enrolled layout and schema 2.")
    options = {"flexible": bool(layout), "coordinate_plan": schema == 1}
    remote = check_working_remote(api, draft, state, previous, report=report, **options)
    expected, requests = plan_updates(draft, state, remote, edits, layout, schema)
    if not requests:
        return None
    latest = check_working_remote(api, draft, state, previous, **options)
    if latest != remote and report:
        report("Rechecked the workbook before writing and resolved the latest compatible layout.")
    expected, requests = plan_updates(draft, state, latest, edits, layout, schema)
    api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=state["spreadsheet"], body={"requests": requests})
    result = capture_remote(api, draft, state)
    if any(remote_values(sheet) != expected[name] or nonvalue_state(sheet) != nonvalue_state(latest[name])
           for name, sheet in result.items()):
        raise CommandError("Post-write values or captured metadata differ. Inspect and explicitly capture the remote draft.")
    return save_remote(api, draft, path, state, result, previous, operation="targeted-publication")


def plan_updates(draft, state, remote, edits, layout, schema):
    tables = {table.name: table for table in draft.sheets}
    expected = {name: remote_values(sheet) for name, sheet in remote.items()}
    desired_rows = {name: [list(row) for row in validated_rows(tables[name], sheet, flexible=bool(layout), physical=True)] for name, sheet in remote.items()}
    cell_metadata = {name: sheet_cells(sheet) for name, sheet in remote.items()}
    requests, seen = [], set()
    for edit in edits:
        try:
            if schema == 2:
                if type(edit["sheet_id"]) is not int:
                    raise ValueError
                name, = [name for name, item in layout["sheets"].items() if item["sheet_id"] == edit["sheet_id"]]
                row, = [item["row"] for item in layout["sheets"][name]["rows"] if item["id"] == edit["row_id"]]
                logical_column = [field for field, _ in catalog(name)].index(edit["field_id"])
                column = column_order(name, remote[name]).index(logical_column) + 1
            else:
                name, row, column = edit["sheet"], edit["row"], edit["column"]
            table = tables[name]
            value = edit["value"]
            if (type(row) is not int or type(column) is not int or not (layout["sheets"][name]["header_row"] if layout else 4) < row <= len(desired_rows[name])
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
        canonical_column = column_order(name, remote[name])[column - 1] + 1 if layout else column
        if name != "Source References" and canonical_column == INACTIVE_INDEX + 1:
            raise CommandError("Inactive is machine-managed. Use the controlled refresh.")
        if name != "Source References" and canonical_column in (1, 2, 13):
            raise CommandError("Targeted edits cannot change configuration numbers, canonical PKs, or slugs.")
        if cell_metadata[name].get(position, {}).get("textFormatRuns"):
            raise CommandError("This cell has rich text runs. Edit it in Sheets and capture a working revision.")
        encoded = entered(value)
        if (expected[name].get(position) or {}) == encoded:
            continue
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
        logical_rows = validated_rows(tables[name], synthetic, flexible=bool(layout))
        if layout:
            prior_rows = layout["sheets"][name]["rows"]
            bound, removed = bind_rows(name, logical_rows, prior_rows, header=layout["sheets"][name]["header_row"] - 1)
            if removed or bound != prior_rows:
                raise CommandError("Targeted edits cannot change working-row identity or order.")
    return expected, requests
