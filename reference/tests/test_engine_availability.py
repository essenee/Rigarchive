"""Manufacturer availability, dependent Admin selection and legacy preservation."""
from pathlib import Path
import shutil
import subprocess

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import model_to_dict
from django.test import TestCase, SimpleTestCase, RequestFactory
from django.urls import reverse

from reference.admin import EngineAdminForm
from reference.models import Engine, Manufacturer, VehicleModel, Generation, VehicleDefinition

PT = dict(engine_displacement_liters='2.0', engine_cylinders=4,
          engine_aspiration='turbocharged', fuel_type='gasoline', electrification_type='none')


class EngineAvailabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.primary = Manufacturer.objects.create(name='Primary')
        cls.additional = Manufacturer.objects.create(name='Additional')
        cls.unrelated = Manufacturer.objects.create(name='Unrelated')
        cls.generations = {}
        for maker in (cls.primary, cls.additional, cls.unrelated):
            model = VehicleModel.objects.create(manufacturer=maker, name='Model')
            cls.generations[maker.pk] = Generation.objects.create(vehicle_model=model, name='Generation', start_year=2020)
        cls.engine = Engine.objects.create(manufacturer=cls.primary, engine_code='SHARED', name='2.0L I4 Turbo', **PT)
        cls.engine.also_available_for_manufacturers.add(cls.additional)
        cls.other = Engine.objects.create(manufacturer=cls.unrelated, engine_code='OTHER', name='Other Engine', **PT)
        cls.user = get_user_model().objects.create_superuser(username='availability-admin', password='test-password')

    def setUp(self):
        self.client.force_login(self.user)
        self.request = RequestFactory().get('/admin/')
        self.request.user = self.user
        self.model_admin = admin.site._registry[VehicleDefinition]

    def form(self, generation=None, instance=None):
        form_class = self.model_admin.get_form(self.request, instance)
        return form_class(instance=instance, initial={'generation': generation.pk} if generation else {})

    def vehicle(self, maker, **kwargs):
        return VehicleDefinition(generation=self.generations[maker.pk], model_year=2021,
                                 trim_name='Trim', engine_name=self.engine.name, engine=self.engine, **kwargs)

    def test_primary_and_additional_availability_and_distinct_choices(self):
        for maker in (self.primary, self.additional):
            with self.subTest(maker=maker.name):
                vehicle = self.vehicle(maker)
                vehicle.full_clean(); vehicle.save()
                self.assertEqual(vehicle.engine_id, self.engine.pk)
                choices = list(self.form(self.generations[maker.pk]).fields['engine'].queryset)
                self.assertEqual(choices, [self.engine])
        self.assertEqual(list(Engine.objects.available_for_manufacturer(self.unrelated.pk)), [self.other])

    def test_model_rejects_unrelated_engine_and_generation_changes(self):
        vehicle = self.vehicle(self.unrelated)
        for validate in (vehicle.full_clean, vehicle.save):
            with self.assertRaises(ValidationError): validate()
        vehicle = self.vehicle(self.additional); vehicle.save()
        vehicle.generation = self.generations[self.unrelated.pk]
        with self.assertRaises(ValidationError): vehicle.save(update_fields=['generation'])

    def test_primary_cannot_be_redundantly_added_in_either_direction(self):
        before = Engine.objects.values().get(pk=self.engine.pk)
        for add in (lambda: self.engine.also_available_for_manufacturers.add(self.primary),
                    lambda: self.primary.additional_available_engines.add(self.engine)):
            with self.assertRaises(ValidationError), transaction.atomic(): add()
        self.assertEqual(Engine.objects.values().get(pk=self.engine.pk), before)
        self.assertEqual(list(self.engine.also_available_for_manufacturers.all()), [self.additional])

    def test_engine_admin_multiselect_excludes_primary_and_preserves_identity(self):
        form = admin.site._registry[Engine].get_form(self.request, self.engine)(instance=self.engine)
        field = form.fields['also_available_for_manufacturers']
        self.assertEqual(field.label, 'Also available for manufacturers')
        self.assertNotIn(self.primary, field.queryset)
        data = model_to_dict(self.engine)
        data['also_available_for_manufacturers'] = [self.primary.pk]
        invalid = EngineAdminForm(data=data, instance=self.engine)
        self.assertFalse(invalid.is_valid())
        self.assertIn('also_available_for_manufacturers', invalid.errors)
        before = Engine.objects.values().get(pk=self.engine.pk)
        self.engine.also_available_for_manufacturers.add(self.unrelated)
        self.engine.also_available_for_manufacturers.remove(self.unrelated)
        self.assertEqual(Engine.objects.values().get(pk=self.engine.pk), before)
        self.engine.internal_variant_key = 'changed'
        with self.assertRaises(ValidationError): self.engine.save()

    def test_add_form_unknown_manufacturer_and_generation_changes(self):
        self.assertFalse(self.form().fields['engine'].queryset.exists())
        form_class = self.model_admin.get_form(self.request)
        for generation, expected in [(self.generations[self.additional.pk].pk, [self.engine]),
                                     (self.generations[self.unrelated.pk].pk, [self.other]),
                                     ('bad', []), ('', []), (999999, [])]:
            form = form_class(data={'generation': generation})
            self.assertEqual(list(form.fields['engine'].queryset), expected)
        self.assertIn('js/admin_engine_availability.js', str(self.model_admin.media))

    def test_dependent_script_loads_after_django_jquery_and_autocomplete(self):
        scripts = (self.form().media + self.model_admin.media)._js
        custom = scripts.index('js/admin_engine_availability.js')
        self.assertLess(scripts.index('admin/js/jquery.init.js'), custom)
        self.assertLess(scripts.index('admin/js/autocomplete.js'), custom)
        jquery = next(script for script in scripts if script.startswith('admin/js/vendor/jquery/jquery.'))
        self.assertLess(scripts.index(jquery),
                        scripts.index('admin/js/jquery.init.js'))

    def test_existing_form_and_revoked_legacy_assignment_allow_unrelated_edits(self):
        vehicle = self.vehicle(self.additional); vehicle.save()
        self.engine.also_available_for_manufacturers.clear()
        self.assertEqual(list(self.form(instance=vehicle).fields['engine'].queryset), [self.engine])
        vehicle.notes = 'Unrelated edit'; vehicle.full_clean(); vehicle.save(update_fields=['notes'])
        url = reverse('admin:reference_vehicledefinition_change', args=[vehicle.pk])
        form = self.client.get(url).context['adminform'].form
        self.assertNotIn('engine_name', form.fields)
        data = {k: '' if v is None else v for k, v in model_to_dict(vehicle, fields=form.fields).items()}
        data.update(notes='Admin edit', slug_correction=vehicle.slug, _save='Save')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.status_code == 200 else '')
        vehicle.refresh_from_db(); self.assertEqual(vehicle.engine_id, self.engine.pk)
        vehicle.engine = self.other
        with self.assertRaises(ValidationError): vehicle.save()

    def test_autocomplete_is_scoped_distinct_and_permission_protected(self):
        url = reverse('admin:reference_engine_variant_autocomplete')
        query = dict(app_label='reference', model_name='vehicledefinition', field_name='engine')
        for generation, expected in [(None, []), ('bad', []), (999999, []),
                                     (self.generations[self.primary.pk].pk, [self.engine.pk]),
                                     (self.generations[self.additional.pk].pk, [self.engine.pk]),
                                     (self.generations[self.unrelated.pk].pk, [self.other.pk])]:
            response = self.client.get(url, {**query, **({'generation': generation} if generation else {})})
            self.assertEqual(response.status_code, 200)
            self.assertEqual([int(r['id']) for r in response.json()['results']], expected)
        self.client.logout()
        self.assertNotEqual(self.client.get(url, {**query, 'generation': self.generations[self.primary.pk].pk}).status_code, 200)

    def test_forged_post_rejected_but_shared_assignment_with_exact_name_succeeds(self):
        url = reverse('admin:reference_vehicledefinition_add')
        data = dict(generation=self.generations[self.unrelated.pk].pk, model_year=2021,
                    trim_name='Trim', engine=self.engine.pk, engine_name=self.engine.name,
                    market='US', drivetrain='4WD', _save='Save')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('engine', response.context['adminform'].form.errors)
        data['generation'] = self.generations[self.additional.pk].pk
        data['engine_name'] = 'Wrong name'
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertFalse(VehicleDefinition.objects.exists())
        data['engine_name'] = self.engine.name
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, response.context['adminform'].form.errors if response.status_code == 200 else '')
        row = VehicleDefinition.objects.get()
        self.assertEqual((row.engine_id, row.engine_name), (self.engine.pk, self.engine.name))


