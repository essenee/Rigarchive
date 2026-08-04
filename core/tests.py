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
