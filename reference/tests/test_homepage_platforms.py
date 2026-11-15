from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse

from core.models import HomepageVehiclePlatform
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition
from reference.services import get_homepage_context


class HomepagePlatformTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Toyota')
        cls.model = VehicleModel.objects.create(manufacturer=maker, name='4Runner')
        cls.other = VehicleModel.objects.create(manufacturer=maker, name='Tacoma')
        cls.gen = Generation.objects.create(vehicle_model=cls.model, name='Fifth Generation', start_year=2010)
        cls.override = Generation.objects.create(vehicle_model=cls.model, name='Fourth Generation', start_year=2003, end_year=2009)
        cls.foreign = Generation.objects.create(vehicle_model=cls.other, name='Third Generation', start_year=2016)
        for i, gen in enumerate((cls.gen, cls.override, cls.foreign)):
            VehicleDefinition.objects.create(generation=gen, model_year=gen.start_year, slug=f'configuration-{i}')
        cls.user = get_user_model().objects.create_superuser(username='platform-admin', password='test-password')

    def test_link_and_empty_selection(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'href="/select-vehicle/?destination=generations"')
        self.assertEqual(response.context['featured_platforms'], [])
        self.assertEqual(self.client.get('/select-vehicle/?destination=generations').status_code, 200)

    def test_enabled_order_and_no_automatic_new_cards(self):
        runner = HomepageVehiclePlatform.objects.create(vehicle_model=self.model, display_order=20)
        tacoma = HomepageVehiclePlatform.objects.create(vehicle_model=self.other, display_order=10)
        self.assertEqual([r['model'] for r in get_homepage_context()['featured_platforms']], [self.other,self.model])
        tacoma.is_enabled = False
        tacoma.save()
        self.assertEqual([r['model'] for r in get_homepage_context()['featured_platforms']], [self.model])
        runner.is_enabled = False
        runner.save()
        self.assertEqual(get_homepage_context()['featured_platforms'], [])

    def test_duplicate_prevention(self):
        HomepageVehiclePlatform.objects.create(vehicle_model=self.model)
        with self.assertRaises(ValidationError):
            HomepageVehiclePlatform(vehicle_model=self.model).save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            HomepageVehiclePlatform.objects.bulk_create([HomepageVehiclePlatform(vehicle_model=self.model)])

    def test_wrong_model_image_rejected_outside_admin(self):
        entry = HomepageVehiclePlatform(vehicle_model=self.model, image_generation=self.foreign)
        with self.assertRaises(ValidationError):
            entry.full_clean()
        with self.assertRaises(ValidationError):
            entry.save()
        self.assertFalse(HomepageVehiclePlatform.objects.exists())

    def test_partial_save_validates_the_effective_relationship(self):
        entry = HomepageVehiclePlatform.objects.create(vehicle_model=self.model, image_generation=self.gen)
        entry.vehicle_model = self.other
        entry.image_generation = self.foreign
        with self.assertRaises(ValidationError):
            entry.save(update_fields=['image_generation'])
        entry.refresh_from_db()
        self.assertEqual(entry.image_generation, self.gen)

    def test_selected_image_and_model_destination(self):
        HomepageVehiclePlatform.objects.create(vehicle_model=self.model, image_generation=self.override)
        response = self.client.get(reverse('home'))
        card = response.context['featured_platforms'][0]
        self.assertEqual(card['hero_image_url'], '/static/images/generations/toyota-4runner-fourth-generation.jpg')
        self.assertContains(response, f'href="{self.model.get_absolute_url()}"')
        self.assertNotContains(response, f'href="{self.override.get_absolute_url()}"')

    def test_default_image_and_missing_override_use_existing_fallback(self):
        entry = HomepageVehiclePlatform.objects.create(vehicle_model=self.model)
        default = get_homepage_context()['featured_platforms'][0]['hero_image_url']
        self.assertEqual(default, '/static/images/generations/toyota-4runner-fifth-generation.jpg')
        missing = Generation.objects.create(vehicle_model=self.model, name='No image', start_year=2020)
        entry.image_generation = missing
        entry.save()
        self.assertEqual(get_homepage_context()['featured_platforms'][0]['hero_image_url'], default)
        with patch('reference.views.get_presentation_hero_image_url', return_value=''):
            response = self.client.get(reverse('home'))
            self.assertContains(response, 'card-photo-placeholder')
            self.assertNotContains(response, 'class="card-photo"')

    def test_inactive_and_unpopulated_models_remain_hidden(self):
        HomepageVehiclePlatform.objects.create(vehicle_model=self.model)
        self.model.is_active = False
        self.model.save()
        self.assertEqual(get_homepage_context()['featured_platforms'], [])
        empty = VehicleModel.objects.create(manufacturer=self.model.manufacturer, name='Empty')
        HomepageVehiclePlatform.objects.create(vehicle_model=empty)
        self.assertEqual(get_homepage_context()['featured_platforms'], [])

    def test_admin_selection_order_visibility_and_filtered_image_choices(self):
        self.client.force_login(self.user)
        add = reverse('admin:core_homepagevehicleplatform_add')
        response = self.client.post(add, dict(vehicle_model=self.model.pk, display_order=4, is_enabled='on', _save='Save'))
        self.assertEqual(response.status_code, 302)
        entry = HomepageVehiclePlatform.objects.get()
        url = reverse('admin:core_homepagevehicleplatform_change', args=[entry.pk])
        form = self.client.get(url).context['adminform'].form
        self.assertEqual(set(form.fields['image_generation'].queryset), {self.gen,self.override})
        response = self.client.post(url, dict(vehicle_model=self.model.pk, display_order=2, image_generation=self.override.pk, _save='Save'))
        self.assertEqual(response.status_code, 302)
        entry.refresh_from_db()
        self.assertEqual(entry.display_order, 2)
        self.assertFalse(entry.is_enabled)
        self.assertEqual(entry.image_generation, self.override)
        response = self.client.post(url, dict(vehicle_model=self.model.pk, display_order=2, image_generation=self.foreign.pk, _save='Save'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('image_generation', response.context['adminform'].form.errors)

    def test_admin_requires_permissions(self):
        user = get_user_model().objects.create_user(username='no-platform-permission', is_staff=True)
        self.client.force_login(user)
        response = self.client.post(reverse('admin:core_homepagevehicleplatform_add'), dict(vehicle_model=self.model.pk))
        self.assertEqual(response.status_code,403)


class HomepageInitializationTests(TransactionTestCase):
    def test_migration_preserves_existing_card_order_and_canonical_data(self):
        maker = Manufacturer.objects.create(name='Toyota')
        other_maker = Manufacturer.objects.create(name='Jeep')
        names = [(other_maker,'Wrangler'),(maker,'Tacoma'),(maker,'4Runner')]
        models = []
        for mfr,name in names:
            model = VehicleModel.objects.create(manufacturer=mfr,name=name)
            gen = Generation.objects.create(vehicle_model=model,name='First',start_year=2000)
            VehicleDefinition.objects.create(generation=gen,model_year=2000)
            models.append(model)
        VehicleModel.objects.create(manufacturer=maker,name='Unpopulated')
        before = list(VehicleDefinition.objects.order_by('pk').values())
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([('core',None)])
            MigrationExecutor(connection).migrate(latest)
            self.assertEqual(list(HomepageVehiclePlatform.objects.values_list('vehicle_model__name',flat=True)), ['4Runner','Tacoma','Wrangler'])
            self.assertEqual(list(VehicleDefinition.objects.order_by('pk').values()), before)
            self.assertFalse(HomepageVehiclePlatform.objects.filter(image_generation__isnull=False).exists())
        finally:
            MigrationExecutor(connection).migrate(latest)
