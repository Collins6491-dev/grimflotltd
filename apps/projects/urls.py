"""Public portfolio and gallery routes."""

from django.urls import path

from . import views


app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("gallery/", views.gallery, name="gallery"),
    path("<slug:slug>/", views.project_detail, name="detail"),
]
