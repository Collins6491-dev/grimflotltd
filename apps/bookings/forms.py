"""Validated consultation request form."""

from django import forms
from django.utils import timezone

from .models import ConsultationBooking


class ConsultationBookingForm(forms.ModelForm):
    class Meta:
        model = ConsultationBooking
        fields = ("name", "email", "phone", "requested_for", "service_interest", "property_type", "notes")
        widgets = {
            "requested_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_requested_for(self):
        requested_for = self.cleaned_data["requested_for"]
        if requested_for <= timezone.now():
            raise forms.ValidationError("Choose a future consultation time.")
        return requested_for
