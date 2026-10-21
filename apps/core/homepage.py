"""Temporary editorial data and a stable contract for the public homepage.

Stage 3 deliberately keeps demonstration content outside the template. Stage 4
will replace this adapter with validated, database-backed CMS records without
forcing a redesign of the presentation layer.
"""

from __future__ import annotations

from django.db.utils import OperationalError, ProgrammingError
from django.templatetags.static import static

from .models import (
    FAQ,
    SEOSettings,
    HeroSlide,
    HomepageCapability,
    HomepageProcessStep,
    HomepageSettings,
)


def _fallback_homepage_context() -> dict[str, object]:
    """Return clearly identified content when an editor has not saved CMS data yet."""
    return {
        "homepage": HomepageSettings(),
        "hero_slides": (
            {
                "eyebrow": "Connected living",
                "title": "A home that understands its rhythm.",
                "summary": "Thoughtful automation, security, energy, and electrical systems should feel effortless from the first switch-on.",
                "primary_label": "Explore our approach",
                "primary_target": "#solutions",
                "secondary_label": "How we work",
                "secondary_target": "#delivery",
                "image": static("images/hero/smart-home-hero.jpg"),
                "alt": "A contemporary illuminated home at blue hour.",
                "position": "center 56%",
            },
            {
                "eyebrow": "Energy resilience",
                "title": "Power designed for the moments that matter.",
                "summary": "Solar, storage, and backup power can be planned as one calm, coherent system rather than a collection of compromises.",
                "primary_label": "See energy systems",
                "primary_target": "#energy",
                "secondary_label": "Our process",
                "secondary_target": "#delivery",
                "image": static("images/services/smart-home.jpg"),
                "alt": "A technician positioning a solar panel during installation.",
                "position": "center 55%",
            },
            {
                "eyebrow": "Security by design",
                "title": "Protection that stays quietly ahead.",
                "summary": "Surveillance, access, and network foundations are considered together, so every connection has a clear purpose.",
                "primary_label": "Discover protection",
                "primary_target": "#security",
                "secondary_label": "Plan a project",
                "secondary_target": "#consultation",
                "image": static("images/services/cctv-security.jpg"),
                "alt": "Two security cameras mounted against a dark architectural wall.",
                "position": "center 48%",
            },
        ),
        "solutions": (
            {"number": "01", "title": "Smart environments", "summary": "Lighting, access, comfort, and control designed around the way a space is actually used."},
            {"number": "02", "title": "Resilient energy", "summary": "Solar, battery, and inverter systems planned for clarity, continuity, and informed expansion."},
            {"number": "03", "title": "Security & access", "summary": "CCTV, smart locks, and perimeter systems arranged as a connected layer of confidence."},
            {"number": "04", "title": "Infrastructure & sound", "summary": "Networking, Starlink, electrical installations, and sound systems that make the invisible dependable."},
        ),
        "delivery_steps": (
            ("01", "Listen", "We start with the way the people, building, and ambition fit together."),
            ("02", "Design", "We turn the brief into a joined-up technical plan with room to grow."),
            ("03", "Deliver", "Installation is sequenced with care, then handed over with the system made clear."),
        ),
        "faqs": (
            ("Can a project combine products and installation?", "Yes. We can plan a supplied product and professional installation as one considered scope."),
            ("Can an existing property be upgraded?", "Many systems can be introduced in phases. Book a consultation so we can understand the property context before making recommendations."),
            ("Can I purchase products online?", "Yes. Browse available products, add them to your cart, and continue through a secure checkout once your account email is verified."),
        ),
    }


def _hero_slide_context(slide: HeroSlide) -> dict[str, str]:
    """Map an editor-managed slide to the small, template-facing slide contract."""
    return {
        "eyebrow": slide.eyebrow,
        "title": slide.title,
        "summary": slide.summary,
        "primary_label": slide.primary_label,
        "primary_target": slide.primary_target,
        "secondary_label": slide.secondary_label,
        "secondary_target": slide.secondary_target,
        "image": slide.background_image.url,
        "mobile_image": slide.mobile_image.url if slide.mobile_image else "",
        "alt": slide.image_alt or slide.title,
        "position": slide.focal_point,
    }


def get_homepage_context() -> dict[str, object]:
    """Return saved homepage content, falling back safely before CMS setup.

    The migration guard allows the existing Stage 3 public page to render during
    a deploy before migrations are run, while normal deployed requests always
    use saved records when they are published.
    """
    context = _fallback_homepage_context()

    try:
        settings = HomepageSettings.get_solo()
        slides = list(
            HeroSlide.objects.filter(is_published=True)
            .exclude(background_image="")
            .order_by("order", "id")
        )
        capabilities = list(
            HomepageCapability.objects.filter(is_published=True).order_by("order", "id")
        )
        process_steps = list(
            HomepageProcessStep.objects.filter(is_published=True).order_by("order", "id")
        )
        faqs = list(FAQ.objects.filter(is_published=True).order_by("order", "id"))
        seo = SEOSettings.objects.filter(page_key="home").first()
    except (OperationalError, ProgrammingError):
        return context

    context["homepage"] = settings
    if slides:
        context["hero_slides"] = tuple(_hero_slide_context(slide) for slide in slides)
    if capabilities:
        context["solutions"] = tuple(
            {
                "number": f"{index:02d}",
                "title": capability.title,
                "summary": capability.summary,
            }
            for index, capability in enumerate(capabilities, start=1)
        )
    if process_steps:
        context["delivery_steps"] = tuple(
            (f"{index:02d}", step.title, step.summary)
            for index, step in enumerate(process_steps, start=1)
        )
    if faqs:
        context["faqs"] = tuple((faq.question, faq.answer) for faq in faqs)
    if seo:
        context["page_title"] = seo.title
        context["meta_description"] = seo.meta_description
        context["canonical_path"] = seo.canonical_path
        context["og_image"] = seo.og_image.url if seo.og_image else ""
    return context
