"""Transactional checkout, reservations, and order lifecycle helpers."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cart.models import Cart
from apps.catalog.models import InventoryRecord, StockMovement

from .models import Order, OrderItem, OrderStatusEvent


class CheckoutError(Exception):
    """A controlled checkout failure suitable for a form-level message."""


def _address_fields(data: dict) -> dict:
    return {
        name: data[name]
        for name in (
            "recipient_name",
            "recipient_phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
        )
    }


@transaction.atomic
def create_pending_order(*, user, cart: Cart, checkout_data: dict) -> Order:
    """Snapshot a cart and reserve physical stock in one database transaction."""
    if not user.is_email_verified:
        raise CheckoutError("Verify your email address before starting payment.")

    locked_cart = Cart.objects.select_for_update().get(pk=cart.pk)
    lines = list(
        locked_cart.items.select_related("product__category").order_by("id")
    )
    if not lines:
        raise CheckoutError("Your cart is empty.")

    product_ids = [line.product_id for line in lines]
    inventory_by_product = {
        inventory.product_id: inventory
        for inventory in InventoryRecord.objects.select_for_update().filter(product_id__in=product_ids)
    }
    subtotal = Decimal("0.00")
    reservations: list[tuple[object, int]] = []
    for line in lines:
        product = line.product
        inventory = inventory_by_product.get(product.pk)
        if not product.is_published or not product.category.is_published or inventory is None:
            raise CheckoutError(f"{product.name} is no longer available.")
        available = inventory.available_quantity
        if available <= 0 and not inventory.allow_backorder:
            raise CheckoutError(f"{product.name} is now out of stock.")
        reserved = min(available, line.quantity)
        if reserved < line.quantity and not inventory.allow_backorder:
            raise CheckoutError(f"Only {available} unit(s) of {product.name} are currently available.")
        reservations.append((inventory, reserved))
        subtotal += product.price * line.quantity

    delivery_fee = Decimal("0.00")
    order = Order.objects.create(
        user=user,
        email=user.email,
        currency=locked_cart.currency,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount_total=Decimal("0.00"),
        total=subtotal + delivery_fee,
        customer_note=checkout_data.get("customer_note", ""),
        **_address_fields(checkout_data),
    )
    for line, (inventory, reserved) in zip(lines, reservations, strict=True):
        product = line.product
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            unit_price=product.price,
            quantity=line.quantity,
            reserved_quantity=reserved,
            line_total=product.price * line.quantity,
        )
        if reserved:
            inventory.reserved_quantity += reserved
            inventory.save(update_fields=("reserved_quantity", "updated_at"))
            StockMovement.objects.create(
                product=product,
                quantity_delta=0,
                reserved_delta=reserved,
                movement_type=StockMovement.RESERVATION,
                reference=order.reference,
                note="Reserved while awaiting payment.",
                actor=user,
            )
    OrderStatusEvent.objects.create(order=order, status=Order.PENDING_PAYMENT, actor=user)
    locked_cart.items.all().delete()
    return order


@transaction.atomic
def release_order_reservations(*, order: Order, actor=None, reason: str = "Payment was not completed.") -> bool:
    """Release physical holds exactly once for cancelled or failed orders."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.reservation_released_at or order.status in {Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.COMPLETED}:
        return False
    items = list(order.items.select_related("product").order_by("id"))
    inventories = {
        row.product_id: row
        for row in InventoryRecord.objects.select_for_update().filter(product_id__in=[item.product_id for item in items if item.product_id])
    }
    for item in items:
        if not item.product_id or not item.reserved_quantity:
            continue
        inventory = inventories[item.product_id]
        inventory.reserved_quantity -= item.reserved_quantity
        inventory.save(update_fields=("reserved_quantity", "updated_at"))
        StockMovement.objects.create(
            product_id=item.product_id,
            quantity_delta=0,
            reserved_delta=-item.reserved_quantity,
            movement_type=StockMovement.RELEASE,
            reference=order.reference,
            note=reason,
            actor=actor,
        )
    order.reservation_released_at = timezone.now()
    order.save(update_fields=("reservation_released_at", "updated_at"))
    return True


