"""Restricted maintenance interface for service content before Stage 9."""

from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "featured", "order", "updated_at")
    list_filter = ("is_published", "featured")
    search_fields = ("title", "short_description", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "title")
    fieldsets = (
        ("Service", {"fields": ("title", "slug", "short_description", "description")}),
        ("Media", {"fields": ("hero_image",)}),
        ("Publishing", {"fields": ("is_published", "featured", "order")}),
        ("Search metadata", {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
    )
