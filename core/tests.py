import time
import uuid
from datetime import datetime

from django.db import connection
from django.test import TestCase

from core.models import BaseModel, TimestampedModel, UUIDModel
from reference.models import (
    Generation,
    Manufacturer,
    VehicleDefinition,
    VehicleModel,
)


class CoreMixinTests(TestCase):
    """
    Tests verifying abstract model mixins and inherited behavior.
    """

    def test_core_mixins_are_abstract(self) -> None:
        self.assertTrue(UUIDModel._meta.abstract)
        self.assertTrue(TimestampedModel._meta.abstract)
        self.assertTrue(BaseModel._meta.abstract)

    def test_no_concrete_tables_for_core_mixins(self) -> None:
        table_names = connection.introspection.table_names()
        self.assertNotIn("core_uuidmodel", table_names)
        self.assertNotIn("core_timestampedmodel", table_names)
        self.assertNotIn("core_basemodel", table_names)

    def test_reference_models_inherit_uuid_and_timestamps(self) -> None:
        for model in (Manufacturer, VehicleModel, Generation, VehicleDefinition):
            with self.subTest(model=model.__name__):
                self.assertTrue(issubclass(model, BaseModel))
                self.assertTrue(issubclass(model, UUIDModel))
                self.assertTrue(issubclass(model, TimestampedModel))

                field_names = [f.name for f in model._meta.get_fields()]
                self.assertIn("uuid", field_names)
                self.assertIn("created_at", field_names)
                self.assertIn("updated_at", field_names)

    def test_newly_created_object_receives_valid_uuid(self) -> None:
        manufacturer = Manufacturer.objects.create(name="Ford", country_code="US")
        self.assertIsInstance(manufacturer.uuid, uuid.UUID)
        self.assertNotEqual(str(manufacturer.uuid), "")

    def test_uuid_is_distinct_from_integer_primary_key(self) -> None:
        manufacturer = Manufacturer.objects.create(name="Jeep", country_code="US")
        self.assertIsInstance(manufacturer.id, int)
        self.assertIsInstance(manufacturer.uuid, uuid.UUID)
        self.assertNotEqual(manufacturer.id, manufacturer.uuid)
        self.assertNotEqual(str(manufacturer.id), str(manufacturer.uuid))

    def test_timestamps_populated_and_updated_on_save(self) -> None:
        manufacturer = Manufacturer.objects.create(name="Subaru", country_code="JP")

        self.assertIsInstance(manufacturer.created_at, datetime)
        self.assertIsInstance(manufacturer.updated_at, datetime)

        initial_created = manufacturer.created_at
        initial_updated = manufacturer.updated_at

        time.sleep(0.01)
        manufacturer.country_code = "US"
        manufacturer.save()
        manufacturer.refresh_from_db()

        self.assertEqual(manufacturer.created_at, initial_created)
        self.assertGreater(manufacturer.updated_at, initial_updated)


import json
from pathlib import Path
import sqlite3
import tempfile

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

from accounts.models import User
from observation.models import Observation


