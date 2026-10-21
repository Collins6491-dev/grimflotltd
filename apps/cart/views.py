"""Safe, server-side cart mutations."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from apps.catalog.models import Product

from .forms import AddToCartForm, CartQuantityForm
from .services import CartError, add_product, get_cart, set_item_quantity, totals


def _next(request, fallback):
    candidate = request.POST.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}):
        return candidate
    return fallback


@require_GET
def cart_detail(request):
    cart = get_cart(request, create=False)
    items = cart.items.select_related("product__category").prefetch_related("product__images") if cart else []
    return render(
        request,
        "cart/detail.html",
        {"cart": cart, "items": items, "cart_totals": totals(cart) if cart else None, "page_title": "Your cart"},
    )


@require_POST
def add_to_cart(request, slug: str):
    product = get_object_or_404(Product.objects.select_related("category", "inventory"), slug=slug)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a valid quantity before adding this product.")
        return redirect(product.get_absolute_url())
    try:
        add_product(cart=get_cart(request), product=product, quantity=form.cleaned_data["quantity"])
    except CartError as error:
        messages.error(request, str(error))
        return redirect(product.get_absolute_url())
    messages.success(request, f"{product.name} was added to your cart.")
    return redirect(_next(request, "cart:detail"))


@require_POST
def update_item(request, item_id: int):
    cart = get_cart(request, create=False)
    if not cart:
        messages.error(request, "Your cart is no longer available.")
        return redirect("cart:detail")
    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Choose a quantity from 0 to 99.")
        return redirect("cart:detail")
    try:
        item = set_item_quantity(cart=cart, item_id=item_id, quantity=form.cleaned_data["quantity"])
    except CartError as error:
        messages.error(request, str(error))
    else:
        messages.info(request, "Item removed from your cart." if item is None else "Cart quantity updated.")
    return redirect("cart:detail")
