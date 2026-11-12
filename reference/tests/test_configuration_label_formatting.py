"""Tests for redundant turbocharger presentation formatting in configuration labels.

Covers:
- Removal of redundant standalone 'Turbo' from configuration choices when aspiration is 'Turbocharged'
- Clean formatting of '3.0L V6 Turbo Diesel' into '3.0L V6 · Turbocharged · Diesel · 4WD'
- Preservation of electrification designations on 4xe PHEV configurations without duplicate turbo
- Invariance of 3.6L ESS, 3.6L eTorque (MHEV), and 6.4L HEMI configurations
- Preservation of meaningful descriptors when aspiration is not separately displayed
- Preservation of canonical database fields and stored engine names
"""
from django.test import SimpleTestCase, TestCase
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel
from reference.powertrain import engine_label
from reference.services import _label_configuration_choices


class ConfigurationLabelFormattingTests(SimpleTestCase):
    """Presentation formatting tests using in-memory model instances without database persistence."""

    def test_turbo_redundancy_removal_in_configuration_choices(self):
        """2.0L I4 Turbo · Turbocharged · 4WD becomes 2.0L I4 · Turbocharged · 4WD."""
        record = VehicleDefinition(
            model_year=2022,
            trim_name="Sport",
            engine_name="2.0L I4 Turbo",
            engine_aspiration="turbocharged",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
        )
        labeled = _label_configuration_choices([record])
        self.assertEqual(labeled[0].choice_label, "2.0L I4 · Turbocharged · 4WD")

    def test_turbo_diesel_formatting_in_configuration_choices(self):
        """3.0L V6 Turbo Diesel · Turbocharged · Diesel · 4WD becomes 3.0L V6 · Turbocharged · Diesel · 4WD."""
        record = VehicleDefinition(
            model_year=2022,
            trim_name="Unlimited Sport",
            engine_name="3.0L V6 Turbo Diesel",
            engine_aspiration="turbocharged",
            fuel_type="diesel",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
        )
        labeled = _label_configuration_choices([record])
        self.assertEqual(labeled[0].choice_label, "3.0L V6 · Turbocharged · Diesel · 4WD")

    def test_4xe_phev_retains_electrification_without_duplicate_turbo(self):
        """4xe PHEV labels retain their electrification designation while avoiding duplicate turbo terminology."""
        record = VehicleDefinition(
            model_year=2022,
            trim_name="Unlimited Rubicon 4xe",
            engine_name="2.0L I4 Turbo PHEV",
            engine_aspiration="turbocharged",
            fuel_type="gasoline",
            electrification_type="plug_in_hybrid",
            drivetrain="4WD",
            market="US",
        )
        labeled = _label_configuration_choices([record])
        self.assertEqual(labeled[0].choice_label, "2.0L I4 · Turbocharged · PHEV · 4WD")

        # Long form engine description
        self.assertEqual(record.engine_description, "2.0L I4, Turbocharged, Plug-in hybrid (PHEV)")

    def test_existing_36l_ess_and_etorque_remain_unchanged(self):
        """Existing 3.6L ESS, eTorque, and HEMI labels remain unchanged."""
        ess = VehicleDefinition(
            model_year=2022,
            trim_name="Sport",
            engine_name="3.6L V6 ESS",
            engine_aspiration="naturally_aspirated",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
        )
        etorque = VehicleDefinition(
            model_year=2022,
            trim_name="Sport",
            engine_name="3.6L V6 eTorque",
            engine_aspiration="naturally_aspirated",
            fuel_type="gasoline",
            electrification_type="mild_hybrid",
            drivetrain="4WD",
            market="US",
        )
        hemi = VehicleDefinition(
            model_year=2022,
            trim_name="Unlimited Rubicon 392",
            engine_name="6.4L V8 HEMI",
            engine_aspiration="naturally_aspirated",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
        )
        self.assertEqual(_label_configuration_choices([ess])[0].choice_label, "3.6L V6 ESS · 4WD")
        self.assertEqual(_label_configuration_choices([etorque])[0].choice_label, "3.6L V6 eTorque · MHEV · 4WD")
        self.assertEqual(_label_configuration_choices([hemi])[0].choice_label, "6.4L V8 HEMI · 4WD")

    def test_labels_without_separate_aspiration_are_not_stripped(self):
        """Labels without a separate aspiration designation are not accidentally stripped of meaningful information."""
        i4_turbo = VehicleDefinition(
            model_year=2025,
            trim_name="SR5",
            engine_name="2.4L Turbo I4",
            engine_aspiration=None,
            fuel_type=None,
            electrification_type=None,
            drivetrain="4WD",
            market="US",
        )
        hybrid_turbo = VehicleDefinition(
            model_year=2025,
            trim_name="TRD Pro",
            engine_name="2.4L Turbo Hybrid I4",
            engine_aspiration=None,
            fuel_type=None,
            electrification_type=None,
            drivetrain="4WD",
            market="US",
        )
        self.assertEqual(_label_configuration_choices([i4_turbo])[0].choice_label, "2.4L Turbo I4 · 4WD")
        self.assertEqual(_label_configuration_choices([hybrid_turbo])[0].choice_label, "2.4L Turbo Hybrid I4 · 4WD")
        self.assertEqual(engine_label(i4_turbo), "2.4L Turbo I4")
        self.assertEqual(engine_label(hybrid_turbo), "2.4L Turbo Hybrid I4")

    def test_trim_and_model_names_containing_turbo_not_corrupted(self):
        """Model, trim, and package names containing 'Turbo' are never corrupted."""
        record = VehicleDefinition(
            model_year=2022,
            trim_name="Turbo S",
            engine_name="3.8L Flat-6 TwinTurbo",
            engine_aspiration="turbocharged",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="AWD",
            market="US",
        )
        # Even with trim varying or not, trim name remains Turbo S
        self.assertEqual(record.trim_name, "Turbo S")
        # TwinTurbo is not standalone Turbo, so it is preserved
        self.assertEqual(engine_label(record, short=True), "3.8L Flat-6 TwinTurbo · Turbocharged")

    def test_naturally_aspirated_not_added_to_labels(self):
        """Naturally Aspirated is not added to labels that omit it."""
        record = VehicleDefinition(
            model_year=2022,
            trim_name="Sport",
            engine_name="3.6L V6 ESS",
            engine_aspiration="naturally_aspirated",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
        )
        self.assertNotIn("Naturally Aspirated", engine_label(record, short=True))
        self.assertNotIn("Naturally aspirated", engine_label(record, short=True))
        self.assertNotIn("Naturally Aspirated", engine_label(record, short=False))
        self.assertNotIn("Naturally aspirated", engine_label(record, short=False))


