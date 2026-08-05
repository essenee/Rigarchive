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
        self.assertContains(response, "RigArchive Reference Implementation")

    def test_about_page_renders_cleanly(self):
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>\n        About | RigArchive\n    </title>", html=False)
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
