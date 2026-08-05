import datetime
import uuid

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from observation.models import Observation
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel

User = get_user_model()


class ObservationModelTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="testadmin",
            email="admin@example.com",
            password="password123",
            is_staff=True,
            is_superuser=True,
        )

        self.manufacturer = Manufacturer.objects.create(
            name="Toyota",
            country_code="JP",
        )

        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="4Runner",
        )

        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Fourth Generation",
            generation_number=4,
            start_year=2003,
            end_year=2009,
        )

        self.vehicle_definition = VehicleDefinition.objects.create(
            generation=self.fourth_generation if hasattr(self, "fourth_generation") else self.generation,
            model_year=2007,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain=VehicleDefinition.Drivetrain.FOUR_WHEEL_DRIVE,
            market=VehicleDefinition.Market.UNITED_STATES,
        )

    def test_observation_creation_and_string_representation(self) -> None:
        obs = Observation.objects.create(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Front Sway Bar Diameter",
            description="Verified 30mm diameter front sway bar on 2007 SR5 V6.",
            observed_on=datetime.date(2026, 8, 4),
            source_notes="Physical inspection note.",
        )

        self.assertEqual(str(obs), "Front Sway Bar Diameter")
        self.assertIsInstance(obs.id, int)
        self.assertIsInstance(obs.uuid, uuid.UUID)
        self.assertIsNotNone(obs.created_at)
        self.assertIsNotNone(obs.updated_at)

    def test_model_validation_requires_title_and_description(self) -> None:
        # Blank title fails full_clean()
        invalid_title_obs = Observation(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="",
            description="Valid description.",
        )
        with self.assertRaises(ValidationError):
            invalid_title_obs.full_clean()

        # Blank description fails full_clean()
        invalid_desc_obs = Observation(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Valid Title",
            description="",
        )
        with self.assertRaises(ValidationError):
            invalid_desc_obs.full_clean()

    def test_optional_fields_accept_null_or_blank(self) -> None:
        obs = Observation(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Valid Title",
            description="Valid description.",
            observed_on=None,
            source_notes="",
        )
        obs.full_clean()
        obs.save()

        self.assertIsNone(obs.observed_on)
        self.assertEqual(obs.source_notes, "")

    def test_protected_deletion_of_vehicle_definition(self) -> None:
        Observation.objects.create(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Protected Relation Test",
            description="Testing PROTECT deletion.",
        )

        with self.assertRaises(ProtectedError):
            self.vehicle_definition.delete()

    def test_protected_deletion_of_user(self) -> None:
        Observation.objects.create(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Protected User Test",
            description="Testing PROTECT deletion on user.",
        )

        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_non_mutation_of_vehicle_definition(self) -> None:
        original_trim = self.vehicle_definition.trim_name
        original_notes = self.vehicle_definition.notes
        original_updated_at = self.vehicle_definition.updated_at

        # Create Observation
        obs = Observation.objects.create(
            vehicle_definition=self.vehicle_definition,
            recorded_by=self.user,
            title="Non Mutation Test",
            description="Ensuring VehicleDefinition is untouched.",
        )

        self.vehicle_definition.refresh_from_db()
        self.assertEqual(self.vehicle_definition.trim_name, original_trim)
        self.assertEqual(self.vehicle_definition.notes, original_notes)
        self.assertEqual(self.vehicle_definition.updated_at, original_updated_at)

        # Edit Observation
        obs.description = "Updated observation description."
        obs.save()

        self.vehicle_definition.refresh_from_db()
        self.assertEqual(self.vehicle_definition.trim_name, original_trim)
        self.assertEqual(self.vehicle_definition.notes, original_notes)
        self.assertEqual(self.vehicle_definition.updated_at, original_updated_at)

        # Delete Observation
        obs.delete()

        self.vehicle_definition.refresh_from_db()
        self.assertEqual(self.vehicle_definition.trim_name, original_trim)
        self.assertEqual(self.vehicle_definition.notes, original_notes)
        self.assertEqual(self.vehicle_definition.updated_at, original_updated_at)


class ObservationAdminTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="superuser",
            email="super@example.com",
            password="superpassword123",
        )

        self.manufacturer = Manufacturer.objects.create(
            name="Ford",
            country_code="US",
        )
        self.vehicle_model = VehicleModel.objects.create(
            manufacturer=self.manufacturer,
            name="Transit",
        )
        self.generation = Generation.objects.create(
            vehicle_model=self.vehicle_model,
            name="Fourth Generation",
            start_year=2014,
        )
        self.vehicle_definition = VehicleDefinition.objects.create(
            generation=self.generation,
            model_year=2020,
            trim_name="Cargo",
        )

    def test_observation_is_registered_with_admin(self) -> None:
        self.assertTrue(admin.site.is_registered(Observation))

    def test_superuser_accesses_admin_changelist_and_add(self) -> None:
        self.client.login(username="superuser", password="superpassword123")

        changelist_url = reverse("admin:observation_observation_changelist")
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        add_url = reverse("admin:observation_observation_add")
        add_response = self.client.get(add_url)
        self.assertEqual(add_response.status_code, 200)

    def test_unauthenticated_user_redirected_to_admin_login(self) -> None:
        changelist_url = reverse("admin:observation_observation_changelist")
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
