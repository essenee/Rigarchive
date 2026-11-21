import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from reference.body_identity import authoring_configuration_key, authoring_body_dimensions
from reference.models import (
    Manufacturer, VehicleModel, Generation, Engine, VehicleDefinition,
    FactoryBodyConfiguration as Body, NominalBedLength, ImportExecutionReceipt,
)
from reference.powertrain import record_powertrain
from reference.services import get_generation_hub_context
from reference.vehicle_authoring import author_configurations


class PickupAuthoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = Manufacturer.objects.create(name='Generic Truck Maker')
        model = VehicleModel.objects.create(manufacturer=cls.maker, name='Pickup')
        cls.gen = Generation.objects.create(vehicle_model=model, name='Current', start_year=2024)
        cls.bodies = []
        for cab, door, bed in [('xtracab', 'two-door', '6-ft'),
                               ('double-cab', 'four-door', '5-ft'), ('double-cab', 'four-door', '6-ft')]:
            length, _ = NominalBedLength.objects.get_or_create(designation=bed)
            cls.bodies.append(Body.objects.create(generation=cls.gen, cab_configuration=cab,
                                                  door_configuration=door, bed_length=length))
        pt = dict(engine_displacement_liters='2.4', engine_cylinders=4,
                  engine_aspiration='turbocharged', fuel_type='gasoline', electrification_type='none')
        cls.engine = Engine.objects.create(manufacturer=cls.maker, engine_code='TEST',
            internal_variant_key='auto-output', name='2.4L 4-Cyl. Turbo', **pt)
        cls.manual = Engine.objects.create(manufacturer=cls.maker, engine_code='TEST',
            internal_variant_key='manual-output', name='2.4L 4-Cyl. Turbo', **pt)

    def proposal(self, body=None, **kw):
        fields = dict(generation=self.gen, model_year=2026, trim_name='Sport', drivetrain='4WD',
                      market='US', factory_body_configuration=body or self.bodies[1],
                      engine=self.engine, engine_name=self.engine.name, **record_powertrain(self.engine))
        fields.update(kw)
        return VehicleDefinition(**fields)

    def run_authoring(self, rows, options=None, corrupt=False):
        observations = []
        for row, _ in rows:
            engines = options or [self.engine]
            observations.append({'identity': authoring_configuration_key(row),
                'engine_name': row.engine_name, 'base_msrp': str(row.base_msrp) if row.base_msrp else None,
                'engine_options': [{'pk': e.pk, 'uuid': str(e.uuid), 'engine_code': e.engine_code,
                    'internal_variant_key': e.internal_variant_key, 'name': e.name,
                    'powertrain': record_powertrain(e)} for e in engines]})
        raw = json.dumps({'record_type': 'human-reviewed-factory-observations',
                          'configurations': observations}).encode()
        with TemporaryDirectory() as tmp, override_settings(BASE_DIR=Path(tmp)):
            Path(tmp, 'observations.json').write_bytes(raw)
            return author_configurations(rows, evidence_reference='observations.json',
                evidence_hash='sha256:' + ('0' * 64 if corrupt else hashlib.sha256(raw).hexdigest()),
                authorization='Test owner approves only these exact rows', operator_label='test-owner')

    def test_distinct_beds_have_readable_deterministic_slugs_and_complete_identity(self):
        rows = [self.proposal(body=b) for b in self.bodies]
        self.assertEqual(len({authoring_configuration_key(v) for v in rows}), 3)
        self.assertEqual(len({v.build_slug() for v in rows}), 3)
        for row in rows:
            self.assertIn(row.factory_body_configuration.bed_length.designation + '-bed', row.build_slug())
        self.assertIn('xtracab-6-ft-bed', rows[0].build_slug())
        self.assertIn('double-cab-5-ft-bed', rows[1].build_slug())
        self.assertEqual(rows[0].build_slug(), self.proposal(self.bodies[0]).build_slug())

    def test_existing_slugs_and_nonpickup_generation_are_unchanged(self):
        old = self.proposal(slug='historical-url')
        old.save(); old.notes = 'Ordinary edit'; old.save()
        self.assertEqual(old.slug, 'historical-url')
        row = self.proposal(factory_body_configuration=None, engine=None, engine_name='2.4L I4')
        self.assertEqual(row.build_slug(), '2026-sport-24l-i4-4wd-us-turbo')

    def test_atomic_import_and_compact_provenance(self):
        results = self.run_authoring([(self.proposal(b), None) for b in self.bodies])
        self.assertEqual(VehicleDefinition.objects.count(), 3)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 3)
        for vehicle, receipt in results:
            self.assertEqual(receipt.created_vehicle_definition, vehicle)
            snapshot = receipt.resolution_snapshot_json
            self.assertEqual(snapshot['profile'], 'human-body-authoring/1')
            self.assertEqual(snapshot['identity']['body'], authoring_body_dimensions(vehicle.factory_body_configuration))
            self.assertIn('Test owner', snapshot['authorization'])
            self.assertEqual(snapshot['engine_uuid'], str(self.engine.uuid))

    def test_implicit_body_authoring_is_generation_specific_and_prevents_duplicates(self):
        model = VehicleModel.objects.create(manufacturer=self.maker, name="Implicit body fixture")
        generation = Generation.objects.create(vehicle_model=model, name="Current", start_year=2025,
                                               uuid="9b0d045b-75c1-49de-addf-c33c781b25a8")
        vehicle, receipt = self.run_authoring([
            (self.proposal(generation=generation, factory_body_configuration=None), None),
        ])[0]
        self.assertIsNone(vehicle.factory_body_configuration_id)
        self.assertIsNone(receipt.resolution_snapshot_json["identity"]["body"])
        with self.assertRaisesMessage(ValidationError, "overlaps"):
            self.run_authoring([(self.proposal(generation=generation, factory_body_configuration=None), None)])
        with self.assertRaisesMessage(ValidationError, "requires a reviewed body parent"):
            self.run_authoring([(self.proposal(factory_body_configuration=None), None)])
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 1)

    def test_reuse_only_activates_exact_record_and_keeps_timestamp_slug_uuid(self):
        old = self.proposal(is_active=False, slug='old-url'); old.save()
        before = VehicleDefinition.objects.filter(pk=old.pk).values().get()
        self.run_authoring([(self.proposal(), old.pk)])
        after = VehicleDefinition.objects.filter(pk=old.pk).values().get()
        self.assertEqual(after, before | {'is_active': True})

    def test_ambiguous_inactive_legacy_remains_unchanged(self):
        old = VehicleDefinition.objects.create(generation=self.gen, model_year=2026, trim_name='Sport',
            drivetrain='4WD', engine_name='2.4L I4', is_active=False)
        before = VehicleDefinition.objects.filter(pk=old.pk).values().get()
        self.run_authoring([(self.proposal(), None)])
        self.assertEqual(VehicleDefinition.objects.filter(pk=old.pk).values().get(), before)

    def test_active_legacy_overlap_and_duplicate_rows_are_rejected(self):
        old = VehicleDefinition.objects.create(generation=self.gen, model_year=2026, trim_name='Sport',
            drivetrain='4WD', engine_name='2.4L I4')
        with self.assertRaisesMessage(ValidationError, 'overlaps'):
            self.run_authoring([(self.proposal(), None)])
        old.is_active = False; old.save(update_fields=['is_active'])
        with self.assertRaises(ValidationError):
            self.run_authoring([(self.proposal(), None), (self.proposal(), None)])
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_transmission_output_alternatives_do_not_split_identity_or_force_fk(self):
        row = self.proposal(engine=None)
        alternate = self.proposal(engine=self.manual)
        self.assertEqual(authoring_configuration_key(row), authoring_configuration_key(alternate))
        vehicle, receipt = self.run_authoring([(row, None)], options=[self.engine, self.manual])[0]
        self.assertIsNone(vehicle.engine_id)
        self.assertEqual(len(receipt.resolution_snapshot_json['observation']['engine_options']), 2)
        with self.assertRaisesMessage(ValidationError, 'forced'):
            self.run_authoring([(self.proposal(), None)], options=[self.engine, self.manual])

    def test_stale_evidence_or_engine_options_roll_back(self):
        with self.assertRaisesMessage(ValidationError, 'changed'):
            self.run_authoring([(self.proposal(), None)], corrupt=True)
        with patch.object(ImportExecutionReceipt, 'save', side_effect=ValidationError('receipt failure')):
            with self.assertRaisesMessage(ValidationError, 'receipt failure'):
                self.run_authoring([(self.proposal(), None)])
        self.assertFalse(VehicleDefinition.objects.exists())
        self.assertFalse(ImportExecutionReceipt.objects.exists())

    def test_reuse_cannot_fill_missing_legacy_identity(self):
        old = VehicleDefinition.objects.create(generation=self.gen, model_year=2026, trim_name='Sport',
            drivetrain='4WD', engine_name='2.4L I4', is_active=False)
        with self.assertRaises(ValidationError):
            self.run_authoring([(self.proposal(), old.pk)])
        old.refresh_from_db(); self.assertFalse(old.is_active)

    def test_configurator_names_and_deep_links_distinguish_both_double_cab_beds(self):
        results = self.run_authoring([(self.proposal(b), None) for b in self.bodies])
        context = get_generation_hub_context(self.gen, model_year='2026')
        groups = context['available_trim_groups']
        self.assertEqual({g['label'] for g in groups}, {
            'Sport · XtraCab · 6-ft Bed', 'Sport · Double Cab · 5-ft Bed', 'Sport · Double Cab · 6-ft Bed'})
        for group in groups:
            selected = get_generation_hub_context(self.gen, model_year='2026', trim_name=group['key'])
            self.assertEqual({v.factory_body_configuration_id for v in selected['configuration_browser_choices']},
                             {group['body'].pk})
        for vehicle, _ in results:
            selected = get_generation_hub_context(self.gen, config_slug=vehicle.slug)
            self.assertEqual(selected['selected_config'].pk, vehicle.pk)
            self.assertEqual(self.client.get(vehicle.get_absolute_url()).status_code, 200)
