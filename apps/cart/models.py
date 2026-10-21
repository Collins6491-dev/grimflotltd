"""Persistent, stock-aware shopping carts for guests and signed-in customers."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """One mutable cart that can move from a browser session to a customer."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    currency = models.CharField(max_length=3, default="NGN")

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(user__isnull=False),
                name="cart_one_open_cart_per_customer",
            )
        ]

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), start=0)

    def __str__(self) -> str:
        return f"Cart {self.pk or 'new'}"


class CartItem(TimeStampedModel):
    """A product quantity with the current commercial price read at checkout."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.UniqueConstraint(fields=("cart", "product"), name="cart_one_item_per_product")
        ]

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def __str__(self) -> str:
        return f"{self.quantity} × {self.product}"
