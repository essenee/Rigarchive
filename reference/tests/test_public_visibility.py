from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import Http404
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition, FactoryBodyConfiguration, Engine
from reference.services import (get_generation_hub_context, get_full_specifications_context,
    get_homepage_context, get_vehicle_context, discover_vehicle_models, discover_manufacturers)


class PublicVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Visibility Maker')
        cls.model = VehicleModel.objects.create(manufacturer=maker, name='Vehicle')
        cls.gen = Generation.objects.create(vehicle_model=cls.model, name='Generation', start_year=2020)
        cls.body = FactoryBodyConfiguration.objects.create(generation=cls.gen, door_configuration='four-door')
        cls.engine = Engine.objects.create(manufacturer=maker, engine_code='EC1', name='2.0L I4 Turbo',
            engine_displacement_liters=Decimal('2.0'),engine_cylinders=4,engine_aspiration='turbocharged',
            fuel_type='gasoline',electrification_type='none')
        cls.visible = VehicleDefinition.objects.create(generation=cls.gen, model_year=2025, trim_name='Sport',
            engine=cls.engine, factory_body_configuration=cls.body, base_msrp=Decimal('40000'))
        cls.hidden = VehicleDefinition.objects.create(generation=cls.gen, model_year=2025, trim_name='Special',
            engine_name='Unique engine', drivetrain='AWD', is_public=False)
        cls.user = get_user_model().objects.create_superuser(username='visibility-admin',password='test-password')

    def test_defaults_and_internal_manager_independence(self):
        self.assertTrue(self.visible.is_public)
        self.assertTrue(self.hidden.is_active)
        self.assertEqual(VehicleDefinition.objects.count(),2)
        self.assertEqual(list(VehicleDefinition.objects.publicly_visible()),[self.visible])
        self.assertEqual(set(self.gen.vehicle_definitions.all()),{self.visible,self.hidden})
        self.visible.is_active=False
        self.visible.save()
        self.assertTrue(self.visible.is_public)
        self.assertFalse(VehicleDefinition.objects.publicly_visible().exists())

    def test_all_ancestor_states(self):
        for obj in (self.gen,self.model,self.model.manufacturer):
            obj.is_active=False;obj.save()
            self.assertFalse(VehicleDefinition.objects.publicly_visible().exists())
            obj.is_active=True;obj.save()

    def test_hidden_specs_and_context_unavailable_even_to_staff(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code,404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code,404)
        self.assertEqual(self.client.get(self.visible.get_absolute_url()).status_code,200)
        for helper in (get_vehicle_context,get_full_specifications_context):
            with self.assertRaises(Http404):helper(self.hidden)
        self.assertEqual(list(get_full_specifications_context(self.visible)['sibling_configs']),[])

    def test_hub_groups_counts_hidden_exact_and_empty_generation(self):
        c=get_generation_hub_context(self.gen,model_year='2025')
        self.assertEqual(c['stats']['configurations_count'],1)
        self.assertEqual(c['stats']['engine_options_count'],1)
        self.assertEqual([g['trim'] for g in c['available_trim_groups']],['Sport'])
        self.assertEqual([v.pk for v in c['configuration_browser_choices']],[self.visible.pk])
        c=get_generation_hub_context(self.gen,config_slug=self.hidden.slug)
        self.assertIsNone(c['selected_config'])
        self.assertTrue(c['filter_errors'])
        self.visible.is_public=False;self.visible.save()
        c=get_generation_hub_context(self.gen,model_year='2025')
        self.assertEqual(c['available_trim_groups'],[])
        self.assertEqual(c['active_model_years'],[])
        self.assertEqual(c['stats']['configurations_count'],0)
        self.assertEqual(self.client.get(self.gen.get_absolute_url()).status_code,200)
        self.assertEqual(self.client.get(self.model.get_absolute_url()).status_code,200)
        year_url=reverse('reference:model-year-overview',kwargs=dict(manufacturer_slug=self.model.manufacturer.slug,
            vehicle_model_slug=self.model.slug,generation_slug=self.gen.slug,model_year=2025))
        self.assertEqual(self.client.get(year_url).status_code,404)

    def test_public_coverage_never_combines_different_rows(self):
        self.visible.is_active=False;self.visible.save()  # public but inactive; other row active but hidden
        self.assertEqual(list(discover_vehicle_models(populated_only=True)),[])
        self.assertEqual(list(discover_manufacturers(populated_only=True)),[])
        self.assertEqual(list(discover_vehicle_models()),[self.model])
        self.assertEqual(get_homepage_context()['featured_platforms'],[])
        response=self.client.get(self.model.manufacturer.get_absolute_url())
        self.assertEqual(list(response.context['vehicle_models']),[])
        selector=self.client.get(reverse('reference:vehicle-selector'),{'q':'Vehicle'})
        self.assertContains(selector,self.model.get_absolute_url())

    def test_homepage_count_and_year_summary_are_public_only(self):
        old=VehicleDefinition.objects.create(generation=self.gen,model_year=2020,trim_name='Older',is_public=False)
        card=get_homepage_context()['featured_platforms'][0]
        self.assertEqual(card['configs_count'],1)
        self.assertEqual(card['generations_count'],1)
        self.assertEqual(get_generation_hub_context(self.gen)['active_model_years'],[2025])

    def test_hidden_price_cannot_determine_trim_order(self):
        self.hidden.trim_name='Sport';self.hidden.base_msrp=Decimal('1');self.hidden.save()
        VehicleDefinition.objects.create(generation=self.gen,model_year=2025,trim_name='Middle',base_msrp=Decimal('30000'))
        groups=get_generation_hub_context(self.gen,model_year='2025')['available_trim_groups']
        self.assertEqual([g['trim'] for g in groups],['Middle','Sport'])

    def test_admin_visibility_change_audit_and_identity_preservation(self):
        row=self.visible
        before=(row.pk,row.uuid,row.slug,row.engine_id,row.factory_body_configuration_id,row.base_msrp,row.is_active)
        self.client.force_login(self.user)
        url=reverse('admin:reference_vehicledefinition_change',args=[row.pk])
        form=self.client.get(url).context['adminform'].form
        self.assertEqual(form.fields['is_public'].label,'Visible on public site')
        data=dict(generation=self.gen.pk,engine=self.engine.pk,factory_body_configuration=self.body.pk,
            model_year=row.model_year,trim_name=row.trim_name,drivetrain=row.drivetrain,market=row.market,
            base_msrp='40000',is_active='on',slug_correction=row.slug,_save='Save')
        self.assertEqual(self.client.post(url,data).status_code,302)
        row.refresh_from_db();self.assertFalse(row.is_public)
        self.assertEqual((row.pk,row.uuid,row.slug,row.engine_id,row.factory_body_configuration_id,row.base_msrp,row.is_active),before)
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertIn('Visible on public site',LogEntry.objects.get(object_id=str(row.pk)).change_message)
        self.assertEqual(self.client.get(row.get_absolute_url()).status_code,404)
        self.assertEqual(self.client.post(url,data|{'is_public':'on'}).status_code,302)
        self.assertEqual(self.client.get(row.get_absolute_url()).status_code,200)

    def test_unauthorized_visibility_change_rejected(self):
        user=get_user_model().objects.create_user(username='no-visibility',is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse('admin:reference_vehicledefinition_change',args=[self.visible.pk]),{'is_public':''}).status_code,403)
        self.visible.refresh_from_db();self.assertTrue(self.visible.is_public)


class PublicVisibilityMigrationTests(TransactionTestCase):
    def test_existing_rows_default_public_without_field_changes(self):
        executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes()
        try:
            before=[('reference','0013_vehicledefinition_base_msrp')]
            executor.migrate(before)
            apps=executor.loader.project_state(before).apps
            maker=apps.get_model('reference','Manufacturer').objects.create(name='Migration Maker',slug='migration-maker')
            model=apps.get_model('reference','VehicleModel').objects.create(manufacturer=maker,name='Model',slug='model')
            gen=apps.get_model('reference','Generation').objects.create(vehicle_model=model,name='Gen',slug='gen',start_year=2020)
            vd=apps.get_model('reference','VehicleDefinition').objects.create(generation=gen,model_year=2025,
                slug='retained',base_msrp=Decimal('12345.67'),is_active=False)
            original=apps.get_model('reference','VehicleDefinition').objects.values().get(pk=vd.pk)
            MigrationExecutor(connection).migrate(latest)
            after=VehicleDefinition.objects.values().get(pk=vd.pk)
            self.assertTrue(after.pop('is_public'))
            self.assertEqual(after,original)
        finally:MigrationExecutor(connection).migrate(latest)
