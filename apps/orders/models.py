"""Immutable order snapshots and delivery records."""

from __future__ import annotations

import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class DeliveryAddress(TimeStampedModel):
    """Reusable customer address, copied into every placed order."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    recipient_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(blank=True, max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    country = models.CharField(max_length=2, default="NG")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_default", "-updated_at")

    def __str__(self) -> str:
        return f"{self.recipient_name}, {self.city}"


class Order(TimeStampedModel):
    """A financially stable order, with customer and delivery data snapshotted."""

    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    STATUS_CHOICES = (
        (PENDING_PAYMENT, "Pending payment"),
        (PAID, "Paid"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (REFUNDED, "Refunded"),
    )

    reference = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING_PAYMENT)
    currency = models.CharField(max_length=3, default="NGN")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    recipient_name = models.CharField(max_length=160)
    recipient_phone = models.CharField(max_length=40)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(blank=True, max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    country = models.CharField(max_length=2, default="NG")
    customer_note = models.TextField(blank=True, max_length=1_500)
    paid_at = models.DateTimeField(blank=True, null=True)
    reservation_released_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "-created_at"), name="orders_customer_history_idx"),
            models.Index(fields=("status", "-created_at"), name="orders_status_history_idx"),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = f"GFL-{timezone.now():%y%m%d}-{secrets.token_hex(4).upper()}"
        super().save(*args, **kwargs)

    def mark_paid(self) -> None:
        self.status = self.PAID
        self.paid_at = timezone.now()

    def __str__(self) -> str:
        return self.reference


class OrderItem(models.Model):
    """Product facts at time of order; product edits can never rewrite history."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", blank=True, null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=180)
    sku = models.CharField(max_length=64)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # The physical portion of a line held while payment is pending.  This is
    # deliberately kept on the immutable order line so a later catalogue edit
    # cannot change the inventory release/fulfilment calculation.
    reserved_quantity = models.PositiveIntegerField(default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.order.reference}: {self.product_name}"


class OrderStatusEvent(TimeStampedModel):
    """Audit trail for support-facing order status changes."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_events")
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.CharField(blank=True, max_length=500)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL, related_name="order_status_events"
    )

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.order.reference}: {self.status}"
