import json

from django.contrib import admin
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse

from reference.models import Manufacturer, VehicleDefinition
from .test_vehicle_msrp import VehicleMsrpTests


class VehicleSlugCorrectionTests(TestCase):
    setUpTestData = classmethod(VehicleMsrpTests.setUpTestData.__func__)
    vehicle = VehicleMsrpTests.vehicle

    def setUp(self):
        self.row = self.vehicle()
        self.url = reverse('admin:reference_vehicledefinition_change', args=[self.row.pk])
        self.client.force_login(self.user)

    def data(self, **kwargs):
        return dict(generation=self.gen.pk, engine=self.engine.pk, model_year=2026,
                    trim_name=self.row.trim_name, drivetrain=self.row.drivetrain,
                    market=self.row.market, is_active='on', slug_correction=self.row.slug,
                    base_msrp='', _save='Save') | kwargs

    def test_authorized_correction_display_warning_identity_and_history(self):
        response = self.client.get(self.url)
        form = response.context['adminform'].form
        self.assertEqual(form.initial['slug_correction'], self.row.slug)
        self.assertIn('invalidate existing public URLs', form.fields['slug_correction'].help_text)
        self.assertNotIn('uuid', form.fields)
        self.assertNotIn('id', form.fields)
        original = (self.row.pk, self.row.uuid, self.row.engine_id, self.row.base_msrp)
        old = self.row.slug
        self.assertEqual(self.client.post(self.url, self.data(slug_correction='corrected-slug')).status_code, 302)
        self.row.refresh_from_db()
        self.assertEqual(self.row.slug, 'corrected-slug')
        self.assertEqual((self.row.pk, self.row.uuid, self.row.engine_id, self.row.base_msrp), original)
        log = LogEntry.objects.get(object_id=str(self.row.pk), action_flag=CHANGE)
        self.assertIn(old, log.change_message)
        self.assertIn('corrected-slug', log.change_message)
        self.assertTrue(isinstance(json.loads(log.change_message), list))

    def test_duplicate_invalid_and_empty_rejected(self):
        other = self.vehicle(trim_name='Other')
        for slug in (other.slug, 'invalid slug!', ''):
            with self.subTest(slug=slug):
                response = self.client.post(self.url, self.data(slug_correction=slug))
                self.assertEqual(response.status_code, 200)
                self.assertIn('slug_correction', response.context['adminform'].form.errors)
                self.row.refresh_from_db()
                self.assertNotEqual(self.row.slug, slug)
        self.assertFalse(LogEntry.objects.filter(object_id=str(self.row.pk)).exists())

    def test_staff_without_change_permission_and_ordinary_user_rejected(self):
        for staff in (True, False):
            user = get_user_model().objects.create_user(username=f'no-change-{staff}', is_staff=staff)
            self.client.force_login(user)
            self.assertIn(self.client.post(self.url, self.data(slug_correction='forbidden')).status_code, (302,403))
        self.row.refresh_from_db()
        self.assertNotEqual(self.row.slug, 'forbidden')

    def test_creation_ignores_posted_correction_and_generates_slug(self):
        url = reverse('admin:reference_vehicledefinition_add')
        form = self.client.get(url).context['adminform'].form
        self.assertNotIn('slug_correction', form.fields)
        response = self.client.post(url, self.data(trim_name='New trim', engine_name='', slug_correction='injected'))
        self.assertEqual(response.status_code, 302)
        new = VehicleDefinition.objects.get(trim_name='New trim')
        self.assertTrue(new.slug)
        self.assertNotEqual(new.slug, 'injected')

    def test_unrelated_edits_keep_slug(self):
        old = self.row.slug
        data = self.data(notes='Edited', trim_name='Changed trim')
        del data['slug_correction']
        self.assertEqual(self.client.post(self.url, data).status_code,302)
        self.row.refresh_from_db()
        self.assertEqual(self.row.slug, old)
        self.assertNotIn('Slug', LogEntry.objects.get(object_id=str(self.row.pk)).change_message)

    def test_automated_updates_cannot_correct_existing_slug(self):
        old = self.row.slug
        self.row.slug = 'automated'
        with self.assertRaises(ValidationError):
            self.row.save()
        with self.assertRaises(ValidationError):
            VehicleDefinition.objects.filter(pk=self.row.pk).update(slug='automated')
        with self.assertRaises(ValidationError), transaction.atomic():
            VehicleDefinition.objects.bulk_update([self.row], ['slug'])
        self.row.refresh_from_db()
        self.assertEqual(self.row.slug, old)

    def test_other_model_admin_slugs_remain_readonly(self):
        for model in (Manufacturer, type(self.gen), type(self.gen.vehicle_model)):
            model_admin = admin.site._registry[model]
            self.assertFalse(model._meta.get_field('slug').editable)
            self.assertIn('slug', model_admin.readonly_fields)
