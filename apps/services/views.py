"""Public views for curated technical services."""

from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Service


@require_GET
def service_list(request):
    services = Service.objects.filter(is_published=True)
    return render(request, "services/service_list.html", {"services": services, "page_title": "Technical services"})


@require_GET
def service_detail(request, slug: str):
    service = get_object_or_404(Service, slug=slug, is_published=True)
    return render(
        request,
        "services/service_detail.html",
        {"service": service, "page_title": service.meta_title or service.title, "meta_description": service.meta_description or service.short_description},
    )