class EngineAvailabilityJavaScriptTests(SimpleTestCase):
    def test_generation_change_clears_engine_and_scopes_ajax(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is unavailable for the vanilla JavaScript regression.')
        script = Path(__file__).resolve().parents[2] / 'static/js/admin_engine_availability.js'
        result = subprocess.run([node, '-e', r'''
const assert = require('node:assert/strict');
const generation = {value: ''};
const autocompleteUrl = '/admin/reference/engine/variant-autocomplete/';
const engine = {value: 'old', getAttribute: name => name === 'data-ajax--url' ? autocompleteUrl : null};
let prefilter, changed;
function $(item) {
    if (typeof item === 'function') { item(); return; }
    return {on: (event, fn) => {changed = fn;}, select2: () => {},
            val: value => {item.value = value; return $(item);}, trigger: () => {}};
}
$.ajaxPrefilter = fn => {prefilter = fn;};
global.django = {jQuery: $};
global.document = {getElementById: id => id === 'id_generation' ? generation : engine};
require(process.argv[1]);
assert.equal(engine.disabled, true);
generation.value = '42'; changed();
assert.equal(engine.disabled, false); assert.equal(engine.value, null);
let aborted = false;
let request = {url: autocompleteUrl, data: 'term=CODE&page=2'};
prefilter(request, {}, {abort: () => {aborted = true;}});
assert.equal(request.data, 'term=CODE&page=2&generation=42');
generation.value = '43'; changed();
assert.equal(aborted, true);
request = {url: autocompleteUrl, data: 'term=CODE'};
prefilter(request); assert.equal(request.data, 'term=CODE&generation=43');
request = {url: '/other/', data: 'term=CODE'};
prefilter(request); assert.equal(request.data, 'term=CODE');
generation.value = ''; changed(); assert.equal(engine.disabled, true);
''', str(script)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
