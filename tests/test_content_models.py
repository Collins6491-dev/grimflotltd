"""Tests for Stage 4 editorial models and their public integration."""

from __future__ import annotations

from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.dashboard.forms import HomepageSettingsForm
from apps.core.homepage import get_homepage_context
from apps.core.models import (
    BrandingSettings,
    CompanyProfile,
    HeroSlide,
    HomepageCapability,
    HomepageProcessStep,
    HomepageSettings,
    SEOSettings,
    SocialLink,
)
from apps.core.validators import safe_upload_filename, validate_content_image
from apps.projects.models import Project, project_image_upload_path
from apps.services.models import Service, service_image_upload_path


class SingletonContentTests(TestCase):
    def test_singleton_settings_reject_a_non_default_site_identifier(self):
        profile = CompanyProfile(site_id=2, name="Another profile")

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_saved_company_profile_is_visible_in_the_public_shell(self):
        CompanyProfile.objects.create(
            name="GRIMFLOT LTD",
            tagline="Building Smart Homes.",
            service_area="Serving verified project locations",
        )

        response = self.client.get("/")

        self.assertContains(response, "Serving verified project locations")

    def test_company_profile_exposes_a_normalised_whatsapp_destination(self):
        profile = CompanyProfile(whatsapp_number="+234 805 855 7947")

        self.assertEqual(profile.whatsapp_url, "https://wa.me/2348058557947")

    def test_public_shell_has_the_configured_whatsapp_action(self):
        CompanyProfile.objects.create(whatsapp_number="+234 805 855 7947")

        response = self.client.get("/")

        self.assertContains(response, 'href="https://wa.me/2348058557947"')
        self.assertContains(response, "Chat with us on WhatsApp")


