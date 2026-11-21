import re
from html import unescape
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


class VehicleDefinitionChangelistTests(TestCase):
    manufacturer_param = "generation__vehicle_model__manufacturer__id__exact"
    model_param = "vehicle_model"

    @classmethod
    def setUpTestData(cls):
        cls.toyota = Manufacturer.objects.create(name="Toyota")
        cls.jeep = Manufacturer.objects.create(name="Jeep")
        cls.tacoma = VehicleModel.objects.create(manufacturer=cls.toyota, name="Tacoma")
        cls.four_runner = VehicleModel.objects.create(manufacturer=cls.toyota, name="4Runner")
        cls.wrangler = VehicleModel.objects.create(manufacturer=cls.jeep, name="Wrangler")
        tacoma = Generation.objects.create(vehicle_model=cls.tacoma, name="Tacoma Gen", start_year=2024)
        for model in (cls.four_runner, cls.wrangler):
            generation = Generation.objects.create(vehicle_model=model, name="Test Gen", start_year=2024)
            VehicleDefinition.objects.create(generation=generation, model_year=2026, trim_name="Other")
        cls.old = VehicleDefinition.objects.create(generation=tacoma, model_year=2024, trim_name="Match A")
        cls.new = VehicleDefinition.objects.create(generation=tacoma, model_year=2026, trim_name="Match B")
        cls.same_year = VehicleDefinition.objects.create(generation=tacoma, model_year=2026, trim_name="Match C")
        cls.inactive = VehicleDefinition.objects.create(
            generation=tacoma, model_year=2025, trim_name="Match D", is_active=False,
        )
        cls.admin = get_user_model().objects.create_superuser(username="changelist-admin", password="test-password")
        cls.viewer = get_user_model().objects.create_user(username="changelist-viewer", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(
            content_type__app_label="reference", codename="view_vehicledefinition",
        ))
        cls.unprivileged = get_user_model().objects.create_user(username="changelist-staff", is_staff=True)

    def setUp(self):
        self.url = reverse("admin:reference_vehicledefinition_changelist")
        self.client.force_login(self.admin)

    def get_list(self, filters=None):
        response = self.client.get(self.url, filters)
        self.assertEqual(response.status_code, 200)
        return response.context["cl"]

    def model_filter(self, changelist):
        return next(spec for spec in changelist.filter_specs if spec.title == "Model")

    def test_manufacturer_scopes_model_choices_and_model_filters_results(self):
        unfiltered = self.get_list()
        self.assertEqual(unfiltered.filter_specs[0].title, "manufacturer")
        self.assertEqual(unfiltered.filter_specs[1].title, "Model")
        self.assertCountEqual([label for _, label in self.model_filter(unfiltered).lookup_choices],
                              ["Toyota Tacoma", "Toyota 4Runner", "Jeep Wrangler"])

        manufacturer = {self.manufacturer_param: self.toyota.pk}
        toyotas = self.get_list(manufacturer)
        self.assertEqual({row.generation.vehicle_model_id for row in toyotas.result_list},
                         {self.tacoma.pk, self.four_runner.pk})
        self.assertEqual([label for _, label in self.model_filter(toyotas).lookup_choices],
                         ["Toyota 4Runner", "Toyota Tacoma"])

        selection = {**manufacturer, self.model_param: self.tacoma.pk, "is_active__exact": "1", "q": "Match"}
        tacomas = self.get_list(selection)
        self.assertEqual([row.pk for row in tacomas.result_list], [self.new.pk, self.same_year.pk, self.old.pk])
        clear = next(iter(self.model_filter(tacomas).choices(tacomas)))
        cleared = parse_qs(urlsplit(clear["query_string"]).query)
        self.assertNotIn(self.model_param, cleared)
        self.assertEqual(cleared, {key: [str(value)] for key, value in selection.items() if key != self.model_param})

        stale = self.get_list({self.manufacturer_param: self.jeep.pk, self.model_param: self.tacoma.pk})
        self.assertEqual(list(stale.result_list), [])
        self.assertEqual([label for _, label in self.model_filter(stale).lookup_choices], ["Jeep Wrangler"])
        for malformed in ("invalid", "999999"):
            with self.subTest(value=malformed):
                changelist = self.get_list({**manufacturer, self.model_param: malformed})
                self.assertEqual(list(changelist.result_list), [])

    def year_filter(self, response, label, years, selected):
        sidebar = re.search(
            r'<details data-filter-title="model year" open>(.*?)</details>',
            response.content.decode(),
            re.S,
        )
        self.assertIsNotNone(sidebar)
        self.assertIn("By model year", sidebar[1])
        toggle = re.search(
            r'<a id="year-filter-order-toggle" href="([^"]+)">\s*(.*?)\s*</a>',
            sidebar[1],
        )
        self.assertIsNotNone(toggle)
        self.assertEqual(toggle[2], label)
        choices = re.findall(r'<li( class="selected")?>\s*<a [^>]+>(All|[0-9]+)</a>', sidebar[1])
        self.assertEqual([value for _, value in choices], ["All", *years])
        self.assertEqual([value for marker, value in choices if marker], [selected])
        self.assertNotContains(response, 'id="year-sort-toggle"')
        return unescape(toggle[1])

    def test_rendered_year_filter_toggles_and_keeps_filters_and_search(self):
        descending = ["2026", "2025", "2024"]
        self.year_filter(self.client.get(self.url), "Newest first ↓", descending, "All")
        filters = {
            self.manufacturer_param: self.toyota.pk, self.model_param: self.tacoma.pk,
            "model_year": "2026", "drivetrain__exact": self.new.drivetrain,
            "is_active__exact": "1", "q": "Match",
        }
        response = self.client.get(self.url, filters)
        link = self.year_filter(response, "Newest first ↓", descending, "2026")
        self.assertEqual(parse_qs(urlsplit(link).query, keep_blank_values=True),
                         {**{key: [str(value)] for key, value in filters.items()}, "year_filter_order": ["asc"]})

        oldest = self.client.get(self.url + link)
        link = self.year_filter(oldest, "Oldest first ↑", descending[::-1], "2026")
        newest = self.client.get(self.url + link)
        self.year_filter(newest, "Newest first ↓", descending, "2026")
        for page in (response, oldest, newest):
            self.assertEqual([row.pk for row in page.context["cl"].result_list], [self.new.pk, self.same_year.pk])

    def test_sidebar_toggle_preserves_explicit_table_sort_and_pagination(self):
        model_admin = admin.site.get_model_admin(VehicleDefinition)
        filters = {self.model_param: self.tacoma.pk, "o": "1.2"}
        with patch.object(model_admin, "list_per_page", 2):
            response = self.client.get(self.url, {**filters, "p": 2})
            link = self.year_filter(response, "Newest first ↓", ["2026", "2025", "2024"], "All")
            reversed_sidebar = self.client.get(self.url + link)
            self.year_filter(reversed_sidebar, "Oldest first ↑", ["2024", "2025", "2026"], "All")
            for page in (response, reversed_sidebar):
                self.assertContains(page, 'class="sortable column-model_year sorted ascending"')
                self.assertEqual(page.context["cl"].page_num, 2)
                self.assertEqual([row.pk for row in page.context["cl"].result_list],
                                 [self.new.pk, self.same_year.pk])

    def test_view_permissions_and_delete_action_are_unchanged(self):
        response = self.client.get(self.url)
        self.assertTrue(response.context["has_add_permission"])
        self.assertContains(response, 'value="delete_selected"')
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="delete_selected"')
        self.assertFalse(response.context["has_add_permission"])
        change_url = reverse("admin:reference_vehicledefinition_change", args=[self.new.pk])
        self.assertEqual(self.client.post(change_url, {}).status_code, 403)
        self.client.force_login(self.unprivileged)
        self.assertEqual(self.client.get(self.url).status_code, 403)
