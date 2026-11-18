"""Generation-scoped body choices and Admin-only concise labels."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.test import TestCase, RequestFactory
from django.urls import reverse

from reference.admin import factory_body_configuration_label
from reference.models import Manufacturer, VehicleModel, Generation, FactoryBodyConfiguration, VehicleDefinition


class AdminBodyConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Body Maker')
        model = VehicleModel.objects.create(manufacturer=maker, name='Body Model')
        cls.generation = Generation.objects.create(vehicle_model=model, name='First', start_year=2020)
        cls.other = Generation.objects.create(vehicle_model=model, name='Second', start_year=2020)
        cls.two = FactoryBodyConfiguration.objects.create(generation=cls.generation, door_configuration='two-door')
        cls.four = FactoryBodyConfiguration.objects.create(generation=cls.generation, door_configuration='four-door')
        cls.foreign = FactoryBodyConfiguration.objects.create(generation=cls.other, door_configuration='four-door')
        cls.user = get_user_model().objects.create_superuser(username='body-admin', password='test-password')

    def setUp(self):
        self.client.force_login(self.user)
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.user
        self.model_admin = admin.site._registry[VehicleDefinition]

    def vehicle(self):
        return VehicleDefinition.objects.create(generation=self.generation, model_year=2021,
            trim_name='Trim', engine_name='2.0L I4', drivetrain='4WD', factory_body_configuration=self.four)

    def test_existing_form_filters_and_preserves_selection_with_concise_label(self):
        row = self.vehicle()
        form = self.model_admin.get_form(self.request, row)(instance=row)
        field = form.fields['factory_body_configuration']
        self.assertCountEqual(field.queryset, [self.two, self.four])
        self.assertEqual(field.label_from_instance(self.four), 'Four Door')
        self.assertEqual(form.initial['factory_body_configuration'], self.four.pk)
        self.assertIn('>Four Door</option>', str(form['factory_body_configuration']))
        data = {k: '' if v is None else v for k,v in model_to_dict(row, fields=form.fields).items()}
        data.update(notes='Unrelated edit', slug_correction=row.slug, _save='Save')
        self.assertEqual(self.client.post(reverse('admin:reference_vehicledefinition_change', args=[row.pk]),data).status_code,302)
        row.refresh_from_db();self.assertEqual(row.factory_body_configuration_id,self.four.pk)

    def test_add_form_unknown_and_changed_generation(self):
        formclass = self.model_admin.get_form(self.request)
        self.assertFalse(formclass().fields['factory_body_configuration'].queryset.exists())
        for generation, expected in [(self.generation.pk, [self.two,self.four]),(self.other.pk,[self.foreign]),('',[]),('bad',[])]:
            form = formclass(data={'generation': generation})
            self.assertCountEqual(form.fields['factory_body_configuration'].queryset, expected)
        form = formclass(initial={'generation': self.generation.pk})
        self.assertCountEqual(form.fields['factory_body_configuration'].queryset,[self.two,self.four])

    def test_autocomplete_scopes_and_formats_results_and_requires_permission(self):
        url = reverse('admin:reference_factorybodyconfiguration_scoped_autocomplete')
        query = dict(app_label='reference',model_name='vehicledefinition',field_name='factory_body_configuration')
        for generation, expected in [(self.generation.pk,{self.two.pk:'Two Door',self.four.pk:'Four Door'}),
                                     (self.other.pk,{self.foreign.pk:'Four Door'}),('',{}),('bad',{}),(999999,{})]:
            response = self.client.get(url,{**query,'generation':generation})
            self.assertEqual(response.status_code,200)
            self.assertEqual({int(r['id']):r['text'] for r in response.json()['results']},expected)
        self.client.logout()
        self.assertNotEqual(self.client.get(url,{**query,'generation':self.generation.pk}).status_code,200)

    def test_forged_body_assignment_and_direct_workflow_mismatch_rejected(self):
        data = dict(generation=self.generation.pk,model_year=2021,trim_name='Trim',engine_name='2.0L I4',
                    drivetrain='4WD',market='US',factory_body_configuration=self.foreign.pk,_save='Save')
        response = self.client.post(reverse('admin:reference_vehicledefinition_add'),data)
        self.assertEqual(response.status_code,200)
        self.assertIn('factory_body_configuration',response.context['adminform'].form.errors)
        self.assertFalse(VehicleDefinition.objects.exists())
        row = self.vehicle();row.factory_body_configuration=self.foreign
        for validate in (row.full_clean,row.save):
            with self.assertRaises(ValidationError):validate()
        row.refresh_from_db();self.assertEqual(row.factory_body_configuration_id,self.four.pk)

    def test_property_order_and_shared_list_label_without_changing_str(self):
        body = FactoryBodyConfiguration.objects.create(generation=self.generation,
            door_configuration='four-door',roof_height_designation='soft-top')
        self.assertEqual(factory_body_configuration_label(body),'Four Door, Soft Top')
        row=self.vehicle();row.factory_body_configuration=body;row.save()
        self.assertEqual(self.model_admin.factory_body_configuration_label(row),'Four Door, Soft Top')
        self.assertEqual(self.model_admin.factory_body_configuration_label.admin_order_field,'factory_body_configuration')
        self.assertIn('door_configuration: four-door',str(body))
        self.assertIn('First',str(body))
        row.factory_body_configuration=None
        self.assertIsNone(self.model_admin.factory_body_configuration_label(row))
        page=self.client.get(reverse('admin:reference_vehicledefinition_changelist'))
        self.assertContains(page,'Four Door, Soft Top')

    def test_ambiguous_property_values_keep_only_necessary_distinctions(self):
        wheelbase=FactoryBodyConfiguration.objects.create(generation=self.generation,wheelbase_designation='long')
        length=FactoryBodyConfiguration.objects.create(generation=self.generation,body_length_designation='long')
        self.assertEqual(factory_body_configuration_label(wheelbase),'Wheelbase: Long')
        self.assertEqual(factory_body_configuration_label(length),'Body Length: Long')
        alternate=FactoryBodyConfiguration.objects.create(generation=self.generation,door_configuration='four_door')
        self.assertNotEqual(factory_body_configuration_label(alternate),factory_body_configuration_label(self.four))