class DataPreservationTestCase(TransactionTestCase):
    """
    Automated synthetic test suite for development data preservation and recovery tooling.
    """

    def setUp(self):
        super().setUp()
        # Create synthetic user
        self.user = User.objects.create_user(
            username="test_contributor",
            email="contributor@example.com",
            password="SecurePassword123!",
            display_name="Test Contributor",
            is_contributor=True,
            is_staff=True,
        )

        # Create synthetic group and permissions
        self.group = Group.objects.create(name="Archive Maintainers")
        user_content_type = ContentType.objects.get_for_model(User)
        perm1 = Permission.objects.filter(content_type=user_content_type).first()
        if perm1:
            self.group.permissions.add(perm1)
            self.user.user_permissions.add(perm1)
        self.user.groups.add(self.group)

        # Create synthetic reference hierarchy
        self.manufacturer = Manufacturer.objects.create(
            name="Test Manufacturer",
            country_code="US",
        )
        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="Test Model",
        )
        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="First Generation",
            start_year=2010,
            end_year=2015,
        )
        self.vehicle_definition = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2012,
            trim_name="Base",
            engine_name="2.0L I4",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
        )

        # Create synthetic observation
        self.observation = Observation.objects.create(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Synthetic Test Observation",
            description="Synthetic description text for preservation testing.",
            source_notes="Captured via synthetic unit test.",
        )

    def test_physical_snapshot_command(self):
        """
        Verify Layer 1 snapshot_db management command creates a valid SQLite backup.
        """
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=True) as tmp:
            tmp_path = Path(tmp.name)

        try:
            call_command("snapshot_db", output=str(tmp_path))
            self.assertTrue(tmp_path.exists())

            # Verify SQLite integrity check
            conn = sqlite3.connect(tmp_path)
            try:
                res = conn.execute("PRAGMA integrity_check;").fetchone()
                self.assertEqual(res[0], "ok")

                user_count = conn.execute("SELECT COUNT(*) FROM accounts_user;").fetchone()[0]
                self.assertGreaterEqual(user_count, 1)

                obs_count = conn.execute("SELECT COUNT(*) FROM observation_observation;").fetchone()[0]
                self.assertGreaterEqual(obs_count, 1)
            finally:
                conn.close()

        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_logical_export_and_restore_cycle(self):
        """
        Verify Layer 2 export_dev_data and loaddata restoration on synthetic dataset.
        """
        original_mfr_uuid = str(self.manufacturer.uuid)
        original_model_uuid = str(self.vehicle_model.uuid)
        original_gen_uuid = str(self.generation.uuid)
        original_def_uuid = str(self.vehicle_definition.uuid)
        original_obs_uuid = str(self.observation.uuid)
        original_password_hash = self.user.password

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=True) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # 1. Export logical data
            call_command("export_dev_data", output=str(tmp_path))
            self.assertTrue(tmp_path.exists())
            self.assertGreater(tmp_path.stat().st_size, 0)

            # Inspect exported JSON structure
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertIsInstance(data, list)
            model_names = {item["model"] for item in data}
            self.assertIn("accounts.user", model_names)
            self.assertIn("reference.manufacturer", model_names)
            self.assertIn("observation.observation", model_names)
            self.assertNotIn("contenttypes.contenttype", model_names)
            self.assertNotIn("auth.permission", model_names)

            # 2. Clear database objects
            Observation.objects.all().delete()
            VehicleDefinition.objects.all().delete()
            Generation.objects.all().delete()
            VehicleModel.objects.all().delete()
            Manufacturer.objects.all().delete()
            User.objects.all().delete()
            Group.objects.all().delete()

            self.assertEqual(User.objects.count(), 0)
            self.assertEqual(Manufacturer.objects.count(), 0)

            # 3. Restore logical data using loaddata
            call_command("loaddata", str(tmp_path))

            # 4. Assert invariant checks
            restored_user = User.objects.get(username="test_contributor")
            self.assertEqual(restored_user.email, "contributor@example.com")
            self.assertEqual(restored_user.display_name, "Test Contributor")
            self.assertTrue(restored_user.is_contributor)
            self.assertTrue(restored_user.is_staff)
            self.assertEqual(restored_user.password, original_password_hash)

            # Verify authentication works with preserved hash
            self.assertTrue(restored_user.check_password("SecurePassword123!"))

            # Verify Group and Permission reconnection
            self.assertEqual(restored_user.groups.count(), 1)
            restored_group = restored_user.groups.first()
            self.assertEqual(restored_group.name, "Archive Maintainers")

            restored_mfr = Manufacturer.objects.get(name="Test Manufacturer")
            self.assertEqual(str(restored_mfr.uuid), original_mfr_uuid)

            restored_def = VehicleDefinition.objects.get(slug=self.vehicle_definition.slug)
            self.assertEqual(str(restored_def.uuid), original_def_uuid)

            restored_obs = Observation.objects.get(title="Synthetic Test Observation")
            self.assertEqual(str(restored_obs.uuid), original_obs_uuid)
            self.assertEqual(restored_obs.vehicle_definition, restored_def)
            self.assertEqual(restored_obs.recorded_by, restored_user)

            # Verify full_clean model validation
            restored_user.full_clean()
            restored_mfr.full_clean()
            restored_def.full_clean()
            restored_obs.full_clean()

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
