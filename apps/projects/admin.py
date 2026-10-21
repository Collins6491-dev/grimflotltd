"""Restricted maintenance interface for portfolio and gallery content."""

from django.contrib import admin

from .models import GalleryItem, Project, ProjectImage


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 0
    fields = ("image", "alt_text", "caption", "order")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "featured", "completed_on", "order")
    list_filter = ("is_published", "featured", "related_services")
    search_fields = ("title", "excerpt", "narrative", "location_label", "client_type")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("related_services",)
    inlines = (ProjectImageInline,)
    fieldsets = (
        ("Case study", {"fields": ("title", "slug", "excerpt", "narrative")}),
        ("Context", {"fields": ("client_type", "location_label", "completed_on", "related_services")}),
        ("Media and publishing", {"fields": ("cover_image", "is_published", "featured", "order")}),
        ("Search metadata", {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
    )


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("alt_text", "project", "is_published", "order", "updated_at")
    list_filter = ("is_published", "project")
    search_fields = ("alt_text", "caption")
    autocomplete_fields = ("project",)
    ordering = ("order", "id")
