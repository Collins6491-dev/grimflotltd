"""Cart mutations centralised away from HTTP views."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Product

from .models import Cart, CartItem


class CartError(Exception):
    """A safe, customer-facing cart mutation failure."""


@dataclass(frozen=True)
class CartTotals:
    subtotal: Decimal
    item_count: int


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_cart(request, *, create: bool = True) -> Cart | None:
    """Get the visitor's cart and merge a pre-login guest cart once signed in."""
    # Merely rendering a cart count must not create a session, cart, or cookie.
    if not create and not request.session.session_key:
        return Cart.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    session_key = _session_key(request)
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"session_key": session_key})
        guest_cart = Cart.objects.filter(user__isnull=True, session_key=session_key).first()
        if guest_cart and guest_cart.pk != cart.pk:
            _merge_carts(destination=cart, source=guest_cart)
        return cart
    if not create:
        return Cart.objects.filter(user__isnull=True, session_key=session_key).first()
    return Cart.objects.get_or_create(user=None, session_key=session_key)[0]


@transaction.atomic
def _merge_carts(*, destination: Cart, source: Cart) -> None:
    """Combine quantities without losing a guest's selections after login."""
    for source_item in source.items.select_for_update().select_related("product"):
        item, created = CartItem.objects.select_for_update().get_or_create(
            cart=destination,
            product=source_item.product,
            defaults={"quantity": source_item.quantity},
        )
        if not created:
            item.quantity += source_item.quantity
            item.save(update_fields=("quantity", "updated_at"))
    source.delete()


@transaction.atomic
def add_product(*, cart: Cart, product: Product, quantity: int) -> CartItem:
    """Add a public product using the current availability rules."""
    if quantity < 1:
        raise CartError("Choose a quantity of at least one.")
    if not product.is_published or not product.category.is_published:
        raise CartError("This product is no longer available.")
    if not product.is_available_for_sale:
        raise CartError("This product is currently unavailable.")
    item, created = CartItem.objects.select_for_update().get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
    if item.quantity > 99:
        raise CartError("Choose no more than 99 units in one cart line.")
    try:
        inventory = product.inventory
    except product.inventory.RelatedObjectDoesNotExist:
        inventory = None
    if inventory and not inventory.allow_backorder and item.quantity > inventory.available_quantity:
        raise CartError(f"Only {inventory.available_quantity} unit(s) are currently available.")
    if not created:
        item.save(update_fields=("quantity", "updated_at"))
    return item


@transaction.atomic
def set_item_quantity(*, cart: Cart, item_id: int, quantity: int) -> CartItem | None:
    """Update a line safely; zero removes it, avoiding a separate hidden branch."""
    item = CartItem.objects.select_for_update().select_related("product__category").filter(
        pk=item_id, cart=cart
    ).first()
    if item is None:
        raise CartError("That cart item could not be found.")
    if quantity <= 0:
        item.delete()
        return None
    if not item.product.is_available_for_sale:
        raise CartError("This product is currently unavailable.")
    if quantity > 99:
        raise CartError("Choose no more than 99 units in one cart line.")
    try:
        inventory = item.product.inventory
    except item.product.inventory.RelatedObjectDoesNotExist:
        inventory = None
    if inventory and not inventory.allow_backorder and quantity > inventory.available_quantity:
        raise CartError(f"Only {inventory.available_quantity} unit(s) are currently available.")
    item.quantity = quantity
    item.save(update_fields=("quantity", "updated_at"))
    return item


def totals(cart: Cart) -> CartTotals:
    """Return decimal-safe totals after callers prefetch item products."""
    items = cart.items.select_related("product")
    return CartTotals(
        subtotal=sum((item.line_total for item in items), start=Decimal("0.00")),
        item_count=sum(item.quantity for item in items),
    )
