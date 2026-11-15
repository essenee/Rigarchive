from decimal import Decimal

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from reference.models import Engine, FactoryBodyConfiguration, Generation, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import _trim_body_groups, get_generation_hub_context


class VehicleMsrpTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Price Jeep')
        model = VehicleModel.objects.create(manufacturer=maker, name='Wrangler')
        cls.gen = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018)
        cls.engine = Engine.objects.create(manufacturer=maker, engine_code='ERC', name='3.6L V6',
            engine_displacement_liters=Decimal('3.6'), engine_cylinders=6,
            engine_aspiration='naturally_aspirated', fuel_type='gasoline', electrification_type='none')
        cls.bodies = [FactoryBodyConfiguration.objects.create(generation=cls.gen, door_configuration=d)
                      for d in ('two-door', 'four-door')]
        cls.user = get_user_model().objects.create_superuser(username='price-admin', password='test-password')

    def vehicle(self, **kwargs):
        return VehicleDefinition.objects.create(**(dict(generation=self.gen, model_year=2026,
            trim_name='Sport', engine=self.engine) | kwargs))

    def test_null_decimal_limits_and_negative_validation(self):
        row = self.vehicle()
        self.assertIsNone(row.base_msrp)
        for value in (Decimal('0'), Decimal('42345.67'), Decimal('99999999.99')):
            row.base_msrp = value
            row.full_clean()
            row.save()
            row.refresh_from_db()
            self.assertEqual(row.base_msrp, value)
        for value in (Decimal('-0.01'), Decimal('1.001'), Decimal('100000000.00')):
            row.base_msrp = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                row.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            VehicleDefinition.objects.filter(pk=row.pk).update(base_msrp=Decimal('-1'))

    def test_admin_edit_preserves_identity_and_records_history(self):
        row = self.vehicle()
        original = (row.pk, row.uuid, row.slug, row.engine_id, row.factory_body_configuration_id)
        self.client.force_login(self.user)
        url = reverse('admin:reference_vehicledefinition_change', args=[row.pk])
        response = self.client.get(url)
        form = response.context['adminform'].form
        self.assertIn('base_msrp', form.fields)
        self.assertNotIn('slug', form.fields)  # ADR-0002 remains in force.
        self.assertNotIn('uuid', form.fields)
        self.assertEqual(form.fields['base_msrp'].widget.input_type, 'number')
        data = dict(generation=self.gen.pk, engine=self.engine.pk, model_year=2026,
                    slug_correction=row.slug,
                    trim_name=row.trim_name, drivetrain=row.drivetrain, market=row.market,
                    base_msrp='42345.67', is_active='on', _save='Save')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.base_msrp, Decimal('42345.67'))
        self.assertEqual((row.pk, row.uuid, row.slug, row.engine_id, row.factory_body_configuration_id), original)
        log = LogEntry.objects.get(object_id=str(row.pk), action_flag=CHANGE)
        self.assertIn('base msrp', log.change_message.lower())
        response = self.client.post(url, data | {'base_msrp': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('base_msrp', response.context['adminform'].form.errors)
        row.refresh_from_db()
        self.assertEqual(row.base_msrp, Decimal('42345.67'))

    def test_admin_permission_required(self):
        row = self.vehicle()
        user = get_user_model().objects.create_user(username='unprivileged', is_staff=True)
        self.client.force_login(user)
        response = self.client.post(reverse('admin:reference_vehicledefinition_change', args=[row.pk]),
                                    {'base_msrp': '1'})
        self.assertEqual(response.status_code, 403)
        row.refresh_from_db()
        self.assertIsNone(row.base_msrp)

    def test_price_and_unrelated_edits_keep_generated_slug(self):
        row = self.vehicle()
        self.assertTrue(row.slug)
        identity = (row.pk, row.uuid, row.slug, row.engine_id)
        row.base_msrp = Decimal('45000.01')
        row.notes = 'Historical base price correction'
        row.save()
        row.refresh_from_db()
        self.assertEqual((row.pk, row.uuid, row.slug, row.engine_id), identity)

    def populate_groups(self):
        # Sport four-door is dearer than Willys, but its two-door/other-engine
        # minimum must keep both Sport groups before Willys.
        for i, (trim, body, price, engine) in enumerate([
            ('Sport', self.bodies[0], '30000', 'V6'),
            ('Sport', self.bodies[0], '28000', 'Turbo'),
            ('Sport', self.bodies[1], '50000', 'V6'),
            ('Willys', self.bodies[1], '35000', 'V6'),
            ('Alpha', self.bodies[0], '35000', 'V6'),
            ('Unknown', self.bodies[0], None, 'V6'),
            ('Zebra', self.bodies[0], None, 'V6'),
        ]):
            VehicleDefinition.objects.create(generation=self.gen, model_year=2026, trim_name=trim,
                factory_body_configuration=body, engine_name=engine, base_msrp=price, slug=f'price-{i}')
        self.vehicle(model_year=2025, trim_name='Earlier', base_msrp=Decimal('1'))
        self.vehicle(trim_name='Inactive', base_msrp=Decimal('1'), is_active=False)

    def test_trim_minimum_across_engines_and_bodies_and_filtering(self):
        self.populate_groups()
        context = get_generation_hub_context(self.gen, model_year='2026')
        groups = context['available_trim_groups']
        self.assertEqual([g['trim'] for g in groups], ['Sport', 'Sport', 'Alpha', 'Willys', 'Unknown', 'Zebra'])
        self.assertEqual([g['body'].door_configuration for g in groups[:2]], ['two-door', 'four-door'])
        self.assertEqual(sum(len(g['pks']) for g in groups), 7)
        for group in groups:
            selected = get_generation_hub_context(self.gen, model_year='2026', trim_name=group['key'])
            self.assertEqual({v.pk for v in selected['configuration_browser_choices']}, set(group['pks']))
        response = self.client.get(self.gen.get_absolute_url(), {'year': '2026'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([g['key'] for g in response.context['available_trim_groups']], [g['key'] for g in groups])

    def test_all_null_fallback_and_no_extra_queries(self):
        self.populate_groups()
        rows = list(VehicleDefinition.objects.filter(model_year=2026, is_active=True)
                    .select_related('factory_body_configuration'))
        for row in rows:
            row.base_msrp = None
        with self.assertNumQueries(0):
            groups = _trim_body_groups(rows)
        self.assertEqual([g['trim'] for g in groups], ['Alpha', 'Sport', 'Sport', 'Unknown', 'Willys', 'Zebra'])


class MsrpMigrationTests(TransactionTestCase):
    def test_existing_records_gain_null_without_identity_changes(self):
        before = [('reference', '0012_engine_registry')]
        after = [('reference', '0013_vehicledefinition_base_msrp')]
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            maker = apps.get_model('reference', 'Manufacturer').objects.create(name='Migration Maker', slug='migration-maker')
            model = apps.get_model('reference', 'VehicleModel').objects.create(manufacturer=maker, name='Model', slug='model')
            gen = apps.get_model('reference', 'Generation').objects.create(vehicle_model=model, name='Gen', slug='gen', start_year=2020)
            old = apps.get_model('reference', 'VehicleDefinition').objects.create(generation=gen,
                model_year=2026, trim_name='Base', slug='stored-slug')
            identity = (old.pk, old.uuid, old.slug, old.generation_id)
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            new = executor.loader.project_state(after).apps.get_model('reference', 'VehicleDefinition').objects.get(pk=old.pk)
            self.assertIsNone(new.base_msrp)
            self.assertEqual((new.pk, new.uuid, new.slug, new.generation_id), identity)
        finally:
            MigrationExecutor(connection).migrate(latest)
