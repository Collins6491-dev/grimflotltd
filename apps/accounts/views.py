"""Customer account, verification, and wishlist endpoints."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.models import Product
from apps.core.security import rate_limit

from .forms import CustomerProfileForm, EmailAuthenticationForm, RegistrationForm
from .models import CustomerProfile, User, WishlistItem
from .services import VERIFY_SALT, send_verification_email


def _safe_next(request, fallback: str) -> str:
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}):
        return candidate
    return fallback


@rate_limit("registration", limit=6, window=900)
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        try:
            send_verification_email(user=user, request=request)
        except Exception:
            # The account is still safe and explicitly unverified; staff can
            # resend later rather than pretending delivery succeeded.
            messages.warning(request, "Your account was created, but we could not send the verification email yet.")
        login(request, user)
        return redirect("accounts:verification-sent")
    return render(request, "accounts/register.html", {"form": form, "page_title": "Create your account"})


@rate_limit("login", limit=10, window=900)
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")
    form = EmailAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next(request, "accounts:account"))
    return render(request, "accounts/login.html", {"form": form, "page_title": "Sign in"})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("home")


@login_required
@require_GET
def verification_sent(request):
    return render(request, "accounts/verification_sent.html", {"page_title": "Verify your email"})


@require_GET
def verify_email(request, token: str):
    try:
        payload = signing.loads(token, salt=VERIFY_SALT, max_age=48 * 60 * 60)
        user = User.objects.get(pk=payload["user_id"], email=payload["email"])
    except (signing.BadSignature, User.DoesNotExist, KeyError):
        raise Http404("This verification link is invalid or has expired.")
    user.is_email_verified = True
    user.save(update_fields=("is_email_verified",))
    messages.success(request, "Your email address has been verified. You can now continue to checkout.")
    return redirect("accounts:account" if request.user.is_authenticated else "accounts:login")


@login_required
@require_http_methods(["GET", "POST"])
def account(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    form = CustomerProfileForm(request.POST or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your account details have been updated.")
        return redirect("accounts:account")
    recent_orders = request.user.orders.prefetch_related("items").order_by("-created_at")[:5]
    return render(
        request,
        "accounts/account.html",
        {"form": form, "recent_orders": recent_orders, "page_title": "Your account"},
    )


@login_required
@require_GET
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related("product__category").prefetch_related("product__images")
    return render(request, "accounts/wishlist.html", {"items": items, "page_title": "Saved products"})


@login_required
@require_POST
def toggle_wishlist(request, slug: str):
    product = get_object_or_404(Product, slug=slug, is_published=True, category__is_published=True)
    try:
        item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    except IntegrityError:
        created = False
        item = WishlistItem.objects.get(user=request.user, product=product)
    if created:
        messages.success(request, f"{product.name} was saved to your wishlist.")
    else:
        item.delete()
        messages.info(request, f"{product.name} was removed from your wishlist.")
    return redirect(_safe_next(request, product.get_absolute_url()))
