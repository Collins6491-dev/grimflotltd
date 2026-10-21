"""Restricted maintenance interface for verified testimonials."""

from django.contrib import admin

from .models import ProductReview, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("person_name", "role_or_company", "is_demonstration", "is_published", "order")
    list_filter = ("is_published", "is_demonstration")
    search_fields = ("person_name", "role_or_company", "quote", "source_reference")
    ordering = ("order", "id")
    fieldsets = (
        ("Testimonial", {"fields": ("person_name", "role_or_company", "quote")}),
        ("Verification", {"fields": ("source_reference", "is_demonstration")}),
        ("Publishing", {"fields": ("is_published", "order")}),
    )


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "created_at")
    list_filter = ("status", "rating")
    search_fields = ("product__name", "user__email", "title", "body")
    list_select_related = ("product", "user")
