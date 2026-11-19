"""Inspect or register human-edited Google Sheets drafts."""
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reference.configuration_logic import select_generation
from reference.configuration_logic_google import connect, read_registry, registry_lock
from reference.configuration_logic_revisions import (
    capture_remote, changes_between, current_draft, load_revision, save_remote, validated_rows, working_history,
)


class Command(BaseCommand):
    help = "Inspect remote edits or register an explicitly confirmed working revision."
    requires_system_checks = []

    def add_arguments(self, parser):
        for name in ("manufacturer", "model", "generation"):
            parser.add_argument(f"--{name}", required=True)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--inspect", action="store_true")
        mode.add_argument("--save", action="store_true")
        mode.add_argument("--history", action="store_true", help="List locally registered working revisions.")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **options):
        if options["save"] != options["confirm"]:
            raise CommandError("Use --save --confirm to register a working revision.")
        generation = select_generation(options["manufacturer"], options["model"], options["generation"])
        directory = Path(settings.BASE_DIR) / ".configuration-logic"
        key = str(generation.uuid)
        path = directory / f"{key}.json"
        try:
            with registry_lock(path) if options["save"] else nullcontext():
                state = read_registry(path, key)
                if not state or not state["sheets"]:
                    raise CommandError("A registered workbook with worksheet IDs is required.")
                if options["history"]:
                    history = list(working_history(path, state))
                    if not history:
                        self.stdout.write("No registered working revisions.")
                    for revision, captured in history:
                        self.stdout.write(f"{revision}  {captured}  working draft")
                    return
                draft = current_draft(generation, path, state)
                previous = load_revision(state, path)
                api = connect(directory, persist=False)
                remote = capture_remote(api, draft, state)
                if options["save"]:
                    revision = save_remote(api, draft, path, state, remote, previous)
                    self.stdout.write(f"Registered working revision {revision}." if revision else "No new revision needed.")
                    return
                if previous is None:
                    self.stdout.write("No trustworthy local comparison baseline exists. Current values can be inspected, but prior edits cannot be reconstructed.")
                changes = changes_between(previous, remote, draft.sheets)
                for table in draft.sheets:
                    name = table.name
                    change = changes[name]
                    self.stdout.write(f"{name}")
                    if "baseline" in change:
                        self.stdout.write(f"  Captured {change['captured_values']} populated cells.")
                    else:
                        self.stdout.write(f"  Values changed: {len(change['cells'])}; notes changed: {len(change['notes'])}; "
                                          f"headers changed: {change['headers_changed']}; metadata changed: {change['sheet_metadata_changed']}")
                        if change["fingerprint_changed"] and not (change["cells"] or change["notes"]):
                            self.stdout.write("  Captured formatting or sheet metadata changed.")
                        for kind, old_start, old_size, new_start, new_size in change["row_changes"]:
                            self.stdout.write(f"  Rows {kind}: previous row {old_start} ({old_size}), current row {new_start} ({new_size})")
                        for kind in ("cells", "notes"):
                            for item in change[kind]:
                                self.stdout.write(f"  {kind} R{item['row']}C{item['column']}: "
                                                  f"{item['before']!r} → {item['after']!r}")
                    try:
                        validated_rows(table, remote[name])
                    except CommandError as exc:
                        self.stdout.write(f"  Incompatible: {exc}")
        except OSError as exc:
            raise CommandError("Could not persist or inspect the working revision directory.") from exc
