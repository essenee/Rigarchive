from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.test import TestCase

from reference.models import Generation, Manufacturer, VehicleModel
from measurements.models import (
    ApplicabilityFeature,
    ApplicabilityState,
    MeasurementDefinition,
    MeasurementResult,
    MeasurementResultCondition,
)


class MeasurementsModelTests(TestCase):
    def setUp(self):
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
            start_year=2003,
            end_year=2009,
        )

        self.def_opening_height = MeasurementDefinition.objects.create(
            name="Cargo Opening Height",
            category=MeasurementDefinition.Category.CARGO,
            description="Usable vertical height of rear cargo opening.",
        )
        self.def_behind_second_row = MeasurementDefinition.objects.create(
            name="Cargo Height Behind Second Row",
            category=MeasurementDefinition.Category.CARGO,
            description="Vertical interior height measured immediately behind second-row seating.",
        )
        self.def_max_interior_height = MeasurementDefinition.objects.create(
            name="Maximum Cargo Interior Height",
            category=MeasurementDefinition.Category.CARGO,
            description="Greatest usable vertical interior dimension within cargo area.",
        )

    def test_01_measurement_definition_identity_and_slug(self):
        self.assertIsInstance(self.def_opening_height.uuid, uuid.UUID)
        self.assertEqual(self.def_opening_height.slug, "cargo-opening-height")

    def test_02_measurement_definition_no_canonical_unit(self):
        self.assertFalse(hasattr(self.def_opening_height, "unit"))

    def test_03_measurement_result_references_generation(self):
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        self.assertEqual(result.generation, self.generation)

    def test_04_measurement_result_no_vehicle_definition_required(self):
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        self.assertFalse(hasattr(result, "vehicle_definition"))

    def test_05_generation_protected_deletion(self):
        MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        with self.assertRaises(models.ProtectedError):
            self.generation.delete()

    def test_06_measurement_result_stores_value_and_unit(self):
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_behind_second_row,
            value=Decimal("34.50"),
            unit=MeasurementResult.Unit.INCHES,
            notes="Measured at centerline",
        )
        self.assertEqual(result.value, Decimal("34.50"))
        self.assertEqual(result.unit, "in")
        self.assertEqual(result.notes, "Measured at centerline")

    def test_07_zero_conditions_is_generation_wide(self):
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        self.assertTrue(result.is_generation_wide)
        self.assertEqual(result.applicability_summary, "Generation-wide")

    def test_08_binary_feature_applicability(self):
        sunroof = ApplicabilityFeature.objects.create(
            name="Sunroof",
            description="Factory or option sunroof",
        )
        state_present = ApplicabilityState.objects.create(
            feature=sunroof,
            name="Present",
        )
        state_absent = ApplicabilityState.objects.create(
            feature=sunroof,
            name="Absent",
        )

        self.assertEqual(state_present.slug, "present")
        self.assertEqual(state_absent.slug, "absent")

        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_behind_second_row,
            value=Decimal("33.00"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(
            result=result,
            state=state_present,
        )

        self.assertFalse(result.is_generation_wide)
        self.assertEqual(result.applicability_summary, "Sunroof: Present")

    def test_09_non_binary_feature_applicability(self):
        floor = ApplicabilityFeature.objects.create(
            name="Cargo Floor Position",
            description="Adjustable cargo deck position",
        )
        state_upper = ApplicabilityState.objects.create(
            feature=floor,
            name="Upper Position",
        )
        state_lower = ApplicabilityState.objects.create(
            feature=floor,
            name="Lower Position",
        )

        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_max_interior_height,
            value=Decimal("36.00"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(
            result=result,
            state=state_lower,
        )

        self.assertFalse(result.is_generation_wide)
        self.assertEqual(result.applicability_summary, "Cargo Floor Position: Lower Position")

    def test_10_multiple_different_features_on_one_result(self):
        sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        state_sunroof_present = ApplicabilityState.objects.create(feature=sunroof, name="Present")

        floor = ApplicabilityFeature.objects.create(name="Cargo Floor Position")
        state_floor_lower = ApplicabilityState.objects.create(feature=floor, name="Lower Position")

        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_max_interior_height,
            value=Decimal("36.00"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(result=result, state=state_sunroof_present)
        MeasurementResultCondition.objects.create(result=result, state=state_floor_lower)

        self.assertFalse(result.is_generation_wide)
        self.assertIn("Sunroof: Present", result.applicability_summary)
        self.assertIn("Cargo Floor Position: Lower Position", result.applicability_summary)
        self.assertIn(" AND ", result.applicability_summary)

    def test_11_duplicate_state_attachment_rejected(self):
        sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        state_present = ApplicabilityState.objects.create(feature=sunroof, name="Present")

        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(result=result, state=state_present)

        with self.assertRaises((ValidationError, IntegrityError)):
            # Duplicate (result, state) attachment
            cond2 = MeasurementResultCondition(result=result, state=state_present)
            cond2.full_clean()
            cond2.save()

    def test_12_multiple_states_same_feature_rejected(self):
        sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        state_present = ApplicabilityState.objects.create(feature=sunroof, name="Present")
        state_absent = ApplicabilityState.objects.create(feature=sunroof, name="Absent")

        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_behind_second_row,
            value=Decimal("33.00"),
            unit=MeasurementResult.Unit.INCHES,
        )
        MeasurementResultCondition.objects.create(result=result, state=state_present)

        # Attempting to add a second state for the SAME feature (Sunroof) on the SAME result
        cond_conflicting = MeasurementResultCondition(result=result, state=state_absent)
        with self.assertRaises(ValidationError) as cm:
            cond_conflicting.full_clean()

        self.assertIn("A single MeasurementResult cannot contain multiple states of the same feature.", str(cm.exception))

    def test_13_multiple_results_same_generation_definition_applicability_coexist(self):
        # Multiple MeasurementResult records for the IDENTICAL Generation + Definition + applicability MUST coexist
        result_1 = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
            notes="Empirical measurement 1 by Contributor A",
        )
        result_2 = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.30"),
            unit=MeasurementResult.Unit.INCHES,
            notes="Empirical measurement 2 by Contributor B",
        )

        self.assertNotEqual(result_1.pk, result_2.pk)
        self.assertEqual(
            MeasurementResult.objects.filter(
                generation=self.generation,
                definition=self.def_opening_height,
            ).count(),
            2,
        )

    def test_14_provisional_cargo_height_definitions_taxonomy(self):
        self.assertEqual(
            MeasurementDefinition.objects.filter(category=MeasurementDefinition.Category.CARGO).count(),
            3,
        )

    def test_24_objects_create_domain_invariant_protection(self):
        """
        Verify that attempting to create a second condition for the same feature
        via ordinary ORM objects.create() raises ValidationError and is not persisted.
        """
        result = MeasurementResult.objects.create(
            generation=self.generation,
            definition=self.def_opening_height,
            value=Decimal("37.25"),
            unit=MeasurementResult.Unit.INCHES,
        )
        sunroof = ApplicabilityFeature.objects.create(name="Sunroof")
        state_present = ApplicabilityState.objects.create(feature=sunroof, name="Present")
        state_absent = ApplicabilityState.objects.create(feature=sunroof, name="Absent")

        # Step 4: Successfully create first condition via ordinary ORM creation
        cond1 = MeasurementResultCondition.objects.create(
            result=result,
            state=state_present,
        )
        self.assertIsNotNone(cond1.pk)

        # Step 5 & 6: Attempting to create second condition for the same feature raises ValidationError
        with self.assertRaises(ValidationError) as cm:
            MeasurementResultCondition.objects.create(
                result=result,
                state=state_absent,
            )

        self.assertIn("A single MeasurementResult cannot contain multiple states of the same feature.", str(cm.exception))
        self.assertEqual(MeasurementResultCondition.objects.filter(result=result).count(), 1)

    def test_25_measurement_definition_slug_immutability(self):
        """
        Verify that changing MeasurementDefinition name later does NOT change existing slug per ADR-0002.
        """
        def_test = MeasurementDefinition.objects.create(
            name="Cargo Floor Width",
            category=MeasurementDefinition.Category.CARGO,
        )
        original_slug = def_test.slug
        self.assertEqual(original_slug, "cargo-floor-width")

        def_test.name = "Modified Cargo Floor Width Name"
        def_test.save()

        def_test.refresh_from_db()
        self.assertEqual(def_test.name, "Modified Cargo Floor Width Name")
        self.assertEqual(def_test.slug, original_slug)

    def test_26_applicability_feature_slug_immutability(self):
        """
        Verify that changing ApplicabilityFeature name later does NOT change existing slug per ADR-0002.
        """
        feature = ApplicabilityFeature.objects.create(name="Roof Rack")
        original_slug = feature.slug
        self.assertEqual(original_slug, "roof-rack")

        feature.name = "Factory Roof Rack Option"
        feature.save()

        feature.refresh_from_db()
        self.assertEqual(feature.name, "Factory Roof Rack Option")
        self.assertEqual(feature.slug, original_slug)

    def test_27_applicability_state_slug_immutability(self):
        """
        Verify that changing ApplicabilityState name later does NOT change existing slug per ADR-0002.
        """
        feature = ApplicabilityFeature.objects.create(name="Roof Rack")
        state = ApplicabilityState.objects.create(feature=feature, name="Installed")
        original_slug = state.slug
        self.assertEqual(original_slug, "installed")

        state.name = "Factory Installed Roof Rails"
        state.save()

        state.refresh_from_db()
        self.assertEqual(state.name, "Factory Installed Roof Rails")
        self.assertEqual(state.slug, original_slug)

