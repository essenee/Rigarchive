from django.test import Client, TestCase
from django.urls import reverse


class ApplicationShellTests(TestCase):
    """Test suite for application shell, navigation, accessibility, and error handling."""

    def setUp(self):
        self.client = Client()

    def test_homepage_renders_cleanly(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RigArchive")
        self.assertContains(response, '<a class="skip-link" href="#main-content">')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'tabindex="-1"')
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, "Vehicle Platforms")
        self.assertContains(response, "Find a Vehicle")

    def test_about_page_renders_cleanly(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>About | RigArchive</title>", html=True)
        self.assertContains(response, "<h1>About RigArchive</h1>")
        self.assertContains(response, "Canonical Vehicle Identity")
        self.assertContains(response, "Factory Configuration Reference")
        self.assertContains(response, "Evidence & Provenance")

    def test_primary_navigation_contains_working_links(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("home"))
        self.assertContains(response, reverse("reference:manufacturer-list"))
        self.assertContains(response, reverse("about"))

    def test_custom_404_handler(self):
        response = self.client.get("/non-existent-page-url-xyz/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page Not Found (404)", status_code=404)

    def test_custom_500_handler(self):
        response = self.client.get(reverse("home"))
        # Call custom_500 handler directly to verify response
        from config.views import custom_500
        handler_response = custom_500(response.wsgi_request)
        self.assertEqual(handler_response.status_code, 500)
        self.assertContains(handler_response, "Server Error (500)", status_code=500)


class ResponsiveHeaderTests(TestCase):
    def test_secondary_navigation_has_native_controls_and_visible_no_js_fallback(self):
        from reference.tests.test_experimental_hub import ConfiguratorParser
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Adventure vehicle info archive')
        self.assertContains(response, 'aria-controls="secondary-navigation-panel" hidden')
        self.assertContains(response, '<span>More</span><span class="secondary-navigation-caret" aria-hidden="true">▾</span>')
        self.assertNotContains(response, '···')
        self.assertContains(response, '<div id="secondary-navigation-panel" class="secondary-navigation-panel">')
        self.assertContains(response, 'js/header_navigation.js')
        links = ConfiguratorParser(response.text).links
        for name, destination in [('Measurements', '/vehicles/?view=measurements'), ('Builds', '#builds'), ('Service Guides', '#service-guides'), ('About', '/about/')]:
            self.assertTrue(any(a['text'].strip() == name and a['attrs']['href'] == destination for a in links))
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'My Garage')

    def test_homepage_keeps_original_images_and_hides_decorative_sketch_from_accessibility(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, '<div class="hero-schematic-panel" aria-hidden="true">')
        self.assertContains(response, '4runner-outdoor-hero.png')
        self.assertContains(response, 'Toyota%204Runner%20Technical%20Blueprint.png')
        self.assertContains(response, 'class="vehicle-study" width="1024" height="1535" alt=""')
        self.assertContains(response, 'width="1536" height="1024"')
        self.assertContains(response, '<a class="skip-link" href="#main-content">')
