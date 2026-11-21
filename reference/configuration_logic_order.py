"""Project approved B3 row numbers onto existing canonical configurations."""
from django.core.management.base import CommandError

from reference.configuration_logic_layout import uses_numbering
from reference.configuration_logic_revisions import validated_rows


def configurator_order_plan(draft, remote, vehicles, years):
    """Verify complete standalone correspondence before returning any changes."""
    tables = {t.name: t for t in draft.sheets}
    plan, seen = [], set()
    for year in sorted(years):
        name = f"MY{year}"
        if name not in tables or not uses_numbering(name, remote[name]):
            raise CommandError(f"{name} requires a registered calculated number column.")
        table = tables[name]
        rows = validated_rows(table, remote[name], flexible=True)
        numbered_rows = [row for row in rows[table.header_row:] if row[0] is not None]
        if not numbered_rows or [row[0] for row in numbered_rows] != list(range(1, len(numbered_rows) + 1)):
            raise CommandError(f"{name} requires sequential calculated configuration numbers.")
        for row in numbered_rows:
            number, pk, _, trim = row[:4]
            vehicle = vehicles.get(pk)
            if (not trim or vehicle is None or pk in seen or vehicle.model_year != year
                    or (vehicle.slug, vehicle.trim_name, vehicle.get_market_display(), vehicle.get_drivetrain_display())
                    != (row[12], trim, row[13], row[7])):
                raise CommandError(f"{name} configuration #{number} lacks an exact standalone canonical correspondence.")
            seen.add(pk)
            plan.append({"year": year, "number": number, "pk": pk, "uuid": str(vehicle.uuid),
                         "slug": vehicle.slug, "trim": trim, "before": vehicle.configurator_order})
    return plan
