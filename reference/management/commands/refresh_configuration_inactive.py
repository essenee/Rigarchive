"""Preview or explicitly apply the approved Tacoma Inactive update."""
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reference.configuration_logic import select_generation
from reference.configuration_logic_changelog import sync_after_revision
from reference.configuration_logic_google import api_call, connect, digest, read_registry, registry_lock
from reference.configuration_logic_inactive import MANUAL_TRIMS, YEARS, plan_inactive, verify_inactive
from reference.configuration_logic_layout import INACTIVE_INDEX, column_order
from reference.configuration_logic_revisions import (
    capture_remote, check_working_remote, current_draft, load_layout, load_revision, save_remote,
)


class Command(BaseCommand):
    help = "Preview Tacoma Inactive migration or refresh. Apply only with the reviewed preview hash."

    def add_arguments(self, parser):
        parser.add_argument("--migrate", action="store_true")
        parser.add_argument("--apply", metavar="PREVIEW_HASH")

    def handle(self, *args, **options):
        generation = select_generation("Toyota", "Tacoma", "fourth-generation")
        directory = Path(settings.BASE_DIR) / ".configuration-logic"
        key = str(generation.uuid)
        registry = directory / f"{key}.json"
        approved = options["apply"]
        migrate = options["migrate"]
        with registry_lock(registry) if approved else nullcontext():
            state = read_registry(registry, key)
            if not state or load_layout(state, registry) is None:
                raise CommandError("An enrolled Tacoma working revision is required.")
            previous = load_revision(state, registry)
            draft = current_draft(generation, registry, state)
            if not set(YEARS) <= previous.keys():
                raise CommandError("The registered Tacoma workbook is missing a model-year tab.")
            api = connect(directory, persist=False)
            remote = check_working_remote(api, draft, state, previous, flexible=True, report=self.stdout.write)
            enrolled = {name for name in YEARS if INACTIVE_INDEX in column_order(name, remote[name])}
            if migrate and enrolled:
                if enrolled == set(YEARS):
                    rows = next(t for t in draft.sheets if t.name == "MY2026")
                    pk_field = load_layout(state, registry)["sheets"]["MY2026"]["columns"]["configuration.pk"] - 1
                    if MANUAL_TRIMS.keys() <= {row[pk_field] for row in rows.rows[rows.header_row:]}:
                        self.stdout.write("Inactive migration already registered.")
                        return
                raise CommandError("Inactive migration is incomplete. Inspect before any retry.")

            def vehicles():
                return {v.pk: v for v in generation.vehicle_definitions.select_related(
                    "factory_body_configuration__bed_length", "engine",
                )}

            requests, expected = plan_inactive(draft, remote, vehicles(), migrate=migrate)
            if not requests:
                self.stdout.write("All registered Inactive cells already match.")
                return
            tag = digest({"base": state["working_revision"], "remote": remote, "requests": requests, "migrate": migrate})
            if not approved:
                self.stdout.write(f"Preview only. Base {state['working_revision']['id']}, {len(requests)} Sheets requests.")
                if migrate:
                    self.stdout.write("Insert Inactive after Base MSRP on MY2024, MY2025, MY2026; "
                                      "append MY2026 VehicleDefinition PKs 1170, 1178, 1181.")
                else:
                    for request in requests:
                        start = request["updateCells"]["start"]
                        self.stdout.write(f"Sheet {start['sheetId']}, row {start['rowIndex'] + 1}, "
                                          f"column {start['columnIndex'] + 1}.")
                self.stdout.write(f"Reviewed preview hash: {tag}")
                return
            if approved != tag:
                raise CommandError("Inactive preview is stale. Inspect and obtain approval for a new preview.")
            if capture_remote(api, draft, state) != remote or plan_inactive(draft, remote, vehicles(), migrate=migrate)[0] != requests:
                raise CommandError("Workbook or canonical status changed during preflight. Nothing was published.")
            api_call("spreadsheets.batchUpdate", api.batchUpdate, spreadsheetId=state["spreadsheet"],
                     body={"requests": requests})
            result = capture_remote(api, draft, state)
            verify_inactive(remote, result, expected)
            operation = "inactive-migration" if migrate else "inactive-refresh"
            revision = save_remote(api, draft, registry, state, result, previous, operation=operation)
            self.stdout.write(f"Registered working revision {revision}.")
            sync_after_revision(api, draft, registry, read_registry(registry, key), self.stdout.write)
