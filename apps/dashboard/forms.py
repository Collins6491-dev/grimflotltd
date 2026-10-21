"""Dashboard forms keep staff updates validated and intentionally scoped."""

from django import forms
from django.contrib.auth.models import Group, Permission

from apps.catalog.models import Category, InventoryRecord, Product
from django.utils.text import slugify
from apps.core.models import (
    BrandingSettings,
    CompanyProfile,
    FAQ,
    HeroSlide,
    HomepageCapability,
    HomepageProcessStep,
    HomepageSettings,
    SocialLink,
)
from apps.projects.models import Project
from apps.services.models import Service
from apps.accounts.models import User


class StaffCreateForm(forms.ModelForm):
    """Create a staff account without ever collecting a reusable password."""

    role = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role", "is_active")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def limit_roles(self, *, can_manage_privileged: bool):
        """Prevent unauthorized staff from assigning privileged roles."""
        if not can_manage_privileged:
            self.fields["role"].queryset = (
                self.fields["role"]
                .queryset
                .exclude(
                    permissions__codename__in=(
                        "manage_staff",
                        "manage_roles",
                    )
                )
                .distinct()
            )


class StaffEditForm(StaffCreateForm):
    class Meta(StaffCreateForm.Meta):
        fields = ("first_name", "last_name", "email", "role", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["role"].initial = (
                self.instance.groups.order_by("name").first()
            )


class RoleForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related(
            "content_type"
        ).order_by(
            "content_type__app_label",
            "codename",
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ("name", "permissions")


class ProductDashboardForm(forms.ModelForm):
    """Validate product details and accept an optional primary image upload."""

    image = forms.ImageField(
        required=False,
        label="Product Image",
        help_text="Upload the main product image. Maximum file size: 5 MB.",
    )

    class Meta:
        model = Product
        fields = (
            "category",
            "name",
            "slug",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "currency",
            "installation_available",
            "is_featured",
            "is_published",
            "meta_title",
            "meta_description",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
        }
        help_texts = {
            "category": "Products appear publicly only when both this product and its category are published.",
            "is_published": "Published products can appear in the public catalogue when their category is also published.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].label_from_instance = lambda category: (
            f"{category.name} ({'Published' if category.is_published else 'Draft'})"
        )

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                "The image must not exceed 5 MB."
            )

        return image


class InventoryDashboardForm(forms.ModelForm):
    class Meta:
        model = InventoryRecord
        fields = (
            "quantity_on_hand",
            "reorder_level",
            "allow_backorder",
        )


class CategoryDashboardForm(forms.ModelForm):
    """Keep category publishing and image validation in the dashboard workflow."""

    slug = forms.SlugField(required=False, help_text="Leave blank to generate this from the category name.")

    class Meta:
        model = Category
        fields = ("name", "slug", "description", "image", "image_alt", "order", "is_published")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def clean_slug(self):
        return self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""))


class ServiceDashboardForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={"rows": 8}),
        }


class ProjectDashboardForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"
        widgets = {
            "narrative": forms.Textarea(attrs={"rows": 8}),
            "completed_on": forms.DateInput(
                attrs={"type": "date"}
            ),
        }


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        exclude = ("site_id",)
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "business_hours": forms.Textarea(attrs={"rows": 3}),
        }


class BrandingSettingsForm(forms.ModelForm):
    class Meta:
        model = BrandingSettings
        exclude = ("site_id",)


class HomepageSettingsForm(forms.ModelForm):
    class Meta:
        model = HomepageSettings
        exclude = ("site_id",)
        labels = {
            "energy_image": "Energy card image",
            "energy_image_alt": "Energy card image alt text",
            "smart_image": "Smart technology card image",
            "smart_image_alt": "Smart technology card image alt text",
            "security_image": "Security card image",
            "security_image_alt": "Security card image alt text",
            "electrical_image": "Electrical services card image",
            "electrical_image_alt": "Electrical services card image alt text",
            "difference_image": "GRIMFLOT Difference feature image",
            "difference_image_alt": "GRIMFLOT Difference feature image alt text",
        }
        widgets = {
            "solutions_intro": forms.Textarea(attrs={"rows": 3}),
            "energy_copy": forms.Textarea(attrs={"rows": 4}),
            "security_copy": forms.Textarea(attrs={"rows": 4}),
            "consultation_copy": forms.Textarea(attrs={"rows": 4}),
        }


class HeroSlideDashboardForm(forms.ModelForm):
    class Meta:
        model = HeroSlide
        exclude = ("created_at", "updated_at")
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
        }


class FAQDashboardForm(forms.ModelForm):
    class Meta:
        model = FAQ
        exclude = ("created_at", "updated_at")
        widgets = {
            "answer": forms.Textarea(attrs={"rows": 5}),
        }


class HomepageCapabilityDashboardForm(forms.ModelForm):
    class Meta:
        model = HomepageCapability
        exclude = ("created_at", "updated_at")
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
        }


class HomepageProcessStepDashboardForm(forms.ModelForm):
    class Meta:
        model = HomepageProcessStep
        exclude = ("created_at", "updated_at")
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
        }


class SocialLinkDashboardForm(forms.ModelForm):
    class Meta:
        model = SocialLink
        exclude = ("created_at", "updated_at")