@transaction.atomic
def settle_paid_order(*, order: Order, actor=None) -> Order:
    """Consume reserved units once a verified provider result is accepted."""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status in {Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.COMPLETED}:
        return order
    if order.status != Order.PENDING_PAYMENT:
        raise ValidationError("Only a pending payment order can be settled.")
    items = list(order.items.select_related("product").order_by("id"))
    inventories = {
        row.product_id: row
        for row in InventoryRecord.objects.select_for_update().filter(product_id__in=[item.product_id for item in items if item.product_id])
    }
    for item in items:
        if not item.product_id or not item.reserved_quantity:
            continue
        inventory = inventories[item.product_id]
        if inventory.quantity_on_hand < item.reserved_quantity or inventory.reserved_quantity < item.reserved_quantity:
            raise ValidationError("Reserved inventory is inconsistent; payment requires staff review.")
        inventory.quantity_on_hand -= item.reserved_quantity
        inventory.reserved_quantity -= item.reserved_quantity
        inventory.save(update_fields=("quantity_on_hand", "reserved_quantity", "updated_at"))
        StockMovement.objects.create(
            product_id=item.product_id,
            quantity_delta=-item.reserved_quantity,
            reserved_delta=-item.reserved_quantity,
            movement_type=StockMovement.FULFILMENT,
            reference=order.reference,
            note="Verified payment converted reservation to fulfilment.",
            actor=actor,
        )
    order.mark_paid()
    order.save(update_fields=("status", "paid_at", "updated_at"))
    OrderStatusEvent.objects.create(order=order, status=Order.PAID, actor=actor)
    return order


@transaction.atomic
def change_order_status(*, order: Order, status: str, actor, note: str = "") -> Order:
    """Apply a permitted operational transition and preserve a clear audit trail.

    Payment settlement is intentionally the only path into ``paid``.  Staff
    cannot turn an unpaid order into a paid one from a dashboard select box.
    Refunds likewise need a verified financial action before a staff member
    records the matching terminal state.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    allowed_transitions = {
        Order.PENDING_PAYMENT: {Order.CANCELLED},
        Order.PAID: {Order.PROCESSING, Order.REFUNDED},
        Order.PROCESSING: {Order.SHIPPED, Order.REFUNDED},
        Order.SHIPPED: {Order.COMPLETED, Order.REFUNDED},
        Order.COMPLETED: {Order.REFUNDED},
        Order.CANCELLED: set(),
        Order.REFUNDED: set(),
    }
    if status == order.status:
        raise ValidationError("This order already has that status.")
    if status == Order.PAID:
        raise ValidationError("Paid status is set only after server-side payment verification.")
    if status not in allowed_transitions.get(order.status, set()):
        raise ValidationError("That order status transition is not permitted.")
    if status == Order.REFUNDED and not note.strip():
        raise ValidationError("Add the verified refund reference or note before recording a refund.")
    if status == Order.CANCELLED:
        release_order_reservations(order=order, actor=actor, reason="Order cancelled by staff.")
    order.status = status
    order.save(update_fields=("status", "updated_at"))
    OrderStatusEvent.objects.create(order=order, status=status, actor=actor, note=note)
    return order


@transaction.atomic
def cancel_unpaid_order(*, order: Order, actor=None, reason: str) -> Order:
    """Cancel an unverified payment safely and return its held stock once.

    A provider-declared failure must never leave an order appearing payable or
    retain stock indefinitely.  The helper is idempotent so a callback and a
    webhook can both reach this path without duplicating movements.
    """
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status == Order.PENDING_PAYMENT:
        release_order_reservations(order=locked, actor=actor, reason=reason)
        locked.status = Order.CANCELLED
        locked.save(update_fields=("status", "updated_at"))
        OrderStatusEvent.objects.create(
            order=locked,
            status=Order.CANCELLED,
            actor=actor,
            note=reason,
        )
    return locked
