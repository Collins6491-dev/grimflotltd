"""Validated checkout and staff-safe order update forms."""

from django import forms

from .models import DeliveryAddress, Order


class CheckoutForm(forms.Form):
    """Capture the delivery snapshot used to create an immutable order."""

    recipient_name = forms.CharField(max_length=160)
    recipient_phone = forms.CharField(max_length=40)
    address_line_1 = forms.CharField(max_length=255, label="Address")
    address_line_2 = forms.CharField(max_length=255, required=False, label="Address line 2")
    city = forms.CharField(max_length=120)
    state = forms.CharField(max_length=120, label="State")
    country = forms.CharField(max_length=2, initial="NG")
    customer_note = forms.CharField(max_length=1500, required=False, widget=forms.Textarea)
    save_address = forms.BooleanField(required=False)

    def clean_country(self):
        return self.cleaned_data["country"].strip().upper()

    @classmethod
    def from_address(cls, address: DeliveryAddress):
        """Populate a checkout form from a customer's selected saved address."""
        return cls(
            initial={
                "recipient_name": address.recipient_name,
                "recipient_phone": address.phone,
                "address_line_1": address.address_line_1,
                "address_line_2": address.address_line_2,
                "city": address.city,
                "state": address.state,
                "country": address.country,
            }
        )


class OrderStatusForm(forms.Form):
    """Constrain staff updates to the published order lifecycle."""

    status = forms.ChoiceField(choices=Order.STATUS_CHOICES)
    note = forms.CharField(required=False, max_length=500, widget=forms.Textarea)
