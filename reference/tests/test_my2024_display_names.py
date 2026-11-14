"""Bounded MY2024 JL display naming; no canonical writes or identity changes."""
from pathlib import Path
import csv

from django.test import SimpleTestCase

from reference.models import Manufacturer, VehicleModel, Generation, FactoryBodyConfiguration, VehicleDefinition


class My2024DisplayNameTests(SimpleTestCase):
    def vehicle(self, door='two-door', year=2024, make='Jeep', generation='JL'):
        maker = Manufacturer(pk=20, name=make, slug=make.lower())
        model = VehicleModel(pk=21, manufacturer=maker, name='Wrangler', slug='wrangler')
        gen = Generation(pk=32, vehicle_model=model, name=generation, slug=generation.lower(), start_year=2018)
        body = FactoryBodyConfiguration(pk=1, generation=gen, door_configuration=door)
        return VehicleDefinition(uuid=None, generation=gen, model_year=year, trim_name='Sport',
                                 engine_name='2.0L I4 Turbo', drivetrain='4WD', market='US',
                                 factory_body_configuration=body)

    def test_two_and_four_door_names_preserve_trim_and_slug(self):
        for door, expected in [('two-door', '2-Door'), ('four-door', '4-Door')]:
            with self.subTest(door=door):
                vehicle = self.vehicle(door)
                slug = vehicle.build_slug()
                self.assertIn('2024 Jeep Wrangler Sport ' + expected, str(vehicle))
                self.assertIn(vehicle.engine_description, str(vehicle))
                self.assertEqual(vehicle.trim_name, 'Sport')
                self.assertEqual(vehicle.build_slug(), slug)

    def test_designation_comes_from_body_not_trim(self):
        vehicle = self.vehicle('four-door')
        vehicle.trim_name = 'Rubicon'
        self.assertIn('Rubicon 4-Door', str(vehicle))
        vehicle.factory_body_configuration.door_configuration = None
        self.assertNotIn('Door', str(vehicle))

    def test_historical_and_unrelated_naming_unchanged(self):
        for values in ({'year':2023}, {'make':'Other'}, {'generation':'JK'}):
            with self.subTest(values=values):
                vehicle = self.vehicle(**values)
                expected = ' '.join([str(vehicle.model_year), str(vehicle.generation.vehicle_model),
                                     vehicle.trim_name, vehicle.engine_description,
                                     vehicle.get_drivetrain_display()])
                self.assertEqual(str(vehicle), expected)
        vehicle = self.vehicle();vehicle.factory_body_configuration = None
        self.assertNotIn('Door', str(vehicle))

    def test_all_approval_names_use_authoritative_model_naming(self):
        path = Path(__file__).resolve().parents[2] / 'docs/implementation/handoffs/RA056_wrangler_jl_my2024_approval/data/approval_matrix.csv'
        rows = list(csv.DictReader(path.open()))
        self.assertEqual(len(rows), 31)
        import json
        plans = json.loads((path.parents[2] / 'RA055_wrangler_jl_my2024_family_planning/data/planning_results.json').read_text())
        for row in rows:
            vehicle = self.vehicle({'2-Door':'two-door', '4-Door':'four-door'}[row['body_configuration']])
            vehicle.trim_name = row['canonical_trim']
            vehicle.engine_name = row['canonical_engine_name']
            # Reuse the exact plan's structured powertrain for the canonical label.
            for key, value in plans[row['candidate_identifier']]['body_plan']['target_fields']['canonical_powertrain'].items():
                setattr(vehicle, key, value)
            self.assertEqual(str(vehicle), row['public_display_name'])