class HomepageContentTests(TestCase):
    @staticmethod
    def uploaded_image(name):
        image_buffer = BytesIO()
        Image.new("RGB", (20, 20), color="navy").save(image_buffer, format="PNG")
        return SimpleUploadedFile(name, image_buffer.getvalue(), content_type="image/png")

    @staticmethod
    def homepage_form_data(settings):
        form = HomepageSettingsForm(instance=settings)
        return {
            name: getattr(settings, name)
            for name in form.fields
            if not name.endswith("_image")
        }

    def test_published_capabilities_and_process_steps_replace_fallback_content(self):
        HomepageSettings.objects.create(solutions_heading="Systems that work together.")
        HomepageCapability.objects.create(
            title="Custom capability",
            summary="A staff-managed capability summary.",
            order=1,
            is_published=True,
        )
        HomepageProcessStep.objects.create(
            title="Scope",
            summary="A staff-managed delivery step.",
            order=1,
            is_published=True,
        )

        context = get_homepage_context()

        self.assertEqual(context["homepage"].solutions_heading, "Systems that work together.")
        self.assertEqual(context["solutions"][0]["title"], "Custom capability")
        self.assertEqual(context["delivery_steps"][0][1], "Scope")

    def test_hero_secondary_call_to_action_requires_both_values(self):
        slide = HeroSlide(
            eyebrow="A label",
            title="A title",
            summary="A summary",
            background_image="homepage/heroes/example.jpg",
            primary_label="Explore",
            primary_target="#solutions",
            secondary_label="Incomplete",
        )

        with self.assertRaises(ValidationError):
            slide.clean()

    def test_hero_context_uses_the_editor_supplied_alt_text_and_mobile_artwork(self):
        slide = HeroSlide.objects.create(
            eyebrow="A label",
            title="A title",
            summary="A summary",
            background_image="homepage/heroes/desktop.jpg",
            image_alt="A detailed description of the desktop image.",
            mobile_image="homepage/heroes/mobile.jpg",
            primary_label="Explore",
            primary_target="#solutions",
            is_published=True,
        )

        context = get_homepage_context()

        self.assertEqual(context["hero_slides"][0]["alt"], slide.image_alt)
        self.assertEqual(context["hero_slides"][0]["mobile_image"], "/media/homepage/heroes/mobile.jpg")

    def test_seo_canonical_path_must_be_an_on_site_path(self):
        settings = SEOSettings(
            page_key="home",
            title="Home",
            meta_description="A concise description for the home page.",
            canonical_path="https://example.com/",
        )

        with self.assertRaises(ValidationError):
            settings.full_clean()

    def test_feature_images_and_published_brand_content_render_in_the_public_shell(self):
        HomepageSettings.objects.create(
            energy_image="homepage/features/energy.jpg",
            energy_image_alt="Installed solar modules on a roof.",
            security_image="homepage/features/security.jpg",
            security_image_alt="A secure access-control installation.",
        )
        BrandingSettings.objects.create(
            logo="branding/grimflot-logo.png",
            favicon="branding/grimflot-favicon.png",
        )
        SocialLink.objects.create(
            label="LinkedIn",
            url="https://www.linkedin.com/company/grimflot",
            is_published=True,
        )

        response = self.client.get("/")

        self.assertContains(response, "/media/branding/grimflot-logo.png")
        self.assertContains(response, "/media/branding/grimflot-favicon.png")
        self.assertContains(response, "https://www.linkedin.com/company/grimflot")
        self.assertContains(response, "/media/homepage/features/energy.jpg")
        self.assertContains(response, "Installed solar modules on a roof.")
        self.assertContains(response, "/media/homepage/features/security.jpg")
        self.assertContains(response, "A secure access-control installation.")

    def test_all_four_solution_card_images_are_exposed_by_the_homepage_settings_form_and_template(self):
        form = HomepageSettingsForm()
        self.assertTrue({
            "energy_image", "smart_image", "security_image", "electrical_image", "difference_image",
        }.issubset(form.fields))

        HomepageSettings.objects.create(
            energy_image="homepage/features/energy.jpg",
            smart_image="homepage/features/smart.jpg",
            security_image="homepage/features/security.jpg",
            electrical_image="homepage/features/electrical.jpg",
            difference_image="homepage/features/difference.jpg",
        )
        response = self.client.get("/")

        self.assertContains(response, "/media/homepage/features/energy.jpg")
        self.assertContains(response, "/media/homepage/features/smart.jpg")
        self.assertContains(response, "/media/homepage/features/security.jpg")
        self.assertContains(response, "/media/homepage/features/electrical.jpg")
        self.assertContains(response, "/media/homepage/features/difference.jpg")

    def test_all_homepage_card_images_save_and_are_preserved_when_no_replacement_is_uploaded(self):
        with TemporaryDirectory() as media_directory, override_settings(MEDIA_ROOT=media_directory):
            settings = HomepageSettings.objects.create()
            form = HomepageSettingsForm(
                self.homepage_form_data(settings),
                {
                    "energy_image": self.uploaded_image("energy.png"),
                    "smart_image": self.uploaded_image("smart.png"),
                    "security_image": self.uploaded_image("security.png"),
                    "electrical_image": self.uploaded_image("electrical.png"),
                    "difference_image": self.uploaded_image("difference.png"),
                },
                instance=settings,
            )

            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            settings.refresh_from_db()
            original_paths = {
                name: getattr(settings, name).name
                for name in ("energy_image", "smart_image", "security_image", "electrical_image", "difference_image")
            }

            preservation_form = HomepageSettingsForm(
                self.homepage_form_data(settings), instance=settings
            )
            self.assertTrue(preservation_form.is_valid(), preservation_form.errors)
            preservation_form.save()
            settings.refresh_from_db()
            self.assertEqual(
                {
                    name: getattr(settings, name).name
                    for name in ("energy_image", "smart_image", "security_image", "electrical_image", "difference_image")
                },
                original_paths,
            )


class UploadPathTests(TestCase):
    def test_image_upload_paths_discard_directories_and_preserve_extensions(self):
        self.assertEqual(
            safe_upload_filename(r"untrusted\\folder\\Energy Plan.WEBP"),
            "energy-plan.webp",
        )
        self.assertEqual(
            service_image_upload_path(
                Service(title="Solar systems", slug="solar-systems"),
                "Panel.JPG",
            ),
            "services/solar-systems/panel.jpg",
        )
        self.assertEqual(
            project_image_upload_path(Project(slug="residence"), "Camera Feed.PNG"),
            "projects/residence/camera-feed.png",
        )

    def test_content_image_rejects_a_filename_extension_that_does_not_match_the_image(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="white").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile("apparently-safe.exe", image_buffer.getvalue())

        with self.assertRaises(ValidationError):
            validate_content_image(upload)


class PortfolioContentTests(TestCase):
    def test_project_can_be_related_to_multiple_services(self):
        automation = Service.objects.create(
            title="Smart automation",
            slug="smart-automation",
            short_description="Connected controls.",
            description="A complete smart automation service.",
        )
        energy = Service.objects.create(
            title="Energy systems",
            slug="energy-systems",
            short_description="Resilient power.",
            description="A complete energy systems service.",
        )
        project = Project.objects.create(
            title="Future case study",
            slug="future-case-study",
            excerpt="A project awaiting approved publication.",
            narrative="Detailed case-study content awaits approval.",
        )
        project.related_services.add(automation, energy)

        self.assertEqual(project.related_services.count(), 2)
