"""Provider callback and webhook routes."""

from django.urls import path

from . import views


app_name = "payments"

urlpatterns = [
    path("callback/", views.payment_callback, name="callback"),
    path("webhooks/paystack/", views.paystack_webhook, name="paystack-webhook"),
]
