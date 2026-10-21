"""Small, safe template context shared by public and error pages."""

from __future__ import annotations

from django.db.utils import OperationalError, ProgrammingError

from .models import BrandingSettings, CompanyProfile, SocialLink


def site_identity(request):
    """Expose saved company and brand records without failing before migrations."""
    try:
        company = CompanyProfile.get_solo()
        branding = BrandingSettings.get_solo()
        social_links = tuple(
            SocialLink.objects.filter(is_published=True).only("label", "url").order_by("order", "id")
        )
    except (OperationalError, ProgrammingError):
        company = CompanyProfile()
        branding = BrandingSettings()
        social_links = ()

    return {
        "site_company": company,
        "site_branding": branding,
        "site_social_links": social_links,
        "cart_item_count": _cart_item_count(request),
    }


def _cart_item_count(request) -> int:
    """Display a cart count without provisioning a cart for every visitor."""
    try:
        from apps.cart.models import Cart

        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).prefetch_related("items").first()
        elif request.session.session_key:
            cart = Cart.objects.filter(user__isnull=True, session_key=request.session.session_key).prefetch_related("items").first()
        else:
            cart = None
        return cart.item_count if cart else 0
    except (OperationalError, ProgrammingError):
        return 0
