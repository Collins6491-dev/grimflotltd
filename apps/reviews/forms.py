"""Customer review form kept intentionally small and moderation-first."""

from django import forms

from .models import ProductReview


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ("rating", "title", "body")
        widgets = {
            "rating": forms.Select(choices=tuple((rating, f"{rating} out of 5") for rating in range(1, 6))),
            "body": forms.Textarea(attrs={"rows": 5}),
        }

