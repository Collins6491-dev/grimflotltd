"""Validated GET parameters for public catalogue discovery."""

from __future__ import annotations

from django import forms

from .models import Category


class CatalogueFilterForm(forms.Form):
    """Keep catalogue filtering predictable and safely bounded."""

    SORT_FEATURED = "featured"
    SORT_NAME = "name"
    SORT_PRICE_ASC = "price_asc"
    SORT_PRICE_DESC = "price_desc"

    SORT_CHOICES = (
        (SORT_FEATURED, "Featured first"),
        (SORT_NAME, "Name, A–Z"),
        (SORT_PRICE_ASC, "Price, low to high"),
        (SORT_PRICE_DESC, "Price, high to low"),
    )

    q = forms.CharField(required=False, max_length=100)
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    min_price = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
    max_price = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
    availability = forms.BooleanField(required=False)
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, initial=SORT_FEATURED)

    def __init__(self, *args, categories=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = categories or Category.objects.none()

    def clean_q(self) -> str:
        """Normalise whitespace while preserving an ordinary phrase search."""
        return " ".join(self.cleaned_data["q"].split())

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get("min_price")
        maximum = cleaned_data.get("max_price")
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error("max_price", "Maximum price must not be lower than minimum price.")
        return cleaned_data
