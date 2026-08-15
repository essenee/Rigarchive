from datetime import datetime
from pathlib import Path
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Creates a physical Layer 1 recovery snapshot of db.sqlite3 using SQLite VACUUM INTO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Optional custom output path for the snapshot SQLite file.",
        )

    def handle(self, *args, **options):
        snapshots_dir = settings.BASE_DIR / "backups" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        if options.get("output"):
            output_path = Path(options["output"]).resolve()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = snapshots_dir / f"db_snapshot_{timestamp}.sqlite3"

        if output_path.exists():
            raise CommandError(
                f"Snapshot target file already exists: {output_path}. Refusing to overwrite."
            )

        self.stdout.write(f"Executing VACUUM INTO '{output_path}'...")

        src_db_path = settings.DATABASES["default"]["NAME"]

        try:
            # Connect directly to source SQLite database file to ensure autocommit mode for VACUUM INTO
            db_str = str(src_db_path)
            if db_str.startswith("file:") or "?" in db_str:
                src_conn = sqlite3.connect(db_str, uri=True)
            else:
                src_conn = sqlite3.connect(db_str)
            try:
                src_conn.execute(f"VACUUM INTO '{output_path}'")
            finally:
                src_conn.close()

        except Exception as exc:
            if output_path.exists():
                output_path.unlink()
            raise CommandError(f"VACUUM INTO failed: {exc}") from exc


        # Physical snapshot verification
        self.stdout.write("Verifying physical snapshot integrity...")
        try:
            conn = sqlite3.connect(output_path)
            try:
                # 1. Integrity check
                integrity_result = conn.execute("PRAGMA integrity_check;").fetchone()
                if not integrity_result or integrity_result[0] != "ok":
                    raise CommandError(f"PRAGMA integrity_check failed: {integrity_result}")

                # 2. Verify table existence
                required_tables = [
                    "accounts_user",
                    "reference_manufacturer",
                    "reference_vehiclemodel",
                    "reference_generation",
                    "reference_vehicledefinition",
                    "observation_observation",
                ]
                tables_in_db = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table';"
                    ).fetchall()
                }

                for table in required_tables:
                    if table not in tables_in_db:
                        raise CommandError(f"Required table missing in snapshot: {table}")

                # 3. Compare row counts with source database
                with connection.cursor() as src_cursor:
                    for table in required_tables:
                        src_count = src_cursor.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
                        snp_count = conn.execute(f"SELECT COUNT(*) FROM {table};").fetchone()[0]
                        if src_count != snp_count:
                            raise CommandError(
                                f"Row count mismatch for {table}: source={src_count}, snapshot={snp_count}"
                            )

            finally:
                conn.close()

        except Exception as exc:
            if output_path.exists():
                output_path.unlink()
            raise CommandError(f"Physical snapshot verification failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created and verified physical snapshot: {output_path}"
            )
        )
        return str(output_path)
