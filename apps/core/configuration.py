"""Configuration for shared public-site and operational functionality."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Register the shared GRIMFLOT platform app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"
