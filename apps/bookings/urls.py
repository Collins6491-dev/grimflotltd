"""Public consultation scheduling route."""

from django.urls import path

from . import views


app_name = "bookings"

urlpatterns = [path("consultation/", views.consultation, name="consultation")]
