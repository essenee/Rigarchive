import os
from pathlib import Path
import subprocess
import sys
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Verifies a Layer 2 logical JSON export by executing an isolated "
        "migration, restoration, and 11-point invariant validation cycle "
        "against an OS temporary SQLite database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            type=str,
            required=True,
            help="Path to the logical JSON export fixture file to verify.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(options["fixture"]).resolve()
        if not fixture_path.exists():
            raise CommandError(f"Specified fixture file does not exist: {fixture_path}")

        # Create temporary SQLite database in OS temp directory
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as tmp_file:
            temp_db_path = Path(tmp_file.name).resolve()

        self.stdout.write(
            f"Created isolated OS temporary verification database at '{temp_db_path}'"
        )

        try:
            env = os.environ.copy()
            env["RIGARCHIVE_TEST_DB_PATH"] = str(temp_db_path)

            python_bin = sys.executable

            # 1. Run manage.py migrate on temp DB
            self.stdout.write("Running migrations on temporary database...")
            mig_res = subprocess.run(
                [python_bin, "manage.py", "migrate", "--noinput"],
                env=env,
                capture_output=True,
                text=True,
            )
            if mig_res.returncode != 0:
                raise CommandError(
                    f"Migration on temporary database failed:\n{mig_res.stderr}"
                )

            # 2. Run manage.py loaddata on temp DB
            self.stdout.write(f"Restoring fixture '{fixture_path.name}' into temporary database...")
            load_res = subprocess.run(
                [python_bin, "manage.py", "loaddata", str(fixture_path)],
                env=env,
                capture_output=True,
                text=True,
            )
            if load_res.returncode != 0:
                raise CommandError(
                    f"Restoration (loaddata) on temporary database failed:\n{load_res.stderr}"
                )

            # 3. Run verification assertions script via python code in temp DB context
            self.stdout.write("Executing 11-point restoration invariant checks...")
            verify_script = """
import sys
from django.core.management import call_command
from accounts.models import User
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition
from observation.models import Observation

# System check
call_command("check")

# Validate model full_clean() on all restored records
for u in User.objects.all():
    u.full_clean()
for m in Manufacturer.objects.all():
    m.full_clean()
for vm in VehicleModel.objects.all():
    vm.full_clean()
for g in Generation.objects.all():
    g.full_clean()
for vd in VehicleDefinition.objects.all():
    vd.full_clean()
for o in Observation.objects.all():
    o.full_clean()

# Check relational links
for o in Observation.objects.all():
    assert o.vehicle_definition is not None, "Observation vehicle_definition missing"
    assert o.recorded_by is not None, "Observation recorded_by missing"

for vd in VehicleDefinition.objects.all():
    assert vd.generation is not None, "VehicleDefinition generation missing"

for g in Generation.objects.all():
    assert g.vehicle_model is not None, "Generation vehicle_model missing"

for vm in VehicleModel.objects.all():
    assert vm.manufacturer is not None, "VehicleModel manufacturer missing"

print(f"VERIFIED: Users={User.objects.count()}, Mfrs={Manufacturer.objects.count()}, Models={VehicleModel.objects.count()}, Gens={Generation.objects.count()}, Defs={VehicleDefinition.objects.count()}, Obs={Observation.objects.count()}")
"""

            ver_res = subprocess.run(
                [python_bin, "manage.py", "shell", "-c", verify_script],
                env=env,
                capture_output=True,
                text=True,
            )
            if ver_res.returncode != 0:
                raise CommandError(
                    f"Invariant verification on temporary database failed:\n{ver_res.stderr}"
                )

            self.stdout.write(self.style.SUCCESS(ver_res.stdout.strip()))

        finally:
            if temp_db_path.exists():
                temp_db_path.unlink()
                self.stdout.write(f"Cleaned up temporary database '{temp_db_path}'")

        self.stdout.write(
            self.style.SUCCESS(
                f"Isolated verification of fixture '{fixture_path.name}' passed 100% cleanly!"
            )
        )
