"""Public enquiry forms with explicit consent."""

from django import forms

from .models import Enquiry


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ("name", "email", "phone", "organisation", "service_interest", "message", "consent_to_contact")
        widgets = {"message": forms.Textarea(attrs={"rows": 6})}

    def clean_consent_to_contact(self):
        if not self.cleaned_data["consent_to_contact"]:
            raise forms.ValidationError("Please confirm that GRIMFLOT LTD may respond to this request.")
        return True
