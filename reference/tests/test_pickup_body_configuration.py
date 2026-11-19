from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.forms import Select, TextInput
from django.test import TestCase, RequestFactory
from django.urls import reverse

from reference.admin import factory_body_configuration_label
from reference.models import Manufacturer, VehicleModel, Generation, FactoryBodyConfiguration as Body, NominalBedLength


class PickupBodyConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker=Manufacturer.objects.create(name='Pickup Maker')
        model=VehicleModel.objects.create(manufacturer=maker,name='Tacoma')
        cls.generation=Generation.objects.create(vehicle_model=model,name='Fourth',start_year=2024)
        cls.five=NominalBedLength.objects.create(designation='5-ft')
        cls.six=NominalBedLength.objects.create(designation='6-ft')
        cls.user=get_user_model().objects.create_superuser(username='pickup-admin',password='test-password')

    def setUp(self):
        self.client.force_login(self.user)
        self.request=RequestFactory().get('/admin/');self.request.user=self.user
        self.model_admin=admin.site._registry[Body]

    def test_native_controlled_dropdowns_and_open_designations(self):
        form=self.model_admin.get_form(self.request)()
        for field in ('door_configuration','cab_configuration'):
            self.assertIsInstance(form.fields[field].widget,Select)
        self.assertEqual(dict(form.fields['door_configuration'].choices)['two-door'],'2-Door')
        self.assertEqual(dict(form.fields['door_configuration'].choices)['four-door'],'4-Door')
        self.assertEqual(dict(form.fields['cab_configuration'].choices)['xtracab'],'XtraCab')
        self.assertEqual(dict(form.fields['cab_configuration'].choices)['double-cab'],'Double Cab')
        self.assertIsInstance(form.fields['bed_length'].widget.widget,Select)
        self.assertCountEqual(form.fields['bed_length'].queryset,[self.five,self.six])
        self.assertIsInstance(form.fields['wheelbase_designation'].widget,TextInput)

    def test_admin_can_extend_nominal_bed_values_without_schema_change(self):
        url=reverse('admin:reference_nominalbedlength_add')
        for value in ('5.5-ft','6.5-ft','8-ft'):
            self.assertEqual(self.client.post(url,{'designation':value,'_save':'Save'}).status_code,302)
        form=self.model_admin.get_form(self.request)()
        self.assertEqual(form.fields['bed_length'].queryset.count(),5)
        bed=NominalBedLength.objects.get(designation='5.5-ft')
        body=Body.objects.create(generation=self.generation,cab_configuration='double-cab',door_configuration='four-door',bed_length=bed)
        self.assertEqual(factory_body_configuration_label(body),'Double Cab, 5.5-ft Bed')

    def test_three_pickup_tuples_and_readable_labels(self):
        for cab,door,bed,label in [('xtracab','two-door',self.six,'XtraCab, 6-ft Bed'),
            ('double-cab','four-door',self.five,'Double Cab, 5-ft Bed'),
            ('double-cab','four-door',self.six,'Double Cab, 6-ft Bed')]:
            body=Body.objects.create(generation=self.generation,cab_configuration=cab,door_configuration=door,bed_length=bed)
            self.assertEqual(factory_body_configuration_label(body),label)
            self.assertEqual(body.door_configuration,door)
            self.assertFalse(body.vehicle_definitions.exists())
            with self.assertRaises(ValidationError):
                Body.objects.create(generation=self.generation,cab_configuration=cab,door_configuration=door,bed_length=bed)
        self.assertEqual(Body.objects.count(),3)

    def test_model_and_form_reject_invalid_or_cross_property_values(self):
        for attrs in ({'door_configuration':'5-ft'}, {'cab_configuration':'two-door'},
                      {'cab_configuration':'double-cab','door_configuration':'two-door'}):
            with self.assertRaises(ValidationError):Body.objects.create(generation=self.generation,**attrs)
        with self.assertRaises(ValidationError):NominalBedLength.objects.create(designation='two-door')
        form=self.model_admin.get_form(self.request)(data={'generation':self.generation.pk,
            'door_configuration':'four-door','cab_configuration':'invalid','bed_length':999999})
        self.assertFalse(form.is_valid())
        self.assertIn('cab_configuration',form.errors);self.assertIn('bed_length',form.errors)

    def test_existing_wrangler_labels_and_frozen_identity_projection(self):
        from reference.models import BODY_ATTRIBUTES
        from reference.body_identity import DIMENSIONS
        self.assertNotIn('cab_configuration',BODY_ATTRIBUTES);self.assertNotIn('bed_length',DIMENSIONS)
        for door,label in [('two-door','Two Door'),('four-door','Four Door')]:
            body=Body.objects.create(generation=self.generation,door_configuration=door)
            self.assertEqual(factory_body_configuration_label(body),label)
            self.assertIsNone(body.cab_configuration);self.assertIsNone(body.bed_length)

    def test_bed_reference_is_protected_and_old_contract_cannot_drop_pickup_fields(self):
        from reference.ingestion.importing.body_identity import body_state, ResolutionError
        body=Body.objects.create(generation=self.generation,cab_configuration='xtracab',door_configuration='two-door',bed_length=self.six)
        with self.assertRaises(ProtectedError):self.six.delete()
        with self.assertRaises(ResolutionError) as caught:body_state(body)
        self.assertEqual(caught.exception.diagnostic['code'],'UNSUPPORTED_BODY_DIMENSION')
