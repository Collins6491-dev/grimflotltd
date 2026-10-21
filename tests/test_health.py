from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


class HealthCheckTests(SimpleTestCase):
    def test_health_check_is_public_and_contains_no_configuration(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class PublicFoundationTests(TestCase):
    def test_home_page_renders_the_stage_three_editorial_structure(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/home_stage3.html")
        self.assertContains(response, "Building Smart Homes.")
        self.assertContains(response, 'id="primary-menu"')
        self.assertContains(response, "site-loader")
        self.assertContains(response, 'data-hero')
        self.assertContains(response, "A home that understands its rhythm.")
        self.assertContains(response, "Development preview")
        self.assertContains(response, "images/demo/hero-smart-home.jpg")

    def test_hero_css_uses_a_valid_small_viewport_height_unit(self):
        """The enhanced carousel needs a non-zero containing block."""
        from django.conf import settings

        stylesheet = (settings.BASE_DIR / "static" / "css" / "site.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("calc(80svh - 8rem)", stylesheet)
        self.assertNotIn("svvh", stylesheet)

    @override_settings(DEBUG=False)
    def test_unknown_url_uses_the_branded_not_found_page(self):
        response = self.client.get("/a-page-that-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "errors/404.html")
        self.assertContains(
            response,
            "The page you requested is not here.",
            status_code=404,
        )
