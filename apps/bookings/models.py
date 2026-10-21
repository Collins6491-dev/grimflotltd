"""Consultation booking requests that staff can confirm operationally."""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class ConsultationBooking(TimeStampedModel):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending review"),
        (CONFIRMED, "Confirmed"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    )

    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    requested_for = models.DateTimeField()
    service_interest = models.CharField(max_length=160)
    property_type = models.CharField(blank=True, max_length=120)
    notes = models.TextField(blank=True, max_length=2_500)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    confirmed_for = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        "accounts.User", blank=True, null=True, on_delete=models.SET_NULL, related_name="assigned_bookings"
    )

    class Meta:
        ordering = ("requested_for",)
        indexes = [models.Index(fields=("status", "requested_for"), name="bookings_status_schedule_idx")]

    def __str__(self) -> str:
        return f"{self.name}: {self.requested_for:%Y-%m-%d %H:%M}"
