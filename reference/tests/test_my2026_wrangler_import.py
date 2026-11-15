import io
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from reference import my2026_wrangler_import as importer
from reference.models import Engine, FactoryBodyConfiguration, Generation, ImportExecutionReceipt, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import get_generation_hub_context


class My2026WranglerImportTests(TestCase):
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
            engine = Engine.objects.create(manufacturer=cls.maker, engine_code=code, name=names[code],
                                           uuid=source['engine_profiles'][profile]['registered_engine_uuid'], **props)
            assert engine.pk == importer.EXPECTED_ENGINE_PKS[code]
        for year in range(2018, 2026):
            VehicleDefinition.objects.create(generation=cls.gen, model_year=year, trim_name='Historical',
                                            engine_name='3.6L V6', market='US', drivetrain='4WD')

    def publish(self, plan=None):
        with patch.object(importer, 'require_local_database'):
            return importer.execute((plan or importer.preview())['plan_hash'])

    def seed_original_family(self):
        """Isolated fixtures for the already-published 33 rows, never the live DB."""
        for row in importer.preview()['rows']:
            if row['fields']['trim_name'] != 'America250':
                vehicle = importer._vehicle(row, self.gen)
                vehicle.full_clean()
                vehicle.save()

    def test_incremental_preview_and_execution_preserve_original_33(self):
        self.seed_original_family()
        previous = list(VehicleDefinition.objects.order_by('pk').values())
        engines = list(Engine.objects.order_by('pk').values())
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 2, 'skip': 33, 'block': 0})
        creates = [r for r in plan['rows'] if r['action'] == 'create']
        self.assertEqual({r['fields']['trim_name'] for r in creates}, {'America250'})
        self.assertEqual({r['engine_code'] for r in creates}, {'ERC', 'EC1'})
        result = self.publish(plan)
        self.assertEqual((result['created'], result['skipped']), (2, 33))
        self.assertEqual(list(VehicleDefinition.objects.filter(pk__in=[r['id'] for r in previous])
                              .order_by('pk').values()), previous)
        self.assertEqual(list(Engine.objects.order_by('pk').values()), engines)
        self.assertEqual(importer.preview()['counts'], {'create': 0, 'skip': 35, 'block': 0})

    def test_supplement_receipts_distinguish_url_proof_from_owner_confirmation(self):
        self.seed_original_family()
        self.publish()
        receipts = ImportExecutionReceipt.objects.filter(execution_outcome='created')
        self.assertEqual(receipts.count(), 2)
        for receipt in receipts:
            self.assertEqual(receipt.source_id, 'jeep_my2026_owner_confirmed_builder')
            self.assertEqual(receipt.raw_artifact_reference, importer.SUPPLEMENT)
            self.assertEqual(receipt.raw_artifact_hash, 'sha256:' + importer.SUPPLEMENT_SHA)
            self.assertEqual(receipt.source_identity_type, 'owner_confirmed_configuration')
            row = receipt.resolution_snapshot_json['row']
            self.assertEqual(row['edmunds_style_ids'], [])
            self.assertIsNone(row['source_details']['transmission_pairing'])
            proof = row['source_details']['source_confirmation']
            self.assertEqual(proof['url_proves_this_engine'], row['engine_code'] == 'ERC')
            self.assertEqual(proof['supplied_url_demonstrates_engine_code'], 'ERC')
        old = ImportExecutionReceipt.objects.filter(execution_outcome='no_op_exact_match')
        self.assertEqual(old.count(), 33)
        self.assertEqual(set(old.values_list('source_id', flat=True)), {'edmunds_my2026_wrangler_builder'})
        self.assertEqual(set(old.values_list('raw_artifact_hash', flat=True)), {'sha256:' + importer.INVENTORY_SHA})

    def test_failure_on_last_supplement_receipt_rolls_back_creates_and_noops(self):
        self.seed_original_family()
        previous = list(VehicleDefinition.objects.order_by('pk').values())
        create = ImportExecutionReceipt.objects.create

        def fail(**kwargs):
            if kwargs['native_identifier'] == 'America250-four-door-EC1':
                raise RuntimeError('Supplement receipt failure')
            return create(**kwargs)

        with patch.object(ImportExecutionReceipt.objects, 'create', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'Supplement receipt failure'):
                self.publish()
        self.assertEqual(list(VehicleDefinition.objects.order_by('pk').values()), previous)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_unapproved_supplement_or_false_source_attribution_is_rejected(self):
        with patch.object(importer, 'SUPPLEMENT_SHA', '0' * 64):
            with self.assertRaisesRegex(ValidationError, 'supplement bytes changed'):
                importer.preview()
        source = json.loads((Path(settings.BASE_DIR) / importer.SUPPLEMENT).read_text())
        source['canonical_configurations'][1]['source_confirmation']['url_proves_this_engine'] = True
        with self.assertRaisesRegex(ValidationError, 'EC1 URL proof'):
            importer.validate_supplement(source)

    def test_america250_public_group_has_only_the_two_confirmed_engines(self):
        self.publish()
        context = get_generation_hub_context(self.gen, model_year=2026)
        self.assertEqual(len(context['available_trim_groups']), 19)
        group = next(g for g in context['available_trim_groups'] if g['trim'] == 'America250')
        self.assertEqual(group['label'], 'America250 · 4-Door')
        choices = get_generation_hub_context(self.gen, model_year=2026, trim_name=group['key'])['configuration_browser_choices']
        self.assertEqual({v.engine.engine_code for v in choices}, {'ERC', 'EC1'})
        response = self.client.get(self.gen.get_absolute_url(), {'year': 2026, 'trim': group['key']})
        for v in choices:
            self.assertEqual(v.trim_name, 'America250')
            self.assertEqual(v.factory_body_configuration.door_configuration, 'four-door')
            self.assertContains(response, v.get_absolute_url())
            self.assertNotIn(v.slug, v.choice_label)

    def test_preview_is_read_only_and_has_exactly_35_distinct_identities(self):
        before = (VehicleDefinition.objects.count(), ImportExecutionReceipt.objects.count(), Engine.objects.count())
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 35, 'skip': 0, 'block': 0})
        self.assertEqual(len({r['identity_digest'] for r in plan['rows']}), 35)
        self.assertEqual(len({r['fields']['slug'] for r in plan['rows']}), 35)
        self.assertEqual(before, (VehicleDefinition.objects.count(), ImportExecutionReceipt.objects.count(), Engine.objects.count()))
        self.assertEqual(plan, importer.preview())

    def test_registry_mapping_classification_and_unknown_provenance(self):
        self.publish()
        rows = VehicleDefinition.objects.filter(model_year=2026)
        self.assertEqual(rows.count(), 35)
        self.assertEqual(rows.filter(electrification_type='plug_in_hybrid').count(), 0)
        self.assertEqual(rows.filter(electrification_type='none').count(), 35)
        self.assertFalse(rows.filter(engine_aspiration__isnull=True).exists())
        self.assertEqual(Engine.objects.count(), 3)
        for code, expected in [('ERC', 16), ('EC1', 17), ('ESG', 2)]:
            self.assertEqual(rows.filter(engine_id=importer.EXPECTED_ENGINE_PKS[code],
                                         engine__engine_code=code).count(), expected)
        self.assertEqual(rows.filter(factory_body_configuration__door_configuration='two-door').count(), 10)
        self.assertEqual(rows.filter(factory_body_configuration__door_configuration='four-door').count(), 25)
        for receipt in ImportExecutionReceipt.objects.all():
            source = receipt.resolution_snapshot_json['row']['source_fields']
            self.assertEqual(source['manufacturer_engine_code'], receipt.created_vehicle_definition.engine.engine_code)
            profile = receipt.candidate_reference.split(':', 1)[1]
            self.assertEqual(receipt.created_vehicle_definition.engine.engine_code, importer.ENGINE_CODES[profile])
            self.assertEqual(source['engine_aspiration'], receipt.created_vehicle_definition.engine.engine_aspiration)
            if receipt.source_id == 'edmunds_my2026_wrangler_builder':
                self.assertIsNone(receipt.resolution_snapshot_json['row']['source_engine_code'])
            else:
                self.assertEqual(receipt.resolution_snapshot_json['row']['source_engine_code'], receipt.created_vehicle_definition.engine.engine_code)
            self.assertTrue(receipt.resolution_snapshot_json['source_urls'])

    def test_idempotent_rerun_and_preservation_of_all_existing_fields(self):
        historical = list(VehicleDefinition.objects.order_by('pk').values())
        self.publish()
        published = list(VehicleDefinition.objects.order_by('pk').values())
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 0, 'skip': 35, 'block': 0})
        result = self.publish(plan)
        self.assertEqual((result['created'], result['skipped']), (0, 35))
        self.assertEqual(list(VehicleDefinition.objects.order_by('pk').values()), published)
        self.assertEqual(list(VehicleDefinition.objects.filter(model_year__lt=2026).order_by('pk').values()), historical)
        self.assertEqual(ImportExecutionReceipt.objects.filter(execution_outcome='no_op_exact_match').count(), 35)

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
        self.assertFalse(VehicleDefinition.objects.filter(model_year=2026).exists())
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)
        self.assertEqual(VehicleDefinition.objects.count(), 8)

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
        engine = Engine.objects.get(engine_code='EC1')
        engine.electrification_type = 'plug_in_hybrid'
        engine.save()
        with self.assertRaisesRegex(ValidationError, 'contradicts registered'):
            importer.preview()

    def test_semantic_duplicate_under_another_slug_blocks_batch(self):
        self.publish()
        row = VehicleDefinition.objects.filter(model_year=2026).first()
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
        VehicleDefinition.objects.create(generation=self.gen, model_year=2026, trim_name='Other',
                                        slug=plan['rows'][0]['fields']['slug'])
        self.assertGreater(importer.preview()['counts']['block'], 0)

    def test_source_pin_prevents_silent_inventory_substitution(self):
        with patch.object(importer, 'INVENTORY_SHA', '0' * 64):
            with self.assertRaisesRegex(ValidationError, 'inventory bytes changed'):
                importer.preview()

    def test_rejects_wrong_existing_engine_pk_without_substitution(self):
        with patch.dict(importer.EXPECTED_ENGINE_PKS, {'ERC': 99}):
            with self.assertRaisesRegex(ValidationError, 'approved registry reference'):
                importer.preview()

    def test_inventory_consistency_rejects_extra_phev_or_unoffered_engine(self):
        source = json.loads((Path(settings.BASE_DIR) / importer.INVENTORY).read_text())
        source['canonical_configurations'][0]['engine_profile'] = 'phev_20_turbo'
        with self.assertRaisesRegex(ValidationError, 'observed style/engine offering'):
            importer.validate_inventory(source)

    def test_inventory_consistency_rejects_duplicate_style_and_mismatched_body(self):
        source = json.loads((Path(settings.BASE_DIR) / importer.INVENTORY).read_text())
        source['styles'].append(source['styles'][0])
        with self.assertRaisesRegex(ValidationError, '18 unique styles'):
            importer.validate_inventory(source)
        source = json.loads((Path(settings.BASE_DIR) / importer.INVENTORY).read_text())
        first = source['canonical_configurations'][0]['canonical_fields']
        second = source['canonical_configurations'][2]['canonical_fields']
        first['factory_body_configuration'], second['factory_body_configuration'] = (
            second['factory_body_configuration'], first['factory_body_configuration'])
        with self.assertRaisesRegex(ValidationError, 'observed style/engine offering'):
            importer.validate_inventory(source)

    def test_namespace_change_invalidates_exact_preview(self):
        plan = importer.preview()
        VehicleDefinition.objects.create(generation=self.gen, model_year=2026,
                                        trim_name='Unrelated new peer', slug='new-peer')
        with self.assertRaisesRegex(ValidationError, 'Stale or unapproved'):
            self.publish(plan)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_public_grouping_filtering_labels_and_specs_links(self):
        self.publish()
        context = get_generation_hub_context(self.gen, model_year=2026)
        groups = [g for g in context['available_trim_groups'] if g['trim'] == 'Willys']
        self.assertEqual({g['label'] for g in groups}, {'Willys · 2-Door', 'Willys · 4-Door'})
        for group in groups:
            selected = get_generation_hub_context(self.gen, model_year=2026, trim_name=group['key'])
            choices = selected['configuration_browser_choices']
            self.assertEqual(len(choices), 2)
            self.assertEqual({v.factory_body_configuration_id for v in choices}, {group['body'].pk})
            response = self.client.get(self.gen.get_absolute_url(), {'year': 2026, 'trim': group['key']})
            self.assertEqual(response.status_code, 200)
            for v in choices:
                self.assertNotIn(v.slug, v.choice_label)
                self.assertNotIn('US', v.choice_label)
                self.assertIn(group['body'].door_configuration.split('-')[0] == 'two' and '2-Door' or '4-Door', str(v))
                self.assertContains(response, v.get_absolute_url())

    def test_command_defaults_to_preview_and_requires_explicit_digest(self):
        output = io.StringIO()
        call_command('import_my2026_wrangler', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['counts']['create'], 35)
        with self.assertRaises(CommandError):
            call_command('import_my2026_wrangler', execute=True, stdout=io.StringIO())
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    @override_settings(DEBUG=False)
    def test_execution_rejects_nonlocal_or_production_settings(self):
        with self.assertRaisesRegex(ValidationError, 'local desktop'):
            importer.execute(importer.preview()['plan_hash'])

    def test_hidden_rhd_remains_canonical_and_rerun_preserves_visibility(self):
        self.publish()
        row = VehicleDefinition.objects.get(model_year=2026, trim_name='Sport RHD')
        original = (row.pk, row.uuid, row.slug, row.engine_id, row.base_msrp)
        row.is_public = False
        row.save()
        plan = importer.preview()
        self.assertEqual(plan['counts'], {'create': 0, 'skip': 35, 'block': 0})
        self.publish(plan)
        row.refresh_from_db()
        self.assertFalse(row.is_public)
        self.assertTrue(row.is_active)
        self.assertEqual((row.pk, row.uuid, row.slug, row.engine_id, row.base_msrp), original)
        self.assertEqual(VehicleDefinition.objects.filter(model_year=2026).count(), 35)
        self.assertEqual(VehicleDefinition.objects.publicly_visible().filter(model_year=2026).count(), 34)
        self.assertEqual(self.client.get(row.get_absolute_url()).status_code, 404)
