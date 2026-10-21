"""Database-backed site configuration and editorial content.

The models in this module intentionally contain no display logic. Templates use
the small homepage adapter so this content can evolve without coupling editors
to page markup.
"""

from __future__ import annotations

import re

from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q

from .validators import safe_upload_filename, validate_content_image, validate_cta_target


hex_colour = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a six-digit hex colour such as #D71920.",
)


def branding_upload_path(instance: models.Model, filename: str) -> str:
    """Keep brand uploads in a predictable, non-user-controlled location."""
    return f"branding/{safe_upload_filename(filename)}"


def hero_upload_path(instance: "HeroSlide", filename: str) -> str:
    """Keep hero artwork organised independently from product media."""
    return f"homepage/heroes/{instance.order:02d}-{safe_upload_filename(filename)}"


class TimeStampedModel(models.Model):
    """Reusable audit fields for editorial records."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SingletonContentModel(TimeStampedModel):
    """Base for one global record per independently managed settings area."""

    site_id = models.PositiveSmallIntegerField(default=1, editable=False, unique=True)

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=Q(site_id=1),
                name="%(app_label)s_%(class)s_site_id_is_one",
            )
        ]

    @classmethod
    def get_solo(cls):
        """Return the saved record or an unsaved sensible default for rendering."""
        return cls.objects.filter(site_id=1).first() or cls(site_id=1)


class CompanyProfile(SingletonContentModel):
    """The verified company details used throughout future public pages."""

    name = models.CharField(max_length=120, default="GRIMFLOT LTD")
    tagline = models.CharField(max_length=160, default="Building Smart Homes")
    description = models.TextField(blank=True, max_length=2_000)
    email = models.EmailField(blank=True, default="grimflotltd@gmail.com")
    phone = models.CharField(blank=True, max_length=40, default="08032272788")
    secondary_phone = models.CharField(blank=True, max_length=40, default="09025525545")
    whatsapp_number = models.CharField(blank=True, max_length=40, default="+234 805 855 7947")
    address = models.TextField(
        blank=True,
        max_length=500,
        default="Near Frankchris Filling Station, Otukutu Junction, Delta State, Nigeria.",
    )
    service_area = models.CharField(blank=True, max_length=255)
    business_hours = models.TextField(blank=True, max_length=1_000, default="Monday–Friday: 8:00 AM–5:30 PM.")

    class Meta(SingletonContentModel.Meta):
        verbose_name = "company profile"
        verbose_name_plural = "company profile"

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def _digits(value: str) -> str:
        return re.sub(r"\D", "", value or "")

    @property
    def whatsapp_url(self) -> str:
        """Return the direct WhatsApp destination from the staff-managed number."""
        digits = self._digits(self.whatsapp_number)
        return f"https://wa.me/{digits or '2348058557947'}"

    @property
    def phone_url(self) -> str:
        return f"tel:{self._digits(self.phone)}" if self.phone else ""

    @property
    def secondary_phone_url(self) -> str:
        return f"tel:{self._digits(self.secondary_phone)}" if self.secondary_phone else ""


class BrandingSettings(SingletonContentModel):
    """Visual identity settings. Colour values stay centrally managed."""

    logo = models.ImageField(
        upload_to=branding_upload_path,
        blank=True,
        validators=[validate_content_image],
        help_text="Use an approved high-resolution logo image.",
    )
    favicon = models.ImageField(
        upload_to=branding_upload_path,
        blank=True,
        validators=[validate_content_image],
        help_text="Use a square PNG, ICO, or similar browser-safe icon.",
    )
    primary_colour = models.CharField(max_length=7, default="#D71920", validators=[hex_colour])
    secondary_colour = models.CharField(max_length=7, default="#102F67", validators=[hex_colour])
    ink_colour = models.CharField(max_length=7, default="#07101F", validators=[hex_colour])

    class Meta(SingletonContentModel.Meta):
        verbose_name = "branding settings"
        verbose_name_plural = "branding settings"

    def __str__(self) -> str:
        return "Branding settings"


class HomepageSettings(SingletonContentModel):
    """Editable editorial copy for the Stage 3 homepage sections."""

    solutions_eyebrow = models.CharField(max_length=80, default="One connected standard")
    solutions_heading = models.CharField(
        max_length=180,
        default="Every system should make the next one work better.",
    )
    solutions_intro = models.TextField(
        max_length=500,
        default=(
            "We bring the systems that shape a modern space into a single practical "
            "conversation—from the energy below the roofline to the networks and "
            "controls within it."
        ),
    )
    energy_eyebrow = models.CharField(max_length=80, default="Power, with a plan")
    energy_heading = models.CharField(
        max_length=180,
        default="Build resilience into the architecture, not as an afterthought.",
    )
    energy_copy = models.TextField(
        max_length=700,
        default=(
            "Solar generation, battery storage, inverter systems, and the electrical "
            "details around them are strongest when they are designed to work as one "
            "clear whole."
        ),
    )
    energy_image = models.ImageField(
        upload_to="homepage/features/",
        blank=True,
        validators=[validate_content_image],
        help_text="Optional replacement for the development solar image.",
    )
    energy_image_alt = models.CharField(
        max_length=255,
        default="A technician carefully installing a solar panel.",
    )
    smart_image = models.ImageField(
        upload_to="homepage/features/",
        blank=True,
        validators=[validate_content_image],
        help_text="Optional replacement for the development smart-home image.",
    )
    smart_image_alt = models.CharField(
        max_length=255,
        default="A connected smart-home installation.",
    )
    security_eyebrow = models.CharField(max_length=80, default="Quiet confidence")
    security_heading = models.CharField(
        max_length=180,
        default="Security starts before the camera is switched on.",
    )
    security_copy = models.TextField(
        max_length=700,
        default=(
            "We consider visibility, access, power, placement, and the network that "
            "joins them—so a security system has the context it needs to do its job well."
        ),
    )
    security_image = models.ImageField(
        upload_to="homepage/features/",
        blank=True,
        validators=[validate_content_image],
        help_text="Optional replacement for the development security image.",
    )
    security_image_alt = models.CharField(
        max_length=255,
        default="Two surveillance cameras on a dark tiled wall.",
    )
    electrical_image = models.ImageField(
        upload_to="homepage/features/",
        blank=True,
        validators=[validate_content_image],
        help_text="Optional replacement for the development electrical-services image.",
    )
    electrical_image_alt = models.CharField(
        max_length=255,
        default="A professional electrical installation.",
    )
    difference_image = models.ImageField(
        upload_to="homepage/features/",
        blank=True,
        validators=[validate_content_image],
        help_text="Optional replacement for the GRIMFLOT Difference feature image.",
    )
    difference_image_alt = models.CharField(
        max_length=255,
        default="A GRIMFLOT smart-home project.",
    )
    process_heading = models.CharField(
        max_length=180,
        default="Complexity becomes clear when the sequence is right.",
    )
    consultation_heading = models.CharField(
        max_length=180,
        default="A better brief makes a better system.",
    )
    consultation_copy = models.TextField(
        max_length=600,
        default=(
            "Bring the building, ambition, and constraints to an initial conversation. "
            "We will help you turn them into a practical next step."
        ),
    )

    class Meta(SingletonContentModel.Meta):
        verbose_name = "homepage settings"
        verbose_name_plural = "homepage settings"

    def __str__(self) -> str:
        return "Homepage settings"


class HomepageCapability(TimeStampedModel):
    """An editable homepage capability row, independent from product records."""

    title = models.CharField(max_length=120)
    summary = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "homepage capability"
        verbose_name_plural = "homepage capabilities"
        indexes = [models.Index(fields=("is_published", "order"))]

    def __str__(self) -> str:
        return self.title


class HomepageProcessStep(TimeStampedModel):
    """An editable process step for the public homepage."""

    title = models.CharField(max_length=100)
    summary = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "homepage process step"
        verbose_name_plural = "homepage process steps"
        indexes = [models.Index(fields=("is_published", "order"))]

    def __str__(self) -> str:
        return self.title


class HeroSlide(TimeStampedModel):
    """An independently ordered, publishable slide for the public homepage."""

    class FocalPoint(models.TextChoices):
        CENTER = "center center", "Centre"
        TOP = "center top", "Top"
        BOTTOM = "center bottom", "Bottom"
        LEFT = "left center", "Left"
        RIGHT = "right center", "Right"

    eyebrow = models.CharField(max_length=80)
    title = models.CharField(max_length=180)
    summary = models.TextField(max_length=600)
    background_image = models.ImageField(
        upload_to=hero_upload_path,
        validators=[validate_content_image],
    )
    image_alt = models.CharField(
        blank=True,
        max_length=255,
        help_text="Describe the slide image for visitors who cannot see it.",
    )
    mobile_image = models.ImageField(
        upload_to=hero_upload_path,
        blank=True,
        validators=[validate_content_image],
        help_text="Optional portrait-oriented crop for future mobile art direction.",
    )
    focal_point = models.CharField(
        max_length=20,
        choices=FocalPoint.choices,
        default=FocalPoint.CENTER,
    )
    primary_label = models.CharField(max_length=50)
    primary_target = models.CharField(max_length=500, validators=[validate_cta_target])
    secondary_label = models.CharField(blank=True, max_length=50)
    secondary_target = models.CharField(blank=True, max_length=500, validators=[validate_cta_target])
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        indexes = [models.Index(fields=("is_published", "order"))]

    def clean(self) -> None:
        super().clean()
        if bool(self.secondary_label) != bool(self.secondary_target):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                "A secondary call-to-action needs both a label and a destination."
            )

    def __str__(self) -> str:
        return self.title


class FAQ(TimeStampedModel):
    """Publishable questions and answers used on future public help pages."""

    question = models.CharField(max_length=255)
    answer = models.TextField(max_length=2_000)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        indexes = [models.Index(fields=("is_published", "order"))]

    def __str__(self) -> str:
        return self.question


class SEOSettings(TimeStampedModel):
    """Per-page metadata without binding SEO behaviour to individual templates."""

    page_key = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=70)
    meta_description = models.CharField(max_length=160, validators=[MaxLengthValidator(160)])
    canonical_path = models.CharField(
        max_length=255,
        blank=True,
        validators=[validate_cta_target],
        help_text="Optional on-site path such as /services/. Do not enter a domain.",
    )
    og_image = models.ImageField(
        upload_to="seo/",
        blank=True,
        validators=[validate_content_image],
    )
    no_index = models.BooleanField(default=False)

    class Meta:
        ordering = ("page_key",)
        verbose_name = "SEO settings"
        verbose_name_plural = "SEO settings"

    def clean(self) -> None:
        super().clean()
        if self.canonical_path and not self.canonical_path.startswith("/"):
            from django.core.exceptions import ValidationError

            raise ValidationError({"canonical_path": "Use an on-site path starting with '/'."})

    def __str__(self) -> str:
        return self.page_key


class SocialLink(TimeStampedModel):
    """Verified company social channels; no destination is hard-coded in templates."""

    label = models.CharField(max_length=60)
    url = models.URLField(max_length=500, validators=[validate_cta_target])
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:
        return self.label
