"""URLs owned by the shared public-site foundation."""

from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("solar-estimator/", views.solar_estimator, name="solar-estimator"),
    path("privacy/", views.policy, {"policy_key": "privacy"}, name="privacy"),
    path("terms/", views.policy, {"policy_key": "terms"}, name="terms"),
    path("shipping-delivery/", views.policy, {"policy_key": "shipping"}, name="shipping"),
    path("returns-refunds/", views.policy, {"policy_key": "returns"}, name="returns"),
]
