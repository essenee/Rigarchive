"""Stable draft field and row bindings for the Configuration Logic workbook."""
from uuid import uuid4

from django.core.management.base import CommandError

from reference.configuration_logic import HEADERS, SOURCE_HEADERS
from reference.configuration_logic_google import digest, remote_values


CONFIG_FIELDS = (
    "number", "pk", "model_code", "trim", "body", "cab", "nominal_bed", "drivetrain",
    "engine_code", "engine_variant", "engine", "base_msrp", "slug", "market", "transmission",
    "conditional_output", "alternate_model_code", "alternate_msrp", "package",
    "applicability", "provenance",
)
SOURCE_FIELDS = ("model_year", "organization", "title", "locator", "reviewed_at",
                 "source_type", "evidence_id", "verification", "notes")


def catalog(name):
    if name == "Source References":
        return tuple(zip((f"source.{f}" for f in SOURCE_FIELDS), SOURCE_HEADERS, strict=True))
    return tuple(zip((f"configuration.{f}" for f in CONFIG_FIELDS), HEADERS, strict=True))


def column_order(name, sheet):
    """Return canonical-column indices in their observed physical order."""
    fields = catalog(name)
    index = {header: i for i, (_, header) in enumerate(fields)}
    values = remote_values(sheet)
    headers = {c: value.get("stringValue") for (r, c), value in values.items() if r == 3}
    if set(headers) != set(range(len(fields))) or set(headers.values()) != set(index):
        raise CommandError(f"{name} column headers are missing, duplicated, or renamed.")
    return tuple(index[headers[col]] for col in range(len(fields)))


def canonical_row(row, order):
    return tuple(row[order.index(index)] for index in range(len(order)))


def row_witnesses(name, rows):
    """Conservative continuity witnesses. These hashes are not the opaque row IDs."""
    parents = {}
    result = []
    for position, row in enumerate(rows[4:], 5):
        if not any(value is not None and value != "" for value in row):
            continue
        parent = None
        if name == "Source References":
            witness = ("source", *(row[i] for i in (0, 1, 2, 3, 6)))
        elif row[3]:
            witness = ("configuration", *(row[i] for i in (3, 4, 5, 6, 7, 8, 9, 13)))
            parents[row[0]] = digest(witness)
        else:
            parent = parents[row[0]]
            witness = ("alternative", parent, *(row[i] for i in (14, 15, 16, 18)))
        result.append((position, digest(witness), parent))
    signatures = [item[1] for item in result]
    if len(set(signatures)) != len(signatures):
        raise CommandError(f"{name} has ambiguous working-row identities. Review duplicate configuration or source rows.")
    return result


def bind_rows(name, rows, prior):
    witnesses = row_witnesses(name, rows)
    prior_by_key = {row["witness"]: row for row in prior}
    keys = {signature for _, signature, _ in witnesses}
    removed = [row for row in prior if row["witness"] not in keys]
    added = keys - prior_by_key.keys()
    old_order = [row["witness"] for row in prior if row["witness"] in keys]
    new_order = [key for _, key, _ in witnesses if key in prior_by_key]
    if (removed and added) or old_order != new_order:
        raise CommandError(f"{name} has ambiguous row replacement or reordering. Owner adjudication is required.")
    ids = {key: prior_by_key[key]["id"] if key in prior_by_key else uuid4().hex
           for _, key, _ in witnesses}
    return ([{"row": position, "witness": key, "id": ids[key], "parent_id": ids.get(parent)}
             for position, key, parent in witnesses], [row["id"] for row in removed])
