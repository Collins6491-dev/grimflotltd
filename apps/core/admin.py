"""Restricted maintenance interface for shared company and editorial content."""

from django.contrib import admin

from .models import (
    BrandingSettings,
    CompanyProfile,
    FAQ,
    HeroSlide,
    HomepageCapability,
    HomepageProcessStep,
    HomepageSettings,
    SEOSettings,
    SocialLink,
)


class SingletonAdmin(admin.ModelAdmin):
    """Allow staff to edit a singleton settings record without creating duplicates."""

    def has_add_permission(self, request):
        return not self.model.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompanyProfile)
class CompanyProfileAdmin(SingletonAdmin):
    fieldsets = (
        ("Identity", {"fields": ("name", "tagline", "description")}),
        ("Contact", {"fields": ("email", "phone", "secondary_phone", "whatsapp_number")}),
        ("Service information", {"fields": ("address", "service_area", "business_hours")}),
    )


@admin.register(BrandingSettings)
class BrandingSettingsAdmin(SingletonAdmin):
    fieldsets = (
        ("Brand assets", {"fields": ("logo", "favicon")}),
        ("Brand colours", {"fields": ("primary_colour", "secondary_colour", "ink_colour")}),
    )


@admin.register(HomepageSettings)
class HomepageSettingsAdmin(SingletonAdmin):
    fieldsets = (
        ("Solutions", {"fields": ("solutions_eyebrow", "solutions_heading", "solutions_intro")}),
        (
            "Energy",
            {"fields": ("energy_eyebrow", "energy_heading", "energy_copy", "energy_image", "energy_image_alt")},
        ),
        (
            "Security",
            {"fields": ("security_eyebrow", "security_heading", "security_copy", "security_image", "security_image_alt")},
        ),
        ("Calls to action", {"fields": ("process_heading", "consultation_heading", "consultation_copy")}),
    )


@admin.register(HomepageCapability)
class HomepageCapabilityAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "order", "updated_at")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("title", "summary")
    ordering = ("order", "id")


@admin.register(HomepageProcessStep)
class HomepageProcessStepAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "order", "updated_at")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("title", "summary")
    ordering = ("order", "id")


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "order", "updated_at")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("title", "eyebrow", "summary")
    ordering = ("order", "id")
    fieldsets = (
        ("Slide copy", {"fields": ("eyebrow", "title", "summary")}),
        ("Media", {"fields": ("background_image", "image_alt", "mobile_image", "focal_point")}),
        ("Primary call to action", {"fields": ("primary_label", "primary_target")}),
        ("Secondary call to action", {"fields": ("secondary_label", "secondary_target")}),
        ("Publishing", {"fields": ("is_published", "order")}),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "is_published", "order", "updated_at")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("question", "answer")
    ordering = ("order", "id")


@admin.register(SEOSettings)
class SEOSettingsAdmin(admin.ModelAdmin):
    list_display = ("page_key", "title", "no_index", "updated_at")
    search_fields = ("page_key", "title", "meta_description")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("label", "url")
    ordering = ("order", "id")
