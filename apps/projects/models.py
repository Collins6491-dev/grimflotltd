"""Project, project-image, and gallery content models."""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import safe_upload_filename, validate_content_image


def project_image_upload_path(instance: models.Model, filename: str) -> str:
    """Group project and gallery assets below a controlled storage prefix."""
    project_slug = getattr(instance, "project_slug", "gallery")
    if hasattr(instance, "project") and instance.project_id:
        project_slug = instance.project.slug
    elif hasattr(instance, "slug"):
        project_slug = instance.slug
    return f"projects/{project_slug}/{safe_upload_filename(filename)}"


class Project(TimeStampedModel):
    """A publishable case study. No case studies are seeded as factual claims."""

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=190, unique=True)
    excerpt = models.CharField(max_length=350)
    narrative = models.TextField(max_length=8_000)
    client_type = models.CharField(blank=True, max_length=120)
    location_label = models.CharField(blank=True, max_length=180)
    completed_on = models.DateField(blank=True, null=True)
    cover_image = models.ImageField(
        upload_to=project_image_upload_path,
        blank=True,
        validators=[validate_content_image],
    )
    related_services = models.ManyToManyField(
        "services.Service",
        blank=True,
        related_name="projects",
    )
    featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    meta_title = models.CharField(blank=True, max_length=70)
    meta_description = models.CharField(blank=True, max_length=160)

    class Meta:
        ordering = ("order", "-completed_on", "title")
        indexes = [
            models.Index(fields=("is_published", "featured", "order")),
            models.Index(fields=("completed_on",)),
        ]

    def __str__(self) -> str:
        return self.title


class ProjectImage(TimeStampedModel):
    """Additional project visual with descriptive alternative text."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=project_image_upload_path, validators=[validate_content_image])
    alt_text = models.CharField(max_length=255)
    caption = models.CharField(blank=True, max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.project}: image {self.order}"


class GalleryItem(TimeStampedModel):
    """Standalone gallery media, optionally connected to a public project."""

    project = models.ForeignKey(
        Project,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="gallery_items",
    )
    image = models.ImageField(upload_to=project_image_upload_path, validators=[validate_content_image])
    alt_text = models.CharField(max_length=255)
    caption = models.CharField(blank=True, max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "gallery item"
        verbose_name_plural = "gallery items"
        indexes = [models.Index(fields=("is_published", "order"))]

    def __str__(self) -> str:
        return self.caption or self.alt_text
