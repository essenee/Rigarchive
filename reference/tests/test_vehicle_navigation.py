"""RA-EXP-02B-1: URL authority, discovery and safe pending navigation."""
from urllib.parse import parse_qs, urlsplit

from django.http import Http404
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import (
    VEHICLE_DESTINATIONS, discover_manufacturers, discover_vehicle_models,
    get_active_vehicle_model, get_homepage_context, get_vehicle_context,
    get_vehicle_destination, resolve_vehicle_destination, vehicle_selector_url,
)


class VehicleNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.toyota = Manufacturer.objects.create(name="Toyota")
        cls.ford = Manufacturer.objects.create(name="Ford")
        cls.hidden = Manufacturer.objects.create(name="Hidden", is_active=False)
        cls.model = VehicleModel.objects.create(manufacturer=cls.toyota, name="Runner")
        cls.empty = VehicleModel.objects.create(manufacturer=cls.toyota, name="Unpopulated")
        cls.transit = VehicleModel.objects.create(manufacturer=cls.ford, name="Transit")
        cls.inactive = VehicleModel.objects.create(manufacturer=cls.toyota, name="Inactive", is_active=False)
        cls.hidden_model = VehicleModel.objects.create(manufacturer=cls.hidden, name="Hidden model")
        cls.generation = Generation.objects.create(vehicle_model=cls.model, name="First", start_year=2000, end_year=2005)
        cls.definition = VehicleDefinition.objects.create(generation=cls.generation, model_year=2001,
            trim_name="Shared", engine_name="V6", drivetrain="4WD", market="US")
        cls.sibling = VehicleDefinition.objects.create(generation=cls.generation, model_year=2001,
            trim_name="Shared", engine_name="V8", drivetrain="4WD", market="US")
        cls.selector = reverse("reference:vehicle-selector")

    def route_kwargs(self):
        return {"manufacturer_slug": self.toyota.slug, "vehicle_model_slug": self.model.slug}

    def scoped_urls(self):
        kwargs = dict(self.route_kwargs(), generation_slug=self.generation.slug)
        return [
            (self.model.get_absolute_url(), self.model, None, None),
            (self.generation.get_absolute_url(), self.model, self.generation, None),
            (reverse("reference:model-year-overview", kwargs=dict(kwargs, model_year=2001)), self.model, self.generation, None),
            (self.definition.get_absolute_url(), self.model, self.generation, self.definition),
            (reverse("measurements:generation-measurements", kwargs=kwargs), self.model, self.generation, None),
        ]

    def test_discovery_includes_models_without_definitions(self):
        self.assertCountEqual(discover_vehicle_models(), [self.model, self.empty, self.transit])
        self.assertCountEqual(discover_vehicle_models("tOyOtA"), [self.model, self.empty])
        self.assertEqual(list(discover_vehicle_models("trans")), [self.transit])
        self.assertEqual(list(discover_vehicle_models(manufacturer_slug=self.ford.slug)), [self.transit])
        self.assertEqual(list(discover_vehicle_models("Runner", self.ford.slug)), [])

    def test_grouped_search_and_populated_policy(self):
        groups = list(discover_manufacturers("Toyota"))
        self.assertEqual([g.name for g in groups], ["Toyota"])
        self.assertEqual(groups[0].active_vehicle_models, [self.model, self.empty])
        self.assertEqual(list(discover_vehicle_models(populated_only=True)), [self.model])
        self.assertEqual(list(discover_manufacturers(manufacturer_slug=self.ford.slug, populated_only=True)), [])

    def test_directory_and_homepage_keep_coverage_rules(self):
        response = self.client.get(reverse("reference:manufacturer-list"))
        self.assertEqual(list(response.context["manufacturers"]), [self.toyota])
        self.assertEqual(response.context["manufacturers"][0].active_vehicle_models, [self.model])
        self.assertEqual([p["model"] for p in get_homepage_context()["featured_platforms"]], [self.model])
        # Legacy search can retain a manufacturer group with no populated match.
        response = self.client.get(reverse("reference:manufacturer-list"), {"q": "Unpopulated"})
        self.assertEqual(list(response.context["manufacturers"]), [self.toyota])
        self.assertEqual(response.context["manufacturers"][0].active_vehicle_models, [])

    def test_inactive_generation_or_definition_does_not_count_as_coverage(self):
        self.definition.is_active = False
        self.definition.save()
        self.sibling.is_active = False
        self.sibling.save()
        self.assertEqual(list(discover_vehicle_models(populated_only=True)), [])
        self.assertIn(self.model, discover_vehicle_models())
        self.generation.is_active = False
        self.generation.save()
        self.assertEqual(list(discover_vehicle_models(populated_only=True)), [])

    def test_selector_defaults_to_generations_and_real_model_links(self):
        response = self.client.get(self.selector)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["destination"].token, "generations")
        choices = [choice for group in response.context["groups"] for choice in group["choices"]]
        self.assertEqual({c["url"] for c in choices}, {m.get_absolute_url() for m in [self.model, self.empty, self.transit]})
        self.assertContains(response, 'method="get"')
        self.assertContains(response, '<label for="id_q">Search manufacturers and models</label>')
        self.assertContains(response, 'src="/static/js/vehicle_quick_selector.js" defer')

    def test_search_and_manufacturer_filter_preserve_intent(self):
        response = self.client.get(self.selector, {"q": "Toyota", "destination": "measurements"})
        group = response.context["groups"][0]
        filter_url = group["filter_url"]
        self.assertEqual(parse_qs(urlsplit(filter_url).query), {"q": ["Toyota"], "destination": ["measurements"], "manufacturer": [self.toyota.slug]})
        filtered = self.client.get(filter_url)
        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, 'name="destination" value="measurements"')
        self.assertContains(filtered, f'name="manufacturer" value="{self.toyota.slug}"')
        self.assertEqual([g["manufacturer"] for g in filtered.context["groups"]], [self.toyota])
        clear = self.client.get(filtered.context["clear_manufacturer_url"])
        self.assertEqual(clear.context["destination"].token, "measurements")
        self.assertEqual(clear.context["selector_form"].cleaned_data["q"], "Toyota")

    def test_all_deferred_tokens_have_explicit_selection_pending_state(self):
        for contract in VEHICLE_DESTINATIONS[1:]:
            with self.subTest(token=contract.token):
                response = self.client.get(self.selector, {"destination": contract.token})
                choice = response.context["groups"][0]["choices"][0]
                self.assertTrue(choice["url"].startswith(self.selector + "?"))
                pending = self.client.get(choice["url"])
                self.assertEqual(pending.status_code, 200)
                self.assertEqual(pending.context["destination"], contract)
                self.assertIsNotNone(pending.context["selected_model"])
                self.assertIsNone(pending.context["selected_destination_url"])
                self.assertContains(pending, "not implemented yet")
                self.assertNotContains(pending, "/explore/vehicles/")

    def test_invalid_destination_has_error_and_no_results(self):
        for value in ["", "unknown", "https://evil.example/", "//evil.example/", "/vehicles/"]:
            with self.subTest(value=value):
                response = self.client.get(self.selector, {"destination": value})
                self.assertEqual(response.status_code, 400)
                self.assertContains(response, "Choose a valid navigation destination.", status_code=400)
                self.assertEqual(response.context["groups"], [])
                self.assertNotIn("Location", response)
                with self.assertRaises(ValueError):
                    get_vehicle_destination(value)

    def test_arbitrary_next_is_not_used(self):
        response = self.client.get(self.selector, {"next": "https://evil.example/", "destination": "generations"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "evil.example")
        self.assertNotIn("Location", response)

    def test_search_escaping_and_bounded_inputs(self):
        response = self.client.get(self.selector, {"q": '<script>alert("x")</script>'})
        self.assertNotContains(response, '<script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertEqual(self.client.get(self.selector, {"q": "x" * 201}).status_code, 400)
        self.assertEqual(self.client.get(self.selector, {"manufacturer": "../invalid"}).status_code, 400)

    def test_empty_and_no_results_are_distinct(self):
        response = self.client.get(self.selector, {"q": "no-match"})
        self.assertContains(response, "No manufacturers or models match")
        VehicleModel.objects.update(is_active=False)
        self.assertContains(self.client.get(self.selector), "No active vehicle models are available")

    def test_selector_ancestry_validation(self):
        for params in [
            {"manufacturer": self.hidden.slug},
            {"manufacturer": "missing"},
            {"manufacturer": self.toyota.slug, "model": self.transit.slug},
            {"manufacturer": self.toyota.slug, "model": self.inactive.slug},
        ]:
            self.assertEqual(self.client.get(self.selector, params).status_code, 404)
        self.assertEqual(self.client.get(self.selector, {"model": self.model.slug}).status_code, 400)
        self.assertEqual(get_active_vehicle_model(self.toyota.slug, self.empty.slug), self.empty)

    def test_selector_is_get_only(self):
        self.assertEqual(self.client.post(self.selector).status_code, 405)

    def test_url_objects_supply_context_on_all_existing_routes(self):
        for url, model, generation, definition in self.scoped_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                context = response.context["vehicle_context"]
                self.assertEqual(context.manufacturer, self.toyota)
                self.assertEqual(context.vehicle_model, model)
                self.assertEqual(context.generation, generation)
                self.assertEqual(context.vehicle_definition, definition)

    def test_query_filters_and_session_cannot_override_route_identity(self):
        session = self.client.session
        session["selected_vehicle_model"] = self.transit.slug
        session.save()
        response = self.client.get(self.generation.get_absolute_url(), {"year": 2001, "trim": "Shared"})
        self.assertIsNone(response.context["selected_config"])
        self.assertIsNone(response.context["vehicle_context"].vehicle_definition)
        response = self.client.get(self.generation.get_absolute_url(), {"configuration": self.definition.slug})
        self.assertEqual(response.context["selected_config"], self.definition)
        self.assertIsNone(response.context["vehicle_context"].vehicle_definition)
        self.assertEqual(response.context["vehicle_context"].vehicle_model, self.model)
        self.assertEqual(self.client.session["selected_vehicle_model"], self.transit.slug)
        self.assertIn("recently_viewed_generations", self.client.session)

    def test_no_selected_vehicle_session_writes(self):
        session = self.client.session
        session["sentinel"] = "preserve"
        session.save()
        for url, *_ in self.scoped_urls():
            self.client.get(url)
        self.client.get(self.selector, {"destination": "builds"})
        state = dict(self.client.session)
        self.assertEqual(set(state), {"sentinel", "recently_viewed_generations"})
        self.assertEqual(state["sentinel"], "preserve")

    def test_discovery_and_selector_issue_no_database_writes(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get(self.selector, {"manufacturer": self.toyota.slug, "model": self.empty.slug, "destination": "full-specs"})
        self.assertFalse(any(q["sql"].lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"} for q in queries))

    def test_existing_routes_reject_wrong_or_inactive_ancestry(self):
        urls = [row[0] for row in self.scoped_urls()]
        for url in urls:
            self.assertEqual(self.client.get(url.replace('/toyota/', '/ford/')).status_code, 404)
        for obj in [self.model, self.toyota]:
            obj.is_active = False
            obj.save()
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 404)
            with self.assertRaises(Http404):
                get_vehicle_context(self.model)
            obj.is_active = True
            obj.save()
        self.generation.is_active = False
        self.generation.save()
        for url in urls[1:]:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.generation.is_active = True
        self.generation.save()
        self.definition.is_active = False
        self.definition.save()
        self.assertEqual(self.client.get(self.definition.get_absolute_url()).status_code, 404)
        with self.assertRaises(Http404):
            get_vehicle_context(self.definition)

    def test_canonical_route_reversals_and_slug_collision_avoidance(self):
        for url, *_ in self.scoped_urls():
            match = resolve(url)
            self.assertEqual(reverse(match.view_name, kwargs=match.kwargs), url)
        self.assertEqual(self.selector, "/select-vehicle/")
        for contract in VEHICLE_DESTINATIONS[1:]:
            generation_url = f"/vehicles/toyota/runner/{contract.token}/"
            self.assertEqual(resolve(generation_url).view_name, "reference:generation-detail")
            planned = contract.pattern.replace('<manufacturer_slug>', 'toyota').replace('<vehicle_model_slug>', 'runner')
            with self.assertRaises(Resolver404):
                resolve(planned)
            with self.assertRaises(NoReverseMatch):
                reverse(contract.route_name, kwargs=self.route_kwargs())
            self.assertIsNone(resolve_vehicle_destination(self.model, contract.token))
        self.assertEqual(resolve_vehicle_destination(self.model), self.model.get_absolute_url())

    def test_pending_url_is_reproducible_without_session(self):
        url = vehicle_selector_url(destination="maintenance", manufacturer=self.toyota.slug, model=self.empty.slug, query="Toyota")
        first = self.client.get(url)
        from django.test import Client
        second = Client().get(url)
        self.assertEqual(first.context["selected_model"], second.context["selected_model"])
        self.assertEqual(second.context["destination"].token, "maintenance")

    def test_vehicles_entry_and_header_search_keep_separate_routes(self):
        response = self.client.get(reverse('about'))
        self.assertContains(response, f'href="{self.selector}?destination=generations" class="nav-link')
        self.assertContains(response, f'action="{reverse("reference:manufacturer-list")}"')
        self.assertContains(response, 'placeholder="Search manufacturers and models..."')
        self.assertNotContains(response, 'configs, or topics')

    def test_model_cards_use_newest_active_generation_chronology(self):
        model = VehicleModel.objects.create(manufacturer=self.toyota, name='4Runner')
        newest = Generation.objects.create(vehicle_model=model, name='Sixth Generation', start_year=2025)
        Generation.objects.create(vehicle_model=model, name='Fifth Generation', start_year=2010)
        Generation.objects.create(vehicle_model=model, name='Future', start_year=2030, is_active=False)
        response = self.client.get(self.selector, {'q': '4Runner'})
        choice = response.context['groups'][0]['choices'][0]
        self.assertEqual(choice['generation'], newest)
        self.assertEqual(choice['image_url'], '/static/images/generations/toyota-4runner-sixth-generation.jpg')
        self.assertEqual(choice['url'], model.get_absolute_url())
        self.assertContains(response, 'alt="Toyota 4Runner — Sixth Generation"')
        self.assertContains(response, 'Explore Generations →')

    def test_missing_newest_image_never_uses_older_or_other_model(self):
        model = VehicleModel.objects.create(manufacturer=self.toyota, name='4Runner')
        Generation.objects.create(vehicle_model=model, name='Fifth Generation', start_year=2010)
        newest = Generation.objects.create(vehicle_model=model, name='Unpictured newest', start_year=2026)
        response = self.client.get(self.selector, {'q': '4Runner'})
        choice = response.context['groups'][0]['choices'][0]
        self.assertEqual(choice['generation'], newest)
        self.assertEqual(choice['image_url'], '')
        self.assertContains(response, 'Photograph unavailable')
        self.assertNotContains(response, '/static/images/generations/')

    def test_models_without_active_generations_remain_selectable(self):
        Generation.objects.create(vehicle_model=self.empty, name='Inactive', start_year=2020, is_active=False)
        response = self.client.get(self.selector, {'q': 'Unpopulated'})
        choice = response.context['groups'][0]['choices'][0]
        self.assertIsNone(choice['generation'])
        self.assertEqual(choice['image_url'], '')
        self.assertEqual(choice['url'], self.empty.get_absolute_url())
        self.assertContains(response, 'No active Generations available yet.')
        model_page = self.client.get(choice['url'])
        self.assertContains(model_page, 'No generations are currently available.')

    def test_selector_filters_search_reset_and_long_names(self):
        self.empty.name = 'An exceptionally long model name ' * 3
        self.empty.save()
        response = self.client.get(self.selector, {'manufacturer': self.toyota.slug, 'q': 'exceptionally'})
        self.assertEqual([c['model'] for g in response.context['groups'] for c in g['choices']], [self.empty])
        self.assertContains(response, 'Explore Vehicles')
        self.assertContains(response, 'Browse vehicle platforms by manufacturer and model.')
        self.assertContains(response, self.empty.name)
        self.assertContains(response, f'href="{self.selector}?destination=generations&amp;q=exceptionally&amp;manufacturer=toyota" aria-current="true"')
        reset = response.context['reset_selector_url']
        self.assertEqual(reset, self.selector + '?destination=generations')
        self.assertEqual(len(self.client.get(reset).context['groups']), 2)

    def test_card_generation_query_count_does_not_grow_with_models(self):
        # Four directory queries plus two bounded global quick-selector queries.
        with self.assertNumQueries(6):
            self.client.get(self.selector)
        for index in range(5):
            model = VehicleModel.objects.create(manufacturer=self.toyota, name=f'Model {index}')
            Generation.objects.create(vehicle_model=model, name='Newest', start_year=2025)
        with self.assertNumQueries(6):
            self.client.get(self.selector)
