import io
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from reference import my2025_wrangler_import as importer
from reference.models import Engine, FactoryBodyConfiguration, Generation, ImportExecutionReceipt, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import get_generation_hub_context


class My2025WranglerImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = Manufacturer.objects.create(name='Jeep')
        model = VehicleModel.objects.create(manufacturer=cls.maker, name='Wrangler')
        cls.gen = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018)
        for door in ('two-door', 'four-door'):
            FactoryBodyConfiguration.objects.create(generation=cls.gen, door_configuration=door)
        source = json.loads((Path(settings.BASE_DIR) / importer.INVENTORY).read_text())
        names = {'ERC': '3.6L V6 ESS', 'EC1': '2.0L I4 Turbo',
                 'ESG': '6.4L V8 HEMI', 'ECX': '2.0L I4 Turbo PHEV'}
        for profile, code in importer.ENGINE_CODES.items():
            props = {k: source['engine_profiles'][profile][k] for k in importer.FIELDS}
            if props['engine_aspiration'] is None:
                props['engine_aspiration'] = 'naturally_aspirated'
            Engine.objects.create(manufacturer=cls.maker, engine_code=code, name=names[code], **props)
        for year in range(2018, 2025):
            VehicleDefinition.objects.create(generation=cls.gen, model_year=year, trim_name='Historical',
                                            engine_name='3.6L V6', market='US', drivetrain='4WD')

    def publish(self, plan=None):
        with patch.object(importer, 'require_local_database'):
            return importer.execute((plan or importer.preview())['plan_hash'])

    def test_preview_is_read_only_and_has_exactly_31_distinct_identities(self):
        before = (VehicleDefinition.objects.count(), ImportExecutionReceipt.objects.count(), Engine.objects.count())
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 31, 'skip': 0, 'block': 0})
        self.assertEqual(len({r['identity_digest'] for r in plan['rows']}), 31)
        self.assertEqual(len({r['fields']['slug'] for r in plan['rows']}), 31)
        self.assertEqual(before, (VehicleDefinition.objects.count(), ImportExecutionReceipt.objects.count(), Engine.objects.count()))
        self.assertEqual(plan, importer.preview())

    def test_registry_mapping_classification_and_unknown_provenance(self):
        self.publish()
        rows = VehicleDefinition.objects.filter(model_year=2025)
        self.assertEqual(rows.count(), 31)
        self.assertEqual(rows.filter(electrification_type='plug_in_hybrid').count(), 7)
        self.assertEqual(rows.filter(electrification_type='none').count(), 24)
        self.assertFalse(rows.filter(engine_aspiration__isnull=True).exists())
        self.assertEqual(Engine.objects.count(), 4)
        for receipt in ImportExecutionReceipt.objects.all():
            source = receipt.resolution_snapshot_json['row']['source_fields']
            self.assertIsNone(source['manufacturer_engine_code'])
            profile = receipt.candidate_reference.split(':', 1)[1]
            self.assertEqual(receipt.created_vehicle_definition.engine.engine_code, importer.ENGINE_CODES[profile])
            if profile in ('gas_36_v6', 'gas_64_v8'):
                self.assertIsNone(source['engine_aspiration'])
            self.assertTrue(receipt.resolution_snapshot_json['source_urls'])

    def test_idempotent_rerun_and_preservation_of_all_existing_fields(self):
        historical = list(VehicleDefinition.objects.order_by('pk').values())
        self.publish()
        published = list(VehicleDefinition.objects.order_by('pk').values())
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 0, 'skip': 31, 'block': 0})
        result = self.publish(plan)
        self.assertEqual((result['created'], result['skipped']), (0, 31))
        self.assertEqual(list(VehicleDefinition.objects.order_by('pk').values()), published)
        self.assertEqual(list(VehicleDefinition.objects.filter(model_year__lt=2025).order_by('pk').values()), historical)
        self.assertEqual(ImportExecutionReceipt.objects.filter(execution_outcome='no_op_exact_match').count(), 31)

    def test_receipt_failure_rolls_back_entire_family(self):
        real_create = ImportExecutionReceipt.objects.create
        calls = 0

        def fail(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RuntimeError('Audit storage failure')
            return real_create(**kwargs)

        with patch.object(ImportExecutionReceipt.objects, 'create', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'Audit storage failure'):
                self.publish()
        self.assertFalse(VehicleDefinition.objects.filter(model_year=2025).exists())
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)
        self.assertEqual(VehicleDefinition.objects.count(), 7)

    def test_stale_registry_change_rejects_execution(self):
        plan = importer.preview()
        engine = Engine.objects.get(engine_code='ERC')
        engine.name = '3.6L V6 Updated'
        engine.save()
        with self.assertRaisesRegex(ValidationError, 'Stale or unapproved'):
            self.publish(plan)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_missing_engine_fails_closed(self):
        Engine.objects.get(engine_code='ERC').delete()
        with self.assertRaisesRegex(ValidationError, 'missing or duplicated'):
            importer.preview()

    def test_conflicting_registry_properties_fail_closed(self):
        engine = Engine.objects.get(engine_code='ECX')
        engine.electrification_type = 'none'
        engine.save()
        with self.assertRaisesRegex(ValidationError, 'contradicts registered'):
            importer.preview()

    def test_semantic_duplicate_under_another_slug_blocks_batch(self):
        self.publish()
        row = VehicleDefinition.objects.filter(model_year=2025).first()
        row.pk = None
        import uuid
        row.uuid = uuid.uuid4()
        row.slug += '-duplicate'
        row.save()
        plan = importer.preview()
        self.assertGreater(plan['counts']['block'], 0)
        with self.assertRaisesRegex(ValidationError, 'Blocked rows'):
            self.publish(plan)

    def test_slug_occupancy_blocks_instead_of_suffix_repair(self):
        plan = importer.preview()
        VehicleDefinition.objects.create(generation=self.gen, model_year=2025, trim_name='Other',
                                        slug=plan['rows'][0]['fields']['slug'])
        self.assertGreater(importer.preview()['counts']['block'], 0)

    def test_source_pin_prevents_silent_inventory_substitution(self):
        with patch.object(importer, 'INVENTORY_SHA', '0' * 64):
            with self.assertRaisesRegex(ValidationError, 'inventory bytes changed'):
                importer.preview()

    def test_public_grouping_filtering_labels_and_specs_links(self):
        self.publish()
        context = get_generation_hub_context(self.gen, model_year=2025)
        groups = [g for g in context['available_trim_groups'] if g['trim'] == 'Willys']
        self.assertEqual({g['label'] for g in groups}, {'Willys · 2-Door', 'Willys · 4-Door'})
        for group in groups:
            selected = get_generation_hub_context(self.gen, model_year=2025, trim_name=group['key'])
            choices = selected['configuration_browser_choices']
            self.assertEqual(len(choices), 2)
            self.assertEqual({v.factory_body_configuration_id for v in choices}, {group['body'].pk})
            response = self.client.get(self.gen.get_absolute_url(), {'year': 2025, 'trim': group['key']})
            self.assertEqual(response.status_code, 200)
            for v in choices:
                self.assertNotIn(v.slug, v.choice_label)
                self.assertNotIn('US', v.choice_label)
                self.assertIn(group['body'].door_configuration.split('-')[0] == 'two' and '2-Door' or '4-Door', str(v))
                self.assertContains(response, v.get_absolute_url())

    def test_command_defaults_to_preview_and_requires_explicit_digest(self):
        output = io.StringIO()
        call_command('import_my2025_wrangler', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['counts']['create'], 31)
        with self.assertRaises(CommandError):
            call_command('import_my2025_wrangler', execute=True, stdout=io.StringIO())
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    @override_settings(DEBUG=False)
    def test_execution_rejects_nonlocal_or_production_settings(self):
        with self.assertRaisesRegex(ValidationError, 'local desktop'):
            importer.execute(importer.preview()['plan_hash'])
