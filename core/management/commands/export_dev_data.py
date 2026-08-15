from datetime import datetime
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates a portable Layer 2 logical JSON data export of development data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Optional custom output path for the logical JSON export.",
        )

    def handle(self, *args, **options):
        logical_dir = settings.BASE_DIR / "backups" / "logical"
        logical_dir.mkdir(parents=True, exist_ok=True)

        if options.get("output"):
            output_path = Path(options["output"]).resolve()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = logical_dir / f"dev_data_{timestamp}.json"

        if output_path.exists():
            raise CommandError(
                f"Export target file already exists: {output_path}. Refusing to overwrite."
            )

        self.stdout.write(f"Generating logical export to '{output_path}'...")

        models_to_export = [
            "accounts.User",
            "auth.Group",
            "reference.Manufacturer",
            "reference.VehicleModel",
            "reference.Generation",
            "reference.VehicleDefinition",
            "observation.Observation",
        ]

        buf = StringIO()
        try:
            call_command(
                "dumpdata",
                *models_to_export,
                exclude=["contenttypes", "auth.Permission", "sessions"],
                natural_foreign=True,
                indent=2,
                stdout=buf,
            )
        except Exception as exc:
            raise CommandError(f"dumpdata execution failed: {exc}") from exc

        content = buf.getvalue()
        if not content.strip():
            raise CommandError("dumpdata output is empty.")

        output_path.write_text(content, encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created logical export ({len(content)} bytes): {output_path}"
            )
        )
        return str(output_path)
