from django import forms


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99, initial=1)
    next = forms.CharField(required=False, widget=forms.HiddenInput)


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)
