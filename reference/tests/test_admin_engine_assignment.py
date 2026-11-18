from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms.models import BaseModelForm, model_to_dict
from django.test import TestCase, RequestFactory
from django.urls import reverse

from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition, Engine
from reference.powertrain import FIELDS, record_powertrain


class AdminEngineAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.jeep = Manufacturer.objects.create(name='Jeep')
        cls.toyota = Manufacturer.objects.create(name='Toyota')
        wrangler = VehicleModel.objects.create(manufacturer=cls.jeep, name='Wrangler')
        runner = VehicleModel.objects.create(manufacturer=cls.toyota, name='4Runner')
        cls.jl = Generation.objects.create(vehicle_model=wrangler, name='JL', start_year=2018)
        cls.runner = Generation.objects.create(vehicle_model=runner, name='Fifth Generation', start_year=2010)
        cls.pt = dict(engine_displacement_liters=Decimal('3.6'), engine_cylinders=6,
                      engine_aspiration='naturally_aspirated', fuel_type='gasoline', electrification_type='none')
        cls.erc = Engine.objects.create(manufacturer=cls.jeep, engine_code='ERC', name='3.6L V6 ESS', **cls.pt)
        cls.erg = Engine.objects.create(manufacturer=cls.jeep, engine_code='ERG', name='3.6L V6 eTorque',
                                       **(cls.pt | {'electrification_type': 'mild_hybrid'}))
        cls.alias = Engine.objects.create(manufacturer=cls.jeep, engine_code='ERC-ALIAS', name='3.6L V6', **cls.pt)
        cls.toyota_engine = Engine.objects.create(manufacturer=cls.toyota, engine_code='1GR-FE', name='4.0L V6',
                                                 **(cls.pt | {'engine_displacement_liters': Decimal('4.0')}))
        cls.user = get_user_model().objects.create_superuser(username='engine-admin',password='test-password')

    def setUp(self):
        self.client.force_login(self.user)

    def legacy(self, **kwargs):
        return VehicleDefinition.objects.create(**(dict(generation=self.jl, model_year=2021,
            trim_name='Sport S', engine_name='3.6L V6 legacy alias', drivetrain='4WD', market='US',
            slug=f'legacy-{VehicleDefinition.objects.count()}', base_msrp=Decimal('12345.67'),
            is_public=False, is_active=True, notes='Preserve notes') | kwargs))

    def submit(self, row, engine, **kwargs):
        url = reverse('admin:reference_vehicledefinition_change',args=[row.pk])
        form = self.client.get(url).context['adminform'].form
        data = model_to_dict(row,fields=form.fields)
        data.update(engine=engine.pk,slug_correction=row.slug,_save='Save',**kwargs)
        data = {key: '' if value is None else value for key,value in data.items()}
        return self.client.post(url,data)

    def assert_unrelated_preserved(self, row, before):
        allowed = {'engine_id', *FIELDS, 'updated_at'}
        after = VehicleDefinition.objects.values().get(pk=row.pk)
        for key,value in before.items():
            if key not in allowed:self.assertEqual(after[key],value,key)

    def test_initial_pre2022_assignment_fills_only_unknowns_preserving_name_and_identity(self):
        row=self.legacy(engine_name=self.erc.name,engine_displacement_liters=Decimal('3.6'),engine_cylinders=6)
        before=VehicleDefinition.objects.values().get(pk=row.pk)
        engines=list(Engine.objects.order_by('pk').values())
        self.assertEqual(self.submit(row,self.erc).status_code,302)
        row.refresh_from_db()
        self.assertEqual(row.engine_id,self.erc.pk)
        self.assertEqual(record_powertrain(row),record_powertrain(self.erc))
        self.assert_unrelated_preserved(row,before)
        self.assertEqual(list(Engine.objects.order_by('pk').values()),engines)

    def test_initial_non_wrangler_assignment_completes_all_unknowns(self):
        row=self.legacy(generation=self.runner,model_year=2020,engine_name='4.0L V6')
        self.assertEqual(self.submit(row,self.toyota_engine).status_code,302)
        row.refresh_from_db()
        self.assertEqual(record_powertrain(row),record_powertrain(self.toyota_engine))

    def test_assignment_requires_registered_name_before_fk(self):
        row=self.legacy()
        alias=row.engine_name
        self.assertEqual(self.submit(row,self.erc,engine_name='').status_code,200)
        row.refresh_from_db()
        self.assertEqual(row.engine_name,alias)
        self.assertIsNone(row.engine_id)
        self.assertEqual(self.submit(row,self.erc,engine_name=self.erc.name).status_code,302)
        row.refresh_from_db()
        self.assertEqual(row.engine_name,self.erc.name)

    def test_electrification_conflict_is_normal_nonfield_error_and_matching_engine_succeeds(self):
        row=self.legacy(engine_name=self.erg.name,**(self.pt|{'electrification_type':'mild_hybrid'}))
        response=self.submit(row,self.erc)
        self.assertEqual(response.status_code,200)
        form=response.context['adminform'].form
        self.assertNotIn('electrification_type',form.fields)
        self.assertIn('electrification type',str(form.non_field_errors()))
        self.assertIn('Known values are not overwritten',str(form.non_field_errors()))
        row.refresh_from_db();self.assertIsNone(row.engine_id)
        self.assertEqual(row.electrification_type,'mild_hybrid')
        self.assertEqual(self.submit(row,self.erg).status_code,302)
        row.refresh_from_db();self.assertEqual(row.engine_id,self.erg.pk)

    def test_conflicts_in_every_snapshot_attribute_reject_without_http500(self):
        conflicts=dict(engine_displacement_liters=Decimal('2.0'), engine_cylinders=4,
                       engine_aspiration='turbocharged',fuel_type='diesel',electrification_type='mild_hybrid')
        for key,value in conflicts.items():
            with self.subTest(key=key):
                row=self.legacy(**(self.pt|{key:value}))
                before=VehicleDefinition.objects.values().get(pk=row.pk)
                response=self.submit(row,self.erc)
                self.assertEqual(response.status_code,200)
                self.assertTrue(response.context['adminform'].form.non_field_errors())
                self.assertEqual(VehicleDefinition.objects.values().get(pk=row.pk),before)

    def test_changing_existing_engine_accepts_compatible_properties_and_rejects_conflicts(self):
        compatible=Engine.objects.create(manufacturer=self.jeep,engine_code='ERC2',name=self.erc.name,**self.pt)
        row=self.legacy(engine=self.erc,engine_name=self.erc.name,**self.pt)
        original=row.slug
        self.assertEqual(self.submit(row,compatible).status_code,302)
        row.refresh_from_db();self.assertEqual(row.engine_id,compatible.pk)
        self.assertEqual(self.submit(row,self.erg).status_code,200)
        row.refresh_from_db();self.assertEqual(row.engine_id,compatible.pk)
        self.assertEqual(row.electrification_type,'none');self.assertEqual(row.slug,original)

    def test_unchanged_relationship_does_not_cascade_registry_edits(self):
        row=self.legacy(engine=self.erc,**self.pt)
        self.erc.electrification_type='mild_hybrid';self.erc.save()
        registry=list(Engine.objects.order_by('pk').values())
        self.assertEqual(self.submit(row,self.erc,notes='Unrelated edit').status_code,302)
        row.refresh_from_db();self.assertEqual(row.electrification_type,'none')
        self.assertEqual(list(Engine.objects.order_by('pk').values()),registry)

    def test_cross_manufacturer_and_incomplete_registry_rejected_normally(self):
        row=self.legacy()
        response=self.submit(row,self.toyota_engine)
        self.assertEqual(response.status_code,200)
        self.assertIn('engine',response.context['adminform'].form.errors)
        pending=Engine.objects.create(manufacturer=self.jeep,engine_code='PENDING',name='Incomplete')
        response=self.submit(row,pending)
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['adminform'].form.non_field_errors())
        row.refresh_from_db();self.assertIsNone(row.engine_id)

    def test_model_validation_remains_enforced_outside_admin(self):
        row=self.legacy(**(self.pt|{'electrification_type':'mild_hybrid'}))
        row.engine=self.erc
        for validate in (row.full_clean,row.save):
            with self.assertRaises(ValidationError) as caught:validate()
            self.assertEqual(caught.exception.error_dict['electrification_type'][0].code,'ENGINE_REGISTRY_CONFLICT')
        row.refresh_from_db();self.assertIsNone(row.engine_id)

    def test_framework_excluded_field_crash_reproduced_and_override_preserves_error_code(self):
        row=self.legacy()
        request=RequestFactory().get('/');request.user=self.user
        formclass=admin.site._registry[VehicleDefinition].get_form(request,row)
        form=formclass(data=model_to_dict(row,fields=formclass.base_fields),instance=row)
        form.full_clean()
        error=ValidationError({'electrification_type':ValidationError('Mismatch',code='ENGINE_REGISTRY_CONFLICT')})
        with self.assertRaisesRegex(ValueError,"no field named 'electrification_type'"):
            BaseModelForm._update_errors(form,error)
        form._update_errors(error)
        errors=form.errors.as_data()[NON_FIELD_ERRORS]
        self.assertEqual(errors[0].code,'ENGINE_REGISTRY_CONFLICT')
        self.assertIn('electrification type',errors[0].message)

    def test_partial_save_persists_the_auto_completed_unknown_fields(self):
        row=self.legacy(engine_name='')
        original=(row.pk,row.uuid,row.slug,row.base_msrp,row.is_public,row.is_active)
        row.engine=self.erc
        row.save(update_fields=iter(['engine']))
        row.refresh_from_db()
        self.assertEqual(record_powertrain(row),record_powertrain(self.erc))
        self.assertEqual(row.engine_name,self.erc.name)
        self.assertEqual((row.pk,row.uuid,row.slug,row.base_msrp,row.is_public,row.is_active),original)

    def test_clearing_known_snapshot_cannot_disguise_conflict_as_unknown(self):
        row=self.legacy(**(self.pt|{'electrification_type':'mild_hybrid'}))
        row.engine=self.erc;row.electrification_type=None
        with self.assertRaises(ValidationError):row.save()
        row.refresh_from_db();self.assertIsNone(row.engine_id)
        self.assertEqual(row.electrification_type,'mild_hybrid')
