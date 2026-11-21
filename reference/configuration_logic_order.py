"""Project approved B3 row numbers onto existing canonical configurations."""
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

from reference.configuration_logic_layout import uses_numbering
from reference.configuration_logic_revisions import validated_rows
from reference.transmission import normalize_source_transmission, transmission_identity


def configurator_order_plan(draft, remote, vehicles, years, *, transmission=False, row_ids=None):
    """Verify complete standalone correspondence before returning any changes."""
    tables = {t.name: t for t in draft.sheets}
    plan, seen = [], set()
    for year in sorted(years):
        name = f"MY{year}"
        if name not in tables or not uses_numbering(name, remote[name]):
            raise CommandError(f"{name} requires a registered calculated number column.")
        table = tables[name]
        rows = validated_rows(table, remote[name], flexible=True)
        numbered_rows = [(position, row) for position, row in enumerate(rows[table.header_row:], table.header_row + 1)
                         if row[0] is not None]
        if not numbered_rows or [row[0] for _, row in numbered_rows] != list(range(1, len(numbered_rows) + 1)):
            raise CommandError(f"{name} requires sequential calculated configuration numbers.")
        for position, row in numbered_rows:
            number, pk, _, trim = row[:4]
            vehicle = vehicles.get(pk)
            if (not trim or vehicle is None or pk in seen or vehicle.model_year != year
                    or (vehicle.slug, vehicle.trim_name, vehicle.get_market_display(), vehicle.get_drivetrain_display())
                    != (row[12], trim, row[13], row[7])):
                raise CommandError(f"{name} configuration #{number} lacks an exact standalone canonical correspondence.")
            seen.add(pk)
            entry = {"year": year, "number": number, "pk": pk, "uuid": str(vehicle.uuid),
                     "slug": vehicle.slug, "trim": trim, "before": vehicle.configurator_order}
            if transmission:
                if row[8] and (not vehicle.engine_id or vehicle.engine.engine_code != row[8]
                               or (vehicle.engine.internal_variant_key or None) != row[9]):
                    raise CommandError(f"{name} configuration #{number} differs from its canonical Engine correspondence.")
                supplied = row[14]
                try:
                    target = None if supplied in (None, "", "Unresolved") else normalize_source_transmission(supplied)
                except ValidationError as exc:
                    raise CommandError(f"{name} configuration #{number} has an unsupported transmission: {supplied!r}.") from exc
                existing = vehicle.transmission
                status = ("unresolved" if target is None else
                          "populate" if not existing else
                          "matching" if transmission_identity(existing) == target else "conflict")
                entry.update(row_id=row_ids[name][position], cl_transmission=supplied,
                             transmission_before=existing, transmission_target=target, transmission_status=status)
            plan.append(entry)
    return plan
