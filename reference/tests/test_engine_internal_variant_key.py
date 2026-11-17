"""Bounded Engine identity evolution; all records/databases here are isolated."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, close_old_connections, connection, transaction
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, SimpleTestCase, TransactionTestCase, RequestFactory
from django.urls import reverse

from reference.engine_registry import resolve_engine, prepare_registered_vehicle, EngineRegistryError
from reference.models import Engine, Manufacturer, VehicleModel, Generation, VehicleDefinition, normalize_internal_variant_key
from reference.powertrain import record_powertrain
from reference.my2025_wrangler_import import snapshot, digest, HISTORICAL_SNAPSHOT_FIELDS

PT = dict(engine_displacement_liters='2', engine_cylinders=4, engine_aspiration='turbocharged',
          fuel_type='gasoline', electrification_type='none')


class VariantNormalizationTests(SimpleTestCase):
    def test_exact_normalization(self):
        for value, expected in [('', ''), ('  REVIEWED_Key--1  ', 'reviewed_key--1'), ('a'*100, 'a'*100), ('_-', '_-')]:
            self.assertEqual(normalize_internal_variant_key(value), expected)
        for value in [None, True, False, 1, 'ſ', 'K', 'é', 'a b', 'a\nb', 'a.b', 'a/b', 'a'*101]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalize_internal_variant_key(value)


class EngineVariantTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = Manufacturer.objects.create(name='Variant maker')
        cls.engine = Engine.objects.create(manufacturer=cls.maker, engine_code='CODE', name='Shared name', **PT)
        model = VehicleModel.objects.create(manufacturer=cls.maker, name='Model')
        cls.generation = Generation.objects.create(vehicle_model=model, name='Generation', start_year=2020)

    def variant(self, key='reviewed'):
        return Engine.objects.create(manufacturer=self.maker, engine_code=' code ',
                                     internal_variant_key=key, name='Shared name', **PT)

    def test_composite_identity_and_explicit_empty(self):
        other = self.variant(' REVIEWED ')
        self.assertEqual(other.internal_variant_key, 'reviewed')
        self.assertEqual(resolve_engine(self.maker, 'code', internal_variant_key=''), self.engine)
        self.assertEqual(resolve_engine(self.maker, 'code', internal_variant_key=' REVIEWED '), other)
        for key in ['', ' REVIEWED ']:
            with self.assertRaises(ValidationError): self.variant(key)
        with self.assertRaises(EngineRegistryError) as error:
            resolve_engine(self.maker, 'code', incoming_powertrain=PT)
        self.assertEqual(error.exception.code, 'ENGINE_REGISTRY_AMBIGUOUS')
        for key in ['missing', None]:
            with self.assertRaises(ValidationError): resolve_engine(self.maker, 'code', internal_variant_key=key)
        self.assertEqual(Engine.objects.count(), 2)

    def test_omitted_unique_missing_and_no_registration(self):
        self.assertEqual(resolve_engine(self.maker, 'CODE'), self.engine)
        with self.assertRaises(EngineRegistryError): resolve_engine(self.maker, 'MISSING')
        self.assertEqual(Engine.objects.count(), 1)

    def test_exact_pin_and_identity_conflicts(self):
        other = self.variant()
        self.assertEqual(resolve_engine(self.maker, 'CODE', engine_pk=other.pk, engine_uuid=other.uuid), other)
        self.assertEqual(resolve_engine(self.maker, 'CODE', engine_uuid=other.uuid), other)
        for kwargs in [dict(engine_pk=other.pk, engine_uuid=self.engine.uuid),
                       dict(engine_pk=other.pk, internal_variant_key=''),
                       dict(engine_pk=99999), dict(engine_pk=other.pk, incoming_powertrain={'fuel_type':'diesel'})]:
            with self.assertRaises(ValidationError): resolve_engine(self.maker, 'CODE', **kwargs)
        with self.assertRaises(ValidationError): resolve_engine(self.maker, 'WRONG', engine_pk=other.pk)
        maker = Manufacturer.objects.create(name='Other maker')
        with self.assertRaises(ValidationError): resolve_engine(maker, 'CODE', engine_pk=other.pk)

    def test_both_incoming_claim_paths_and_vehicle_identity(self):
        other = self.variant()
        original = str(other)
        vehicle = prepare_registered_vehicle(self.maker, 'CODE', engine_pk=other.pk,
            generation=self.generation, model_year=2024, trim_name='Trim', engine_name='2.0L I4 Historical name')
        vehicle.save()
        identity = (vehicle.pk, vehicle.uuid, vehicle.slug, vehicle.engine_name)
        self.assertEqual(vehicle.engine_id, other.pk)
        self.assertNotIn('[reviewed]', str(other))
        self.assertEqual(str(other), original)
        for inputs in [dict(incoming_powertrain={'fuel_type':'diesel'}, fuel_type='gasoline'),
                       dict(incoming_powertrain=PT, fuel_type='diesel')]:
            with self.assertRaises(ValidationError):
                prepare_registered_vehicle(self.maker, 'CODE', engine_pk=other.pk,
                    generation=self.generation, model_year=2024, trim_name='Other', **inputs)
        vehicle.refresh_from_db()
        self.assertEqual((vehicle.pk, vehicle.uuid, vehicle.slug, vehicle.engine_name), identity)

    def test_all_variant_identity_changes_forbidden(self):
        other = self.variant()
        for engine, value in [(self.engine, 'reviewed'), (other, ''), (other, 'renamed')]:
            fresh = Engine.objects.get(pk=engine.pk)
            fresh.internal_variant_key = value
            with self.assertRaises(ValidationError): fresh.save()
        with self.assertRaises(ValidationError): Engine.objects.filter(pk=other.pk).update(internal_variant_key='other')

    def test_storage_constraints_without_model_save(self):
        for key in ['BAD', ' leading', 'trailing ', 'a b', 'a.b', 'a\x00b', 'é', 'a'*101, None, '']:
            with self.subTest(key=key), self.assertRaises(IntegrityError), transaction.atomic():
                engine = Engine(manufacturer=self.maker, engine_code='CODE', internal_variant_key=key,
                                name='Raw', **PT)
                engine.save_base(raw=True)
        self.variant('a'*100)

    def test_authorization_projection_does_not_enumerate_future_fields(self):
        self.engine.refresh_from_db()
        expected = snapshot(self.engine)
        self.assertEqual(list(expected), list(HISTORICAL_SNAPSHOT_FIELDS['engine']))
        with patch.object(Engine._meta, 'concrete_fields', [*Engine._meta.concrete_fields, SimpleNamespace(attname='future_horsepower')]):
            self.engine.future_horsepower = 999
            self.assertEqual(snapshot(self.engine), expected)
        self.assertEqual(expected['engine_displacement_liters'], '2.00')
        self.assertNotIn('internal_variant_key', expected)
        from reference.engine_assignment import canonical_state
        self.assertEqual(canonical_state()['engines'][0]['internal_variant_key'], '')
        with self.assertRaises(ValidationError): snapshot(self.variant())

    def test_legacy_binding_retains_exact_reference_and_rejects_new_semantics(self):
        from reference.ingestion.importing.registry_body_import import engine_binding
        binding = engine_binding(self.engine)
        other = self.variant()
        self.assertEqual(engine_binding(resolve_engine(self.maker, 'CODE', engine_pk=self.engine.pk,
                         engine_uuid=self.engine.uuid)), binding)
        with self.assertRaises(ValidationError): engine_binding(other)

    def test_reconciliation_never_uses_partial_properties_to_choose_shared_code(self):
        from reference.engine_reconciliation import preview_engine_assignments
        other = self.variant()
        other.fuel_type = 'diesel'; other.save()
        vehicle = VehicleDefinition.objects.create(generation=self.generation, model_year=2024,
            trim_name='Unlinked', engine_name='Shared name', fuel_type='gasoline')
        row = next(r for r in preview_engine_assignments()['rows'] if r['pk'] == vehicle.pk)
        self.assertEqual(row['status'], 'AMBIGUOUS')
        self.assertIsNone(row['proposed_engine'])

    def test_admin_creation_readonly_search_and_autocomplete_permissions(self):
        model_admin = admin.site._registry[Engine]
        user = get_user_model().objects.create_superuser(username='variant-admin', email='', password='test')
        request = RequestFactory().get('/admin/'); request.user = user
        self.assertIn('internal_variant_key', model_admin.get_form(request).base_fields)
        self.assertNotIn('internal_variant_key', model_admin.get_form(request, self.engine).base_fields)
        self.assertIn('internal_variant_key', model_admin.list_display)
        self.assertIn('internal_variant_key', model_admin.search_fields)
        other = self.variant()
        found, _ = model_admin.get_search_results(request, Engine.objects.all(), 'reviewed')
        self.assertEqual(list(found), [other])
        url = reverse('admin:reference_engine_variant_autocomplete')
        query = dict(app_label='reference', model_name='vehicledefinition', field_name='engine', term='CODE')
        self.assertNotEqual(self.client.get(url, query).status_code, 200)
        self.client.force_login(user)
        response = self.client.get(url, query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(url, dict(app_label='reference', model_name='engine',
                        field_name='manufacturer', term='maker')).status_code, 403)
        results = response.json()['results']
        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0]['text'], results[1]['text'])
        self.assertTrue(any('[reviewed]' in row['text'] for row in results))
        form = admin.site._registry[VehicleDefinition].get_form(request)()
        self.assertIn(url, form.fields['engine'].widget.widget.get_url())


class HistoricalAuthorizationTests(SimpleTestCase):
    def test_all_six_historical_preimages_and_full_model_projections(self):
        root = Path(__file__).resolve().parents[2]
        cases = [
            (2025, 'local_import_preview', '3d07c967c782390f23d26865e49b0c20a34ca75dcc245c25afd15cdfec20581d'),
            (2025, 'local_import_rerun_preview', '937149ab096f185f772c5cb881afc9fbc27606466203a98e8a48aeaf6e0d96bb'),
            (2026, 'local_import_preview', '14cc91a525060048b2e6aa37b7781b0e7f13b8c226b84d5f46225a47a209930a'),
            (2026, 'local_import_rerun_preview', '1b94462b38a49ded4d90e39b5b0ef4cd92d97b67538fb6dc68ed6ac95cd834e6'),
            (2026, 'america250_incremental_preview', 'd8312f5bd6aab0cd2d0e95913fb39427b9781cfae7cd4c161c7dda0d85e28c72'),
            (2026, 'america250_rerun_preview', 'c97b51032ab1de8ff50b3841f247c790ff35f79cd4746bdc5039e83fa4aebfca'),
        ]
        for year, name, expected in cases:
            with self.subTest(year=year, name=name):
                value = json.loads((root/f'docs/research/MY{year}_JL_edmunds_builder_20261114/{name}_20261114.json').read_text())
                self.assertEqual(value.pop('plan_hash'), 'sha256:'+expected)
                groups = [('parents', model, row) for model, row in zip(['manufacturer','vehiclemodel','generation'], value['parents'])]
                groups += [('engines','engine',row) for row in value['engines'].values()]
                groups += [('bodies','factorybodyconfiguration',row) for row in value['bodies'].values()]
                groups += [('namespace','vehicledefinition',row) for row in value['namespace']]
                for _, model, row in groups:
                    self.assertEqual(set(row), set(HISTORICAL_SNAPSHOT_FIELDS[model]))
                    # Actual historical value spellings, plus a simulated future field.
                    obj = SimpleNamespace(**row, future_torque=999, _meta=SimpleNamespace(model_name=model))
                    self.assertEqual(snapshot(obj), row)
                self.assertEqual(digest(value), 'sha256:'+expected)


class VariantMigrationTests(TransactionTestCase):
    def test_forward_preservation_and_fail_closed_reverse(self):
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        old = [('reference', '0014_vehicledefinition_is_public')]
        try:
            executor = MigrationExecutor(connection); executor.migrate(old)
            apps = executor.loader.project_state(old).apps
            Maker = apps.get_model('reference','Manufacturer'); OldEngine = apps.get_model('reference','Engine')
            maker = Maker.objects.create(name='Migration maker', slug='migration-maker')
            engine = OldEngine.objects.create(manufacturer=maker, engine_code='CODE', name='Before', **PT)
            Model=apps.get_model('reference','VehicleModel'); Gen=apps.get_model('reference','Generation'); Vehicle=apps.get_model('reference','VehicleDefinition')
            model=Model.objects.create(manufacturer=maker,name='Model',slug='model')
            gen=Gen.objects.create(vehicle_model=model,name='Generation',slug='gen',start_year=2020)
            Vehicle.objects.create(generation=gen,engine=engine,model_year=2024,trim_name='Trim',slug='preserved')
            with connection.cursor() as cursor:
                cursor.execute('select * from reference_engine'); before=cursor.fetchall()
                cursor.execute('select * from reference_vehicledefinition'); vehicles=cursor.fetchall()
            MigrationExecutor(connection).migrate(latest)
            with connection.cursor() as cursor:
                cursor.execute('select '+','.join(f.column for f in OldEngine._meta.concrete_fields)+' from reference_engine')
                self.assertEqual(cursor.fetchall(), before)
                cursor.execute('select * from reference_vehicledefinition'); self.assertEqual(cursor.fetchall(), vehicles)
            current = Engine.objects.get(pk=engine.pk); self.assertEqual(current.internal_variant_key, '')
            variant=Engine.objects.create(manufacturer_id=maker.pk,engine_code='CODE',internal_variant_key='reviewed',name='After',**PT)
            with self.assertRaises(IrreversibleError): MigrationExecutor(connection).migrate(old)
            self.assertTrue(Engine.objects.filter(pk=variant.pk,internal_variant_key='reviewed').exists())
            # A failed reverse can already have removed later migrations. Use
            # the actual 0015 state, not today's model with future audit relations.
            historical_engine = MigrationExecutor(connection).loader.project_state(
                [('reference', '0015_engine_internal_variant_key')]
            ).apps.get_model('reference', 'Engine')
            historical_engine.objects.get(pk=variant.pk).delete()
            MigrationExecutor(connection).migrate(old)
            self.assertEqual(MigrationExecutor(connection).loader.project_state(old).apps.get_model('reference','Engine').objects.count(), 1)
        finally:
            MigrationExecutor(connection).migrate(latest)

    def test_concurrent_duplicate_creation(self):
        maker = Manufacturer.objects.create(name='Concurrent maker')
        from threading import Barrier
        barrier = Barrier(2)
        def create():
            close_old_connections(); barrier.wait(timeout=10)
            try:
                Engine.objects.create(manufacturer_id=maker.pk,engine_code='SAME',internal_variant_key='reviewed',name='Concurrent',**PT)
                return 'created'
            except (ValidationError, IntegrityError, OperationalError):
                # SQLite can reject a simultaneous writer with a lock rather than a
                # uniqueness error. Neither failure may produce a duplicate.
                return 'rejected'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:create(),range(2)))
        self.assertLessEqual(results.count('created'), 1)
        # If SQLite rejected both upgrades, an ordinary save must still work.
        if not Engine.objects.filter(manufacturer=maker).exists():
            Engine.objects.create(manufacturer=maker,engine_code='SAME',internal_variant_key='reviewed',name='Retry',**PT)
        self.assertEqual(Engine.objects.filter(manufacturer=maker,engine_code='SAME').count(), 1)
