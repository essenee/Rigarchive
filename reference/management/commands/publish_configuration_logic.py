"""Plan or synchronize a draft generation workbook through desktop OAuth."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reference.configuration_logic import generation_draft, select_generation
from reference.configuration_logic_google import (
    RECOVERY_CAUTION, connect, create, publish, read_registry, recover_registry, registry_lock, release_reservation,
)


class Command(BaseCommand):
    help = "Plan or safely publish a generation-level Configuration Logic draft."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--manufacturer", required=True)
        parser.add_argument("--model", required=True)
        parser.add_argument("--generation", required=True, help="Generation slug or PK.")
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--dry-run", action="store_true", help="Offline plan unless --check-remote is supplied.")
        modes.add_argument("--publish", action="store_true", help="Synchronize a registered draft.")
        modes.add_argument("--inspect-reservation", action="store_true", help="Report local recovery state without contacting Google.")
        modes.add_argument("--recover-id", help="Verify and register an explicitly identified empty spreadsheet or exact draft.")
        modes.add_argument("--release-no-spreadsheet", action="store_true",
                           help=f"Release a pending reservation after an owner Drive search. {RECOVERY_CAUTION}")
        modes.add_argument("--authorize", action="store_true", help="Authorize desktop OAuth without publishing.")
        parser.add_argument("--confirm-recovery", action="store_true",
                            help="Explicitly authorize adoption or attest that the owner checked Drive before release.")
        parser.add_argument("--initialize", action="store_true", help="Explicitly create a new spreadsheet with no registry or after an audited release.")
        parser.add_argument("--check-remote", action="store_true", help="Read and verify the existing remote spreadsheet on a dry run.")
        parser.add_argument("--allow-shrink", action="store_true", help="Allow a smaller draft to clear formerly published cells.")

    def handle(self, *args, **options):
        directory = Path(settings.BASE_DIR) / ".configuration-logic"
        if options["initialize"] and not options["publish"]:
            raise CommandError("--initialize requires --publish.")
        if options["check_remote"] and not options["dry_run"]:
            raise CommandError("--check-remote requires --dry-run.")
        recovery = options["recover_id"] is not None or options["release_no_spreadsheet"]
        if recovery != options["confirm_recovery"]:
            raise CommandError("Use --confirm-recovery with --recover-id or --release-no-spreadsheet after checking Drive.")
        generation = select_generation(options["manufacturer"], options["model"], options["generation"])
        if options["authorize"]:
            connect(directory, authorize=True)
            self.stdout.write("Desktop OAuth authorized. No spreadsheet was published.")
            return
        draft = generation_draft(generation)
        path = directory / f"{draft.key}.json"
        if options["inspect_reservation"]:
            state = read_registry(path, draft.key, allow_pending=True)
            has_id = bool(state and state["spreadsheet"])
            has_pins = bool(state and state["sheets"])
            if state is None:
                status = "unregistered"
            elif has_id:
                status = "registered and fingerprinted" if has_pins else "registered without fingerprints"
            else:
                status = "released" if "release_audit" in state else "pending creation"
            self.stdout.write(f"Generation: {generation.name} ({generation.slug}, {draft.key})")
            self.stdout.write(f"Intended spreadsheet: {draft.title}")
            self.stdout.write(f"Reservation: {status}; spreadsheet ID: {'yes' if has_id else 'no'}; "
                              f"publication fingerprints: {'yes' if has_pins else 'no'}")
            if not has_pins:
                self.stdout.write("Known matching spreadsheet: --recover-id SPREADSHEET_ID --confirm-recovery.")
            if status == "pending creation":
                self.stdout.write("After checking Drive and confirming no match: --release-no-spreadsheet --confirm-recovery.")
            if status == "released":
                self.stdout.write("A separate --publish --initialize is available after owner review.")
            if has_pins:
                self.stdout.write("Trusted fingerprints exist; reservation recovery cannot replace them.")
            self.stdout.write(RECOVERY_CAUTION)
            return
        if options["dry_run"]:
            state = read_registry(path, draft.key, allow_pending=not options["check_remote"])
            if not options["check_remote"]:
                self.stdout.write(draft.title)
                for table in draft.sheets:
                    self.stdout.write(f"{table.name}: {len(table.rows) - 4} data rows")
                self.stdout.write("Offline plan only. Remote edits and identity were not checked.")
                if state and state["spreadsheet"] is None:
                    if "release_audit" in state:
                        self.stdout.write("Creation reservation released. A separate --publish --initialize is required.")
                    else:
                        self.stdout.write("Creation reservation pending with no spreadsheet ID. Preserve it and verify the outcome in Drive before retrying.")
                else:
                    self.stdout.write("Registry found." if state else "Unregistered. First publication requires explicit --initialize.")
                return
            if state is None:
                raise CommandError("No trusted registry for a remote dry run.")
            actions = publish(connect(directory, persist=False), draft, path, state, dry_run=True,
                              allow_shrink=options["allow_shrink"])
            self.stdout.write("\n".join(actions) or "Remote draft already matches.")
            return
        try:
            with registry_lock(path):
                if options["release_no_spreadsheet"]:
                    self.stdout.write(RECOVERY_CAUTION)
                    audit = release_reservation(draft, path, authorized=True)
                    self.stdout.write(f"Reservation released. Audit: recovery-audit/{audit}. No spreadsheet was created.")
                    return
                if options["recover_id"] is not None:
                    exact = recover_registry(connect(directory, persist=False), draft, path,
                                             options["recover_id"], authorized=True)
                    description = "exact remote draft" if exact else "empty remote spreadsheet"
                    self.stdout.write(f"Verified {description} and recorded its identity. No spreadsheet was changed.")
                    return
                state = read_registry(path, draft.key, allow_pending=options["initialize"])
                released = state is not None and "release_audit" in state
                if state is None and not options["initialize"]:
                    raise CommandError("Registry missing. Restore its backup, or explicitly initialize a first publication.")
                if state is not None and not released and options["initialize"]:
                    raise CommandError("Registry already exists. Inspect the reservation before retrying.")
                api = connect(directory)
                if state is None or released:
                    state = create(api, draft, path)
                actions = publish(api, draft, path, state, allow_shrink=options["allow_shrink"])
        except OSError:
            raise CommandError("Cannot read or persist the local publication registry. Check the state directory.") from None
        self.stdout.write("\n".join(actions) or "Remote draft already matches.")
        self.stdout.write(f"https://docs.google.com/spreadsheets/d/{state['spreadsheet']}/edit")
