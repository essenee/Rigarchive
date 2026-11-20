"""Plan and verify the Tacoma operational status projection."""
from copy import deepcopy

from django.core.management.base import CommandError

from reference.admin import factory_body_configuration_label
from reference.configuration_logic_google import entered
from reference.configuration_logic_layout import INACTIVE_INDEX, canonical_row, column_order, header_index
from reference.configuration_logic_revisions import sheet_cells, validated_rows


YEARS = ("MY2024", "MY2025", "MY2026")
MANUAL_TRIMS = {1170: "SR", 1178: "TRD Sport", 1181: "TRD Off-Road"}


def canonical_attributes(vehicle):
    body, engine = vehicle.factory_body_configuration, vehicle.engine
    if not body or not engine or not body.bed_length_id:
        raise CommandError(f"VehicleDefinition {vehicle.pk} lacks complete body or Engine correspondence.")
    return (
        vehicle.trim_name, factory_body_configuration_label(body), body.get_cab_configuration_display(),
        body.bed_length.designation, vehicle.get_drivetrain_display(), engine.engine_code,
        engine.internal_variant_key, engine.name,
    )


def canonical_status(row, vehicles, year):
    """Resolve only explicit PK links in the selected generation."""
    if not row[3] or row[1] is None:
        return None
    if row[1] not in vehicles:
        raise CommandError(f"VehicleDefinition PK {row[1]} is outside the registered generation or missing.")
    vehicle = vehicles[row[1]]
    if (vehicle.model_year != year or tuple(row[3:11]) != canonical_attributes(vehicle)
            or tuple(row[12:14]) != (vehicle.slug, vehicle.get_market_display())):
        raise CommandError(f"Stale or ambiguous VehicleDefinition correspondence for PK {row[1]}.")
    return None if vehicle.is_active else "Yes"


def cell_request(sheet_id, row, column, values):
    return {"updateCells": {
        "start": {"sheetId": sheet_id, "rowIndex": row, "columnIndex": column},
        "rows": [{"values": [{"userEnteredValue": entered(value)} if entered(value) else {}
                             for value in line]} for line in values],
        "fields": "userEnteredValue",
    }}


def manual_row(vehicle, number):
    attrs = canonical_attributes(vehicle)
    if (vehicle.is_active or vehicle.model_year != 2026 or vehicle.market != "US"
            or attrs[0] != MANUAL_TRIMS[vehicle.pk]
            or (attrs[2], attrs[3], vehicle.drivetrain, attrs[6])
            != ("Double Cab", "5-ft", "4WD", "i-force-270hp")):
        raise CommandError(f"Approved inactive MY2026 configuration changed: PK {vehicle.pk}.")
    price = float(vehicle.base_msrp) if vehicle.base_msrp is not None else None
    return (number, vehicle.pk, None, *attrs, price, vehicle.slug, vehicle.get_market_display(),
            None, None, None, None, None, "Stored configuration",
            "RigArchive database; source match unavailable", "Yes")


