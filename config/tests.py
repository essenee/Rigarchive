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

    def test_homepage_preserves_photo_and_hides_derived_decorative_sketch(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, '<div class="hero-schematic-panel" aria-hidden="true">')
        self.assertContains(response, '4runner-outdoor-hero.png')
        self.assertContains(response, '4runner-diagram-approved-paper-length-corrected.png')
        self.assertContains(response, 'class="vehicle-study" width="502" height="514" alt=""')
        self.assertContains(response, 'width="1536" height="1024"')
        self.assertContains(response, '<a class="skip-link" href="#main-content">')


    def test_annotated_sketch_embeds_the_unchanged_original_without_numeric_labels(self):
        import base64
        import re
        import xml.etree.ElementTree as ET
        from django.conf import settings
        root = ET.fromstring((settings.BASE_DIR / 'static/images/homepage/toyota-4runner-technical-annotated.svg').read_text())
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        image = root.find('.//svg:image', ns)
        payload = image.attrib['href'].split(',', 1)[1]
        self.assertEqual(base64.b64decode(payload), (settings.BASE_DIR / 'static/images/homepage/Toyota 4Runner Technical Blueprint.png').read_bytes())
        self.assertEqual(root.attrib['viewBox'], '0 60 1200 1340')
        self.assertEqual(root.findall('.//svg:text', ns), [])
        self.assertEqual({g.attrib['data-dimension'] for g in root.findall('.//svg:g[@data-dimension]', ns)}, {'overall-length', 'overall-height', 'wheelbase', 'front-tire-width', 'rear-hatch-height'})
        self.assertEqual(image.attrib['width'], '1024')
        self.assertEqual(image.attrib['height'], '1535')
        self.assertEqual(len(root.findall('.//svg:path[@marker-start]', ns)), 5)
        self.assertEqual(len(root.findall('.//svg:path[@marker-end]', ns)), 5)
        for group in root.findall('.//svg:g[@data-dimension]', ns):
            for path in group.findall('svg:path', ns):
                self.assertLessEqual(set(re.findall(r'[A-Za-z]', path.attrib['d'])), {'M', 'H', 'V'})
        for crop in root.findall('svg:svg', ns):
            self.assertEqual(crop.attrib['viewBox'].split()[2:], [crop.attrib['width'], crop.attrib['height']])
        self.assertIn('no measured dimensions', root.find('svg:desc', ns).text)

    def test_homepage_paper_assets_are_separate_rgba_pngs(self):
        import struct
        from django.conf import settings
        assets = settings.BASE_DIR / 'static/images/homepage'
        for name, dimensions in {
            '4runner-diagram-approved-paper.png': (502, 514),
            'hero-photo-paper.png': (1024, 1024),
            'topographic-approved-neutral.png': (1536, 1536),
        }.items():
            with self.subTest(asset=name):
                data = (assets / name).read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                self.assertEqual(struct.unpack('>II', data[16:24]), dimensions)
                self.assertEqual(data[24:26], bytes([8, 6]))
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'technical-annotated.svg')
        self.assertContains(response, '4runner-outdoor-hero.png')
