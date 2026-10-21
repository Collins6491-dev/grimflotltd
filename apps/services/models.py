"""Service content managed independently from commerce products."""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import safe_upload_filename, validate_content_image


def service_image_upload_path(instance: "Service", filename: str) -> str:
    """Store service imagery by stable editorial slug, not a user-supplied path."""
    return f"services/{instance.slug or slugify(instance.title)}/{safe_upload_filename(filename)}"


class Service(TimeStampedModel):
    """A professional solution offered by GRIMFLOT LTD.

    Products are modelled separately in the catalogue domain; a service can
    later be associated with products without making this content model depend
    on the commerce implementation prematurely.
    """

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True)
    short_description = models.CharField(max_length=300)
    description = models.TextField(max_length=5_000)
    hero_image = models.ImageField(
        upload_to=service_image_upload_path,
        blank=True,
        validators=[validate_content_image],
    )
    featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    meta_title = models.CharField(blank=True, max_length=70)
    meta_description = models.CharField(blank=True, max_length=160)

    class Meta:
        ordering = ("order", "title")
        indexes = [
            models.Index(fields=("is_published", "featured", "order")),
            models.Index(fields=("title",)),
        ]

    def __str__(self) -> str:
        return self.title
