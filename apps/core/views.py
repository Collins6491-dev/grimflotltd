"""Shared public-site and operational views."""

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.catalog.selectors import published_products
from apps.projects.models import Project
from apps.reviews.models import Testimonial
from apps.services.models import Service

from .forms import SolarEstimatorForm
from .homepage import get_homepage_context
from .models import FAQ


@require_GET
def health_check(request):
    """Return only liveness information; never disclose configuration or data."""
    return JsonResponse({"status": "ok"})


def home(request):
    """Render the Stage 3 editorial homepage from its content adapter."""
    context = get_homepage_context()
    context.setdefault("page_title", "Smart technology, energy & electrical solutions")
    context.setdefault(
        "meta_description",
        (
            "GRIMFLOT LTD delivers thoughtfully engineered smart technology, "
            "energy, security, and electrical solutions."
        ),
    )
    canonical_path = context.pop("canonical_path", "")
    if canonical_path:
        context["canonical_url"] = request.build_absolute_uri(canonical_path)
    context.update(
        {
            "featured_services": Service.objects.filter(is_published=True, featured=True)[:4],
            "featured_products": published_products().filter(is_featured=True)[:4],
            "featured_projects": Project.objects.filter(is_published=True, featured=True).prefetch_related(
                "related_services"
            )[:3],
            # Testimonials never appear unless an editor has explicitly approved them.
            "testimonials": Testimonial.objects.filter(is_published=True)[:3],
        }
    )
    return render(
        request,
        "public/home_stage3.html",
        context,
    )


@require_GET
def about(request):
    """Explain the company using managed company and service records."""
    return render(
        request,
        "public/about.html",
        {
            "services": Service.objects.filter(is_published=True)[:6],
            "projects": Project.objects.filter(is_published=True, featured=True)[:3],
            "page_title": "About GRIMFLOT LTD",
            "meta_description": "Learn how GRIMFLOT LTD plans and delivers connected technology, energy, security, and electrical systems.",
        },
    )


@require_GET
def faq(request):
    return render(request, "public/faq.html", {"faqs": FAQ.objects.filter(is_published=True), "page_title": "Frequently asked questions"})


def solar_estimator(request):
    """Provide an indicative solar conversation starter, never a binding quote."""
    form = SolarEstimatorForm(request.POST or None)
    estimate = form.recommendation() if request.method == "POST" and form.is_valid() else None
    return render(request, "public/solar_estimator.html", {"form": form, "estimate": estimate, "page_title": "Solar estimator"})


@require_GET
def policy(request, policy_key: str):
    """Keep policy routes explicit and concise until the business approves final legal copy."""
    policies = {
        "privacy": (
            "Privacy policy", "How we use information you give us",
            [("Information we collect", "We collect contact, account, order, and enquiry details needed to respond to you, provide products and services, and meet our legal obligations."), ("How we use it", "We use your information to fulfil requests, process orders, arrange installation or consultation, provide support, and improve the services you request."), ("Your choices", "You may ask us to update your account details or withdraw marketing consent. Service, payment, and legal records may be retained where required.")],
        ),
        "terms": (
            "Terms and conditions", "Terms for using the GRIMFLOT LTD platform",
            [("Quotes and specifications", "Technical recommendations and quotations are subject to site assessment, final scope, availability, and written acceptance."), ("Orders", "An order is confirmed only after a verified payment and an order acknowledgement. Product availability may change before payment is verified."), ("Installation", "Installation dates and works are agreed after the property, access, safety requirements, and scope have been reviewed.")],
        ),
        "shipping": (
            "Shipping and delivery", "Delivery planning for technology equipment",
            [("Delivery confirmation", "Delivery timing and charges are confirmed during the order process or by our team for installation-led purchases."), ("Inspection", "Please inspect deliveries promptly and report missing, damaged, or incorrect items using the contact details in your order confirmation."), ("Installation goods", "Equipment ordered with installation may be scheduled to align with the agreed site programme.")],
        ),
        "returns": (
            "Returns and refunds", "How to request a product return or order review",
            [("Before returning", "Contact GRIMFLOT LTD with the order reference and a description of the issue so we can confirm the appropriate next step."), ("Eligibility", "Return eligibility depends on product condition, supplier requirements, configuration, and whether a product has been installed or specially ordered."), ("Refunds", "Approved refunds are issued to the original payment method after the relevant product or service review is complete.")],
        ),
    }
    title, intro, sections = policies[policy_key]
    return render(request, "public/policy.html", {"page_title": title, "intro": intro, "sections": sections})


def error_400(request, exception=None):
    """Render a consistent, safe response for malformed requests."""
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    """Render a consistent response for forbidden requests."""
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    """Render a consistent response for missing public pages."""
    return render(request, "errors/404.html", status=404)


def error_500(request):
    """Render a non-disclosing response for unexpected server errors."""
    return render(request, "errors/500.html", status=500)
