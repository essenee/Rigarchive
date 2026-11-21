"""Synchronize canonical configurator ordering from verified B3 worksheets."""
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reference.configuration_logic import select_generation
from reference.configuration_logic_google import connect, digest, read_registry, registry_lock
from reference.configuration_logic_order import configurator_order_plan
from reference.configuration_logic_revisions import check_working_remote, current_draft, load_layout, load_revision
from reference.models import VehicleDefinition


class Command(BaseCommand):
    help = "Preview or apply Configurator # values from approved, numbered B3 worksheets."

    def add_arguments(self, parser):
        for name in ("manufacturer", "model", "generation"):
            parser.add_argument(f"--{name}", required=True)
        parser.add_argument("--year", action="append", type=int, required=True)
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
        with registry_lock(registry) if approved else nullcontext():
            state = read_registry(registry, key)
            if not state or load_layout(state, registry) is None:
                raise CommandError("An enrolled B3 working revision is required.")
            baseline = load_revision(state, registry)
            draft = current_draft(generation, registry, state)
            api = connect(directory, persist=False)
            remote = check_working_remote(api, draft, state, baseline, flexible=True)
            with transaction.atomic() if approved else nullcontext():
                records = generation.vehicle_definitions.filter(model_year__in=years)
                if approved:
                    records = records.select_for_update()
                vehicles = records.in_bulk()
                plan = configurator_order_plan(draft, remote, vehicles, years)
                preview = digest({"revision": state["working_revision"], "assignments": plan})
                changes = [entry for entry in plan if entry["before"] != entry["number"]]
                if approved:
                    if approved != preview:
                        raise CommandError("Configurator order preview is stale. Run a new dry-run.")
                    latest = check_working_remote(api, draft, state, baseline, flexible=True)
                    if configurator_order_plan(draft, latest, vehicles, years) != plan:
                        raise CommandError("Configurator order changed during preflight. No records were updated.")
                    for entry in changes:
                        vehicles[entry["pk"]].configurator_order = entry["number"]
                    count = VehicleDefinition.objects.bulk_update(
                        [vehicles[entry["pk"]] for entry in changes], ["configurator_order"],
                    )
                    if count != len(changes):
                        raise CommandError("Could not update every previewed configuration.")
        for entry in plan:
            self.stdout.write(f"MY{entry['year']} #{entry['number']:02} → PK {entry['pk']} ({entry['trim']})")
        self.stdout.write(f"B3 revision {state['working_revision']['id']}. {len(plan)} verified correspondences.")
        if approved:
            self.stdout.write(f"Updated {len(changes)} Configurator # values.")
        else:
            self.stdout.write(f"Preview only. {len(changes)} Configurator # values would change.")
            self.stdout.write(f"Reviewed preview hash: {preview}")