class DatabaseIntegrityAndRegressionTests(TestCase):
    """Verify that stored database records remain unmodified and format cleanly in real queries."""

    @classmethod
    def setUpTestData(cls):
        mfg = Manufacturer.objects.create(name="Jeep", slug="jeep")
        model = VehicleModel.objects.create(manufacturer=mfg, name="Wrangler", slug="wrangler")
        gen = Generation.objects.create(vehicle_model=model, name="JL", slug="jl", start_year=2018)
        cls.turbo_gas = VehicleDefinition.objects.create(
            generation=gen,
            model_year=2022,
            trim_name="Sport",
            engine_name="2.0L I4 Turbo",
            engine_aspiration="turbocharged",
            fuel_type="gasoline",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
            slug="2022-sport-20l-i4-turbo-4wd-us",
        )
        cls.turbo_diesel = VehicleDefinition.objects.create(
            generation=gen,
            model_year=2022,
            trim_name="Unlimited Sport",
            engine_name="3.0L V6 Turbo Diesel",
            engine_aspiration="turbocharged",
            fuel_type="diesel",
            electrification_type="none",
            drivetrain="4WD",
            market="US",
            slug="2022-unlimited-sport-30l-v6-turbo-diesel-4wd-us",
        )
        cls.turbo_phev = VehicleDefinition.objects.create(
            generation=gen,
            model_year=2022,
            trim_name="Unlimited Rubicon 4xe",
            engine_name="2.0L I4 Turbo PHEV",
            engine_aspiration="turbocharged",
            fuel_type="gasoline",
            electrification_type="plug_in_hybrid",
            drivetrain="4WD",
            market="US",
            slug="2022-unlimited-rubicon-4xe-20l-i4-turbo-phev-4wd-us",
        )

    def test_canonical_engine_names_in_database_remain_unchanged(self):
        """Canonical engine names and database values remain strictly unchanged."""
        # Query fresh from DB
        gas_record = VehicleDefinition.objects.get(pk=self.turbo_gas.pk)
        diesel_record = VehicleDefinition.objects.get(pk=self.turbo_diesel.pk)
        phev_record = VehicleDefinition.objects.get(pk=self.turbo_phev.pk)

        # Database values remain untouched
        self.assertEqual(gas_record.engine_name, "2.0L I4 Turbo")
        self.assertEqual(diesel_record.engine_name, "3.0L V6 Turbo Diesel")
        self.assertEqual(phev_record.engine_name, "2.0L I4 Turbo PHEV")

        # When formatted through choice labeling, redundant words are removed in presentation only
        labeled_gas = _label_configuration_choices([gas_record])
        self.assertEqual(labeled_gas[0].choice_label, "2.0L I4 · Turbocharged · 4WD")
        self.assertEqual(labeled_gas[0].engine_name, "2.0L I4 Turbo")

        labeled_diesel = _label_configuration_choices([diesel_record])
        self.assertEqual(labeled_diesel[0].choice_label, "3.0L V6 · Turbocharged · Diesel · 4WD")
        self.assertEqual(labeled_diesel[0].engine_name, "3.0L V6 Turbo Diesel")

        labeled_phev = _label_configuration_choices([phev_record])
        self.assertEqual(labeled_phev[0].choice_label, "2.0L I4 · Turbocharged · PHEV · 4WD")
        self.assertEqual(labeled_phev[0].engine_name, "2.0L I4 Turbo PHEV")
