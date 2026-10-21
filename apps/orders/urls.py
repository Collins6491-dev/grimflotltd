"""Customer order and checkout routes."""

from django.urls import path

from . import views


app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<str:reference>/", views.order_confirmation, name="confirmation"),
    path("", views.order_list, name="list"),
    path("<str:reference>/", views.order_detail, name="detail"),
    path("<str:reference>/pay/", views.begin_payment, name="begin-payment"),
]
