"""Stable draft field and row bindings for the Configuration Logic workbook."""
from uuid import uuid4

from django.core.management.base import CommandError

from reference.configuration_logic import HEADERS, LEGACY_BODY_COLUMNS, SOURCE_HEADERS
from reference.configuration_logic_google import digest, remote_values


CONFIG_FIELDS = (
    "number", "pk", "model_code", "trim", "body", "cab", "nominal_bed", "drivetrain",
    "engine_code", "engine_variant", "engine", "base_msrp", "slug", "market", "transmission",
    "conditional_output", "alternate_model_code", "alternate_msrp", "package",
    "applicability", "provenance",
)
INACTIVE_FIELD = "configuration.inactive"
INACTIVE_HEADER = "Inactive"
INACTIVE_INDEX = len(CONFIG_FIELDS)
NUMBERING_PREFIX = '={"#";LET('
NUMBERING_FIELDS = (3, 14, 15, 16, 17, 18, 19)

SOURCE_FIELDS = ("model_year", "organization", "title", "locator", "reviewed_at",
                 "source_type", "evidence_id", "verification", "notes")


def catalog(name):
    if name == "Source References":
        return tuple(zip((f"source.{f}" for f in SOURCE_FIELDS), SOURCE_HEADERS, strict=True))
    return (*zip((f"configuration.{f}" for f in CONFIG_FIELDS), HEADERS, strict=True),
            (INACTIVE_FIELD, INACTIVE_HEADER))


def header_index(name, sheet):
    """Allow a compact header at row 1 only on model-year worksheets."""
    if name.startswith("MY") and name[2:].isdigit():
        values = remote_values(sheet)
        if any(r == 0 and number_header(value) for (r, _), value in values.items()):
            return 0
    return 3


def column_order(name, sheet):
    """Return canonical-column indices in their observed physical order."""
    fields = catalog(name)
    index = {header: i for i, (_, header) in enumerate(fields)}
    values = remote_values(sheet)
    header = header_index(name, sheet)
    headers = {c: "#" if name.startswith("MY") and number_header(value) else value.get("stringValue")
               for (r, c), value in values.items() if r == header}
    if name.startswith("MY"):
        headers = {c: "VehicleDefinition PK" if label == "Vehicle Definition PK" else label
                   for c, label in headers.items()}
    if name != "Source References" and INACTIVE_HEADER not in headers.values():
        index.pop(INACTIVE_HEADER)
    if name.startswith("MY") and not ({"Cab", "Nominal Bed"} & set(headers.values())):
        index = {label: i for label, i in index.items() if i not in LEGACY_BODY_COLUMNS}
    if set(headers) != set(range(len(index))) or set(headers.values()) != set(index):
        raise CommandError(f"{name} column headers are missing, duplicated, or renamed.")
    return tuple(index[headers[col]] for col in range(len(index)))


def canonical_row(row, order):
    values = dict(zip(order, row, strict=True))
    return tuple(values.get(index) for index in range(max(order) + 1))


def number_header(value):
    return value.get("stringValue") == "#" or value.get("formulaValue", "").startswith(NUMBERING_PREFIX)


def numbering_formula(order):
    """Anchor the spill in the header and use whole columns so inserts recalculate."""
    def column(field):
        # The fixed CL schema has fewer than 26 columns.
        letter = chr(ord("A") + order.index(field))
        return f"{letter}:{letter}"

    present = "+".join(f"LEN({column(field)})" for field in NUMBERING_FIELDS)
    return (f'{NUMBERING_PREFIX}used,FILTER(({present})>0,ROW({column(3)})>ROW()),'
            'ARRAYFORMULA(IF(used,SCAN(0,used,LAMBDA(total,item,total+N(item))),"")))}')


def uses_numbering(name, sheet):
    if not name.startswith("MY"):
        return False
    header = header_index(name, sheet)
    return any(row == header and value.get("formulaValue", "").startswith(NUMBERING_PREFIX)
               for (row, _), value in remote_values(sheet).items())


def row_witnesses(name, rows, header=3, *, numbered=False):
    """Conservative continuity witnesses. These hashes are not the opaque row IDs."""
    parents = {}
    most_recent = None
    result = []
    for position, row in enumerate(rows[header + 1:], header + 2):
        if not any(value is not None and value != "" for value in row):
            continue
        parent = None
        if name == "Source References":
            witness = ("source", *(row[i] for i in (0, 1, 2, 3, 6)))
        elif row[3]:
            witness = ("configuration", *(row[i] for i in (3, 4, 5, 6, 7, 8, 9, 13)))
            parents[row[0]] = digest(witness)
            most_recent = parents[row[0]]
        else:
            parent = most_recent if numbered else parents[row[0]]
            witness = ("alternative", parent, *(row[i] for i in (14, 15, 16, 18)))
        result.append((position, digest(witness), parent))
    signatures = [item[1] for item in result]
    if len(set(signatures)) != len(signatures):
        raise CommandError(f"{name} has ambiguous working-row identities. Review duplicate configuration or source rows.")
    return result


def bind_rows(name, rows, prior, *, header=3, numbered=False, allow_reorder=False):
    witnesses = row_witnesses(name, rows, header, numbered=numbered)
    prior_by_key = {row["witness"]: row for row in prior}
    keys = {signature for _, signature, _ in witnesses}
    removed = [row for row in prior if row["witness"] not in keys]
    added = keys - prior_by_key.keys()
    old_order = [row["witness"] for row in prior if row["witness"] in keys]
    new_order = [key for _, key, _ in witnesses if key in prior_by_key]
    if (removed and added) or (old_order != new_order and not (allow_reorder and not (removed or added))):
        raise CommandError(f"{name} has ambiguous row replacement or reordering. Owner adjudication is required.")
    ids = {key: prior_by_key[key]["id"] if key in prior_by_key else uuid4().hex
           for _, key, _ in witnesses}
    return ([{"row": position, "witness": key, "id": ids[key], "parent_id": ids.get(parent)}
             for position, key, parent in witnesses], [row["id"] for row in removed])
