from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/<slug:slug>/", views.add_to_cart, name="add"),
    path("item/<int:item_id>/", views.update_item, name="update"),
]