def plan_inactive(draft, remote, vehicles, *, migrate=False):
    """Return a single bounded Sheets batch and its expected verification state."""
    requests, expected = [], {}
    for table in draft.sheets:
        name = table.name
        if name not in YEARS:
            continue
        sheet = remote[name]
        order = column_order(name, sheet)
        header = header_index(name, sheet)
        rows = validated_rows(table, sheet, flexible=True, physical=True)
        props = deepcopy({k: v for k, v in sheet.items() if k != "data"})
        sheet_id = props["properties"]["sheetId"]
        cells = sheet_cells(sheet)
        if migrate and INACTIVE_INDEX not in order:
            if any(value for key, value in props.items() if key not in {"properties", "basicFilter"}):
                raise CommandError(f"{name} has unsupported metadata for Inactive migration.")
            grid = props["properties"]["gridProperties"]
            column = order.index(11) + 1
            if grid.get("frozenColumnCount", 0) >= column:
                raise CommandError(f"{name} has a frozen boundary at the insertion point.")
            new_order = (*order[:column], INACTIVE_INDEX, *order[column:])
            canonical = [canonical_row(row, order) for row in rows[header + 1:]]
            manual = []
            if name == "MY2026":
                parents = [row for row in canonical if row[3]]
                if (len(parents) != 24 or set(MANUAL_TRIMS) & {row[1] for row in canonical}
                        or not set(MANUAL_TRIMS) <= vehicles.keys()
                        or any(row[1] not in vehicles or not vehicles[row[1]].is_active for row in parents)):
                    raise CommandError("MY2026 does not match the reviewed 24-row migration scope.")
                number = max(row[0] for row in parents)
                manual = [manual_row(vehicles[pk], number + i) for i, pk in enumerate(MANUAL_TRIMS, 1)]
                if (len(rows) + len(manual) > grid["rowCount"] or
                        any(len(rows) <= row < len(rows) + len(manual)
                            and set(cell) - {"userEnteredFormat"} for (row, _), cell in cells.items())):
                    raise CommandError("MY2026 has no verified blank append range.")
            requests.append({"insertDimension": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": column, "endIndex": column + 1},
                "inheritFromBefore": False,
            }})
            grid["columnCount"] += 1
            cells = {(r, c + (c >= column)): cell for (r, c), cell in cells.items()}
            requests.append(cell_request(sheet_id, header, column, [("Inactive",)]))
            cells[(header, column)] = {"userEnteredValue": entered("Inactive")}
            basic_filter = props.get("basicFilter")
            if basic_filter:
                old_range = basic_filter.get("range", {})
                if (set(basic_filter) != {"range"} or old_range.get("startColumnIndex", 0) != 0
                        or old_range.get("endColumnIndex") != len(order)
                        or old_range.get("startRowIndex", 0) != header
                        or old_range.get("endRowIndex") != len(rows)):
                    raise CommandError(f"{name} filter does not match the reviewed managed range.")
                old_range["endColumnIndex"] += 1
                old_range["endRowIndex"] += len(manual)
                requests.append({"setBasicFilter": {"filter": deepcopy(basic_filter)}})
            if manual:
                inserted = [tuple(row[i] for i in new_order) for row in manual]
                requests.append(cell_request(sheet_id, len(rows), 0, inserted))
                for r, row in enumerate(inserted, len(rows)):
                    cells.update({(r, c): {**cells.get((r, c), {}), "userEnteredValue": entered(value)}
                                  for c, value in enumerate(row) if entered(value)})
            order = new_order
        else:
            if INACTIVE_INDEX not in order:
                raise CommandError(f"{name} is not enrolled for Inactive refresh.")
            column = order.index(INACTIVE_INDEX)
            canonical = [canonical_row(row, order) for row in rows[header + 1:]]
        for r, row in enumerate(canonical, header + 1):
            value = canonical_status(row, vehicles, int(name[2:]))
            position = r, column
            old_cell = cells.get(position, {})
            if old_cell.get("userEnteredValue") != (entered(value) or None):
                requests.append(cell_request(sheet_id, r, column, [(value,)]))
                updated = {k: v for k, v in old_cell.items() if k != "userEnteredValue"}
                if value is not None:
                    updated["userEnteredValue"] = entered(value)
                if updated:
                    cells[position] = updated
                else:
                    cells.pop(position, None)
        expected[name] = (props, cells)
    return requests, expected


def verify_inactive(before, after, expected):
    for name, sheet in after.items():
        if name not in expected:
            if sheet != before[name]:
                raise CommandError(f"Unexpected changes to {name}; inspect before retrying.")
            continue
        props, cells = expected[name]
        actual = sheet_cells(sheet)
        # Insertion inherits presentation in the new column only.
        old_order, order = column_order(name, before[name]), column_order(name, sheet)
        if INACTIVE_INDEX not in old_order:
            column = order.index(INACTIVE_INDEX)
            actual = {pos: ({k: v for k, v in cell.items() if k != "userEnteredFormat"}
                            if pos[1] == column else cell) for pos, cell in actual.items()}
            actual = {pos: cell for pos, cell in actual.items() if cell}
        if ({k: v for k, v in sheet.items() if k != "data"} != props or actual != cells):
            raise CommandError(f"{name} differs from the reviewed status operation. Inspect before retrying.")
        def dimensions(sheet, column=None):
            result = {}
            for block in sheet.get("data", ()):
                for axis, offset in (("row", "startRow"), ("column", "startColumn")):
                    for i, data in enumerate(block.get(f"{axis}Metadata", ()), block.get(offset, 0)):
                        if data and (axis != "column" or i != column):
                            result[axis, i - (axis == "column" and column is not None and i > column)] = data
            return result
        inserted_column = order.index(INACTIVE_INDEX) if INACTIVE_INDEX not in old_order else None
        if dimensions(before[name]) != dimensions(sheet, inserted_column):
            raise CommandError(f"{name} dimension metadata changed during the status operation.")
