"""Minimal RA-048 persistence; all records live in isolated test databases."""
from unittest.mock import patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from reference.models import FactoryBodyConfiguration as Body, Generation, Manufacturer, VehicleDefinition as Vehicle, VehicleModel


class FactoryBodyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name="Test Jeep")
        model = VehicleModel.objects.create(manufacturer=maker, name="Test Wrangler")
        cls.generation = Generation.objects.create(vehicle_model=model, name="Test JL", start_year=2018)
        cls.other = Generation.objects.create(vehicle_model=model, name="Other", start_year=2018)
        cls.two = Body.objects.create(generation=cls.generation, door_configuration="two-door")
        cls.four = Body.objects.create(generation=cls.generation, door_configuration="four-door")

    def vehicle(self, **kwargs):
        defaults = dict(generation=self.generation, model_year=2024, trim_name="Sport")
        defaults.update(kwargs)
        return Vehicle.objects.create(**defaults)

    def test_two_and_four_door_preserve_trim(self):
        a = self.vehicle(factory_body_configuration=self.two, slug="sport-2")
        b = self.vehicle(factory_body_configuration=self.four, slug="sport-4")
        self.assertEqual(a.trim_name, b.trim_name)
        self.assertNotEqual(a.factory_body_configuration_id, b.factory_body_configuration_id)

    def test_nullable_legacy_vehicle(self):
        self.assertIsNone(self.vehicle().factory_body_configuration)

    def test_reuse_across_trim_and_year(self):
        self.vehicle(factory_body_configuration=self.two)
        self.vehicle(factory_body_configuration=self.two, model_year=2023, trim_name="Rubicon")
        self.assertEqual(self.two.vehicle_definitions.count(), 2)

    def test_exact_duplicate_rejected(self):
        with self.assertRaises(ValidationError):
            Body.objects.create(generation=self.generation, door_configuration="two-door")

    def test_database_rejects_duplicate_with_null_dimensions(self):
        with self.assertRaises(IntegrityError), transaction.atomic(), patch.object(Body, "full_clean"):
            Body.objects.create(generation=self.generation, door_configuration="two-door")

    def test_sparse_tuples_not_merged(self):
        rich = Body.objects.create(generation=self.generation, door_configuration="two-door", body_style="suv")
        self.assertNotEqual(rich.pk, self.two.pk)

    def test_same_tuple_other_generation(self):
        self.assertIsNotNone(Body.objects.create(generation=self.other, door_configuration="two-door").pk)

    def test_empty_dimension_set_rejected(self):
        with self.assertRaises(ValidationError):
            Body.objects.create(generation=self.generation)

    def test_empty_strings_normalized(self):
        body = Body.objects.create(generation=self.generation, door_configuration="four-door", body_style=" ", roof_height_designation="high")
        self.assertIsNone(body.body_style)

    def test_namespace_requires_code(self):
        with self.assertRaises(ValidationError):
            Body.objects.create(generation=self.generation, body_code_namespace="jeep")

    def test_code_requires_namespace(self):
        with self.assertRaises(ValidationError):
            Body.objects.create(generation=self.generation, body_code="jl")

    def test_code_pair(self):
        self.assertIsNotNone(Body.objects.create(generation=self.generation, body_code="jl", body_code_namespace="jeep").pk)

    def test_noncanonical_or_measurement_values_rejected(self):
        for value in (True, 2, 2.4, "Two Door", "two-door\n"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Body.objects.create(generation=self.generation, door_configuration=value)

    def test_cross_generation_save_rejected(self):
        with self.assertRaises(ValidationError):
            self.vehicle(generation=self.other, factory_body_configuration=self.two)

    def test_cross_generation_clean_rejected(self):
        vehicle = Vehicle(generation=self.other, model_year=2024, factory_body_configuration=self.two)
        with self.assertRaises(ValidationError):
            vehicle.full_clean()

    def test_shared_generation_change_rejected(self):
        self.vehicle(factory_body_configuration=self.two)
        self.two.generation = self.other
        with self.assertRaises(ValidationError):
            self.two.save()

    def test_partial_vehicle_save_checks_persisted_pair(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        vehicle.generation = self.other
        vehicle.factory_body_configuration = None
        with self.assertRaises(ValidationError):
            vehicle.save(update_fields=["generation"])

    def test_correction_preserves_identity_and_provenance(self):
        vehicle = self.vehicle(factory_body_configuration=self.two, notes="Unlimited source label")
        before = (vehicle.pk, vehicle.uuid, vehicle.slug, vehicle.trim_name, vehicle.notes)
        vehicle.factory_body_configuration = self.four
        vehicle.save()
        vehicle.refresh_from_db()
        self.assertEqual(before, (vehicle.pk, vehicle.uuid, vehicle.slug, vehicle.trim_name, vehicle.notes))

    def test_referenced_body_deletion_protected(self):
        self.vehicle(factory_body_configuration=self.two)
        with self.assertRaises(ProtectedError):
            self.two.delete()

    def test_generation_deletion_protected(self):
        with self.assertRaises(ProtectedError):
            self.generation.delete()

    def test_bulk_body_edit_rejected(self):
        with self.assertRaises(ValidationError):
            Body.objects.filter(pk=self.two.pk).update(door_configuration="four-door")

    def test_bulk_vehicle_assignment_rejected(self):
        vehicle = self.vehicle()
        with self.assertRaises(ValidationError):
            Vehicle.objects.filter(pk=vehicle.pk).update(factory_body_configuration=self.two)

    def test_bulk_generation_change_rejected(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        with self.assertRaises(ValidationError):
            Vehicle.objects.filter(pk=vehicle.pk).update(generation=self.other)

    def test_bulk_upsert_cannot_change_generation_behind_existing_body(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        incoming = Vehicle(pk=vehicle.pk, generation=self.other, model_year=2024,
                           trim_name="Sport", slug=vehicle.slug)
        with self.assertRaises(ValidationError):
            Vehicle.objects.bulk_create([incoming], update_conflicts=True,
                                        update_fields=["generation"], unique_fields=["id"])
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.generation_id, self.generation.pk)

    def test_bulk_upsert_unrelated_fields_preserves_existing_body(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        incoming = Vehicle(pk=vehicle.pk, generation=self.generation, model_year=2024,
                           trim_name="Sport", slug=vehicle.slug, notes="Source retained")
        Vehicle.objects.bulk_create([incoming], update_conflicts=True,
                                    update_fields=iter(["notes"]), unique_fields=["id"])
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.notes, "Source retained")
        self.assertEqual(vehicle.factory_body_configuration_id, self.two.pk)

    def test_bulk_update_body_assignment_rejected(self):
        vehicle = self.vehicle()
        vehicle.factory_body_configuration = self.two
        with self.assertRaises(ValidationError):
            Vehicle.objects.bulk_update([vehicle], ["factory_body_configuration"])

    def test_bulk_update_generation_rejected(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        vehicle.generation = self.other
        with self.assertRaises(ValidationError):
            Vehicle.objects.bulk_update([vehicle], ["generation"])

    def test_partial_save_accepts_update_fields_iterator(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        vehicle.notes = "Retained source label"
        vehicle.save(update_fields=iter(["notes"]))
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.notes, "Retained source label")

    def test_shared_body_correction_is_allowed(self):
        vehicle = self.vehicle(factory_body_configuration=self.two)
        self.two.body_style = "suv"
        self.two.save()
        self.assertEqual(vehicle.factory_body_configuration.body_style, "suv")

    def admin_login(self):
        user = get_user_model().objects.create_superuser(username="body-admin", password="test-only")
        self.client.force_login(user)

    def test_admin_requires_permission(self):
        user = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:reference_factorybodyconfiguration_change", args=[self.two.pk])).status_code, 403)

    def test_admin_shared_warning_and_audited_correction(self):
        self.admin_login()
        self.vehicle(factory_body_configuration=self.two)
        url = reverse("admin:reference_factorybodyconfiguration_change", args=[self.two.pk])
        self.assertContains(self.client.get(url), "affects all 1 referencing VehicleDefinitions")
        response = self.client.post(url, {"generation": self.generation.pk, "door_configuration": "two-door", "body_style": "suv", "_save": "Save"})
        self.assertEqual(response.status_code, 302)
        self.two.refresh_from_db()
        self.assertEqual(self.two.body_style, "suv")
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.two.pk), action_flag=2).exists())

    def test_admin_body_scope_validation(self):
        self.admin_login()
        vehicle = self.vehicle(factory_body_configuration=self.two)
        url = reverse("admin:reference_vehicledefinition_change", args=[vehicle.pk])
        response = self.client.post(url, {"generation": self.other.pk, "factory_body_configuration": self.two.pk, "model_year": 2024, "trim_name": "Sport", "drivetrain": "UNK", "market": "US", "is_active": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Body configuration must belong")
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.generation_id, self.generation.pk)

    def test_admin_vehicle_fk_correction(self):
        self.admin_login()
        vehicle = self.vehicle(factory_body_configuration=self.two)
        original = (vehicle.uuid, vehicle.slug)
        response = self.client.post(reverse("admin:reference_vehicledefinition_change", args=[vehicle.pk]), {"generation": self.generation.pk, "factory_body_configuration": self.four.pk, "model_year": 2024, "trim_name": "Sport", "drivetrain": "UNK", "market": "US", "is_active": "on"})
        self.assertEqual(response.status_code, 302)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.factory_body_configuration_id, self.four.pk)
        self.assertEqual(original, (vehicle.uuid, vehicle.slug))


class FactoryBodyMigrationTests(TransactionTestCase):
    def test_additive_migration_preserves_all_existing_tables(self):
        self.assertNotEqual(str(connection.settings_dict["NAME"]), str(__import__("pathlib").Path.cwd() / "db.sqlite3"))
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old = [("reference", "0010_vehicledefinition_electrification_type_and_more")]
        try:
            executor.migrate(old)
            apps = executor.loader.project_state(old).apps
            maker = apps.get_model("reference", "Manufacturer").objects.create(name="Migration maker", slug="migration-maker")
            model = apps.get_model("reference", "VehicleModel").objects.create(manufacturer=maker, name="Model", slug="model")
            gen = apps.get_model("reference", "Generation").objects.create(vehicle_model=model, name="Gen", slug="gen", start_year=2020)
            vehicle = apps.get_model("reference", "VehicleDefinition").objects.create(generation=gen, model_year=2024, trim_name="Sport", slug="historical", notes="Unlimited preserved")
            snapshot = {}
            with connection.cursor() as cursor:
                for table in connection.introspection.table_names():
                    if table == "django_migrations":
                        continue
                    columns = [column.name for column in connection.introspection.get_table_description(cursor, table)]
                    quoted = ", ".join(connection.ops.quote_name(column) for column in columns)
                    cursor.execute(f'SELECT {quoted} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    snapshot[table] = (quoted, cursor.fetchall())
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            with connection.cursor() as cursor:
                for table, (quoted, rows) in snapshot.items():
                    cursor.execute(f'SELECT {quoted} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    self.assertEqual(cursor.fetchall(), rows, table)
            self.assertIsNone(Vehicle.objects.get(pk=vehicle.pk).factory_body_configuration_id)
            self.assertEqual(Body.objects.count(), 0)
        finally:
            MigrationExecutor(connection).migrate(latest)
