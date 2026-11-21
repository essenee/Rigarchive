"""Synchronize canonical configurator ordering from verified B3 worksheets."""
from contextlib import nullcontext
from collections import Counter
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reference.configuration_logic import select_generation
from reference.configuration_logic_google import connect, digest, read_registry, registry_lock, remote_values
from reference.configuration_logic_order import configurator_order_plan
from reference.configuration_logic_revisions import check_working_remote, current_draft, load_layout, load_revision
from reference.models import VehicleDefinition


class Command(BaseCommand):
    help = "Preview or apply Configurator # values and optionally fill transmissions from a pinned B3 revision."

    def add_arguments(self, parser):
        for name in ("manufacturer", "model", "generation"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--year", action="append", type=int, required=True)
        parser.add_argument("--transmission", action="store_true", help="Also fill blank canonical transmissions.")
        parser.add_argument("--revision", help="Require this exact B3 revision and registered cell order.")
        parser.add_argument("--json", action="store_true", help="Output a machine-readable plan and reconciliation report.")
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", metavar="PREVIEW_HASH")

    def handle(self, *args, **options):
        generation = select_generation(options["manufacturer"], options["model"], options["generation"])
        years = set(options["year"])
        directory = Path(settings.BASE_DIR) / ".configuration-logic"
        key = str(generation.uuid)
        registry = directory / f"{key}.json"
        approved = options["apply"]
        include_transmission = options["transmission"]
        revision = options["revision"]
        if include_transmission and not revision:
            raise CommandError("--transmission requires an exact --revision.")
        with registry_lock(registry) if approved else nullcontext():
            state = read_registry(registry, key)
            layout = load_layout(state, registry) if state else None
            if layout is None:
                raise CommandError("An enrolled B3 working revision is required.")
            if revision and revision != state["working_revision"]["id"]:
                raise CommandError("The requested B3 revision is not the registered head.")
            baseline = load_revision(state, registry)
            draft = current_draft(generation, registry, state)
            api = connect(directory, persist=False)
            def verified_remote():
                remote = check_working_remote(api, draft, state, baseline, flexible=True)
                if revision and any(remote_values(sheet) != remote_values(baseline[name])
                                    for name, sheet in remote.items()):
                    raise CommandError("The live workbook differs from the exact registered revision.")
                return remote

            remote = verified_remote()
            row_ids = {name: {row["row"]: row["id"] for row in entry["rows"]}
                       for name, entry in layout["sheets"].items()}
            plan_options = {"transmission": include_transmission, "row_ids": row_ids}
            with transaction.atomic() if approved else nullcontext():
                records = generation.vehicle_definitions.filter(model_year__in=years)
                if include_transmission:
                    records = records.select_related("engine")
                if approved:
                    records = records.select_for_update()
                vehicles = records.in_bulk()
                plan = configurator_order_plan(draft, remote, vehicles, years, **plan_options)
                preview = digest({"revision": state["working_revision"], "assignments": plan})
                changes = [entry for entry in plan if entry["before"] != entry["number"]]
                transmissions = [entry for entry in plan if entry.get("transmission_status") == "populate"]
                out_of_scope = sorted(vehicles.keys() - {entry["pk"] for entry in plan})
                if approved:
                    if approved != preview:
                        raise CommandError("Configurator order preview is stale. Run a new dry-run.")
                    if configurator_order_plan(draft, verified_remote(), vehicles, years, **plan_options) != plan:
                        raise CommandError("Configurator order changed during preflight. No records were updated.")
                    for entry in transmissions:
                        vehicle = vehicles[entry["pk"]]
                        vehicle.transmission = entry["transmission_target"]
                        vehicle.save(update_fields=["transmission"])
                    for entry in changes:
                        vehicles[entry["pk"]].configurator_order = entry["number"]
                    count = VehicleDefinition.objects.bulk_update(
                        [vehicles[entry["pk"]] for entry in changes], ["configurator_order"],
                    )
                    if count != len(changes):
                        raise CommandError("Could not update every previewed configuration.")
        counts = Counter(entry["transmission_status"] for entry in plan) if include_transmission else None
        if options["json"]:
            self.stdout.write(json.dumps({
                "spreadsheet": state["spreadsheet"], "revision": state["working_revision"]["id"],
                "preview_hash": preview, "applied": bool(approved), "rows": plan,
                "order_changes": len(changes), "order_matching": len(plan) - len(changes),
                "transmissions": dict(counts) if counts is not None else None, "out_of_scope_pks": out_of_scope,
            }, indent=2))
            return
        for entry in plan:
            self.stdout.write(f"MY{entry['year']} #{entry['number']:02} → PK {entry['pk']} ({entry['trim']})")
        self.stdout.write(f"B3 revision {state['working_revision']['id']}. {len(plan)} verified correspondences.")
        if counts is not None:
            self.stdout.write(f"Transmissions: {counts['populate']} {'populated' if approved else 'to populate'}, "
                              f"{counts['matching']} matching, {counts['conflict']} conflicts, {counts['unresolved']} unresolved.")
            for entry in plan:
                if entry["transmission_status"] in ("unresolved", "conflict"):
                    self.stdout.write(f"MY{entry['year']} PK {entry['pk']}: {entry['transmission_status']} "
                                      f"(CL {entry['cl_transmission']!r}, canonical {entry['transmission_before']!r}).")
            self.stdout.write(f"Out-of-scope PKs in selected years: {out_of_scope}.")
        if approved:
            self.stdout.write(f"Updated {len(changes)} Configurator # values.")
        else:
            self.stdout.write(f"Preview only. {len(changes)} Configurator # values would change.")
            self.stdout.write(f"Reviewed preview hash: {preview}")
