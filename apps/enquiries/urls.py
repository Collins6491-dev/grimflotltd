"""Public contact and quotation routes."""

from django.urls import path

from . import views


app_name = "enquiries"

urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("quote/", views.quote_request, name="quote"),
]
