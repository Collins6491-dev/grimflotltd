"""Provider-agnostic payment records; provider calls live in services.py."""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class PaymentTransaction(TimeStampedModel):
    INITIALIZED = "initialized"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    ABANDONED = "abandoned"
    STATUS_CHOICES = (
        (INITIALIZED, "Initialized"),
        (PENDING, "Pending"),
        (SUCCESS, "Successful"),
        (FAILED, "Failed"),
        (ABANDONED, "Abandoned"),
    )

    PAYSTACK = "paystack"
    PROVIDER_CHOICES = ((PAYSTACK, "Paystack"),)

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PAYSTACK)
    reference = models.CharField(max_length=100, unique=True)
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=INITIALIZED)
    provider_transaction_id = models.CharField(blank=True, max_length=100)
    provider_payload = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    failure_reason = models.CharField(blank=True, max_length=500)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("order", "status"), name="payments_order_status_idx")]

    def __str__(self) -> str:
        return f"{self.provider}: {self.reference}"


class WebhookEvent(TimeStampedModel):
    """Records accepted delivery identifiers so retried webhooks stay idempotent."""

    provider = models.CharField(max_length=20)
    event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
