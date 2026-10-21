"""Validated customer-facing account forms."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import CustomerProfile, User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField()
    marketing_opt_in = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ("email", "password1", "password2", "marketing_opt_in")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_email_verified = False
        if commit:
            user.save()
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={"marketing_opt_in": self.cleaned_data["marketing_opt_in"]},
            )
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


class StaffAuthenticationForm(EmailAuthenticationForm):
    """Authenticate only staff users for the private operations dashboard."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise ValidationError(
                "This account does not have access to the operations dashboard.",
                code="not_staff",
            )


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = CustomerProfile
        fields = ("phone", "marketing_opt_in")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            self.user.save(update_fields=("first_name", "last_name"))
            profile.save()
        return profile
