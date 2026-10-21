"""Public, factual portfolio views; drafts never appear publicly."""

from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import GalleryItem, Project


@require_GET
def project_list(request):
    projects = Project.objects.filter(is_published=True).prefetch_related("related_services")
    return render(request, "projects/project_list.html", {"projects": projects, "page_title": "Projects"})


@require_GET
def project_detail(request, slug: str):
    project = get_object_or_404(Project.objects.prefetch_related("images", "related_services"), slug=slug, is_published=True)
    return render(request, "projects/project_detail.html", {"project": project, "page_title": project.meta_title or project.title, "meta_description": project.meta_description or project.excerpt})


@require_GET
def gallery(request):
    items = GalleryItem.objects.filter(is_published=True).select_related("project")
    return render(request, "projects/gallery.html", {"items": items, "page_title": "Gallery"})
