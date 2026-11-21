"""Preview or publish calculated numbering for a B3-enrolled workbook."""
from contextlib import nullcontext
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from reference.configuration_logic import select_generation
from reference.configuration_logic_google import connect, read_registry, registry_lock
from reference.configuration_logic_numbering import publish_numbering
from reference.configuration_logic_revisions import current_draft


class Command(BaseCommand):
    help = "Preview automatic CL numbering or apply the exact reviewed preview."

    def add_arguments(self, parser):
        for name in ("manufacturer", "model", "generation"):
            parser.add_argument(f"--{name}", required=True)
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--dry-run", action="store_true")
        modes.add_argument("--apply", metavar="PREVIEW_HASH")

    def handle(self, *args, **options):
        generation = select_generation(options["manufacturer"], options["model"], options["generation"])
        directory = Path(settings.BASE_DIR) / ".configuration-logic"
        key = str(generation.uuid)
        registry = directory / f"{key}.json"
        apply_hash = options["apply"]
        with registry_lock(registry) if apply_hash else nullcontext():
            state = read_registry(registry, key)
            if not state or not state.get("working_revision"):
                raise CommandError("Automatic numbering requires an enrolled B3 revision.")
            draft = current_draft(generation, registry, state)
            count, preview_hash, revision = publish_numbering(
                connect(directory, persist=False), draft, registry, state, apply_hash=apply_hash,
            )
        if revision:
            self.stdout.write(f"Published {count} model-year tabs and verified working revision {revision}.")
        elif count:
            self.stdout.write(f"Preview only. Base {state['working_revision']['id']}, {count} model-year tabs.")
            self.stdout.write(f"Reviewed preview hash: {preview_hash}")
        else:
            self.stdout.write("All registered model-year tabs already use automatic numbering.")
