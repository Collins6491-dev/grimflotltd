"""Qualified public enquiries, quotations, and contact requests."""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Enquiry(TimeStampedModel):
    GENERAL = "general"
    QUOTE = "quote"
    CONTACT = "contact"
    ENQUIRY_TYPES = ((GENERAL, "General"), (QUOTE, "Quote request"), (CONTACT, "Contact"))
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    STATUS_CHOICES = ((NEW, "New"), (IN_PROGRESS, "In progress"), (CLOSED, "Closed"))

    enquiry_type = models.CharField(max_length=16, choices=ENQUIRY_TYPES, default=GENERAL)
    name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(blank=True, max_length=40)
    organisation = models.CharField(blank=True, max_length=160)
    service_interest = models.CharField(blank=True, max_length=160)
    message = models.TextField(max_length=4_000)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=NEW)
    consent_to_contact = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        "accounts.User", blank=True, null=True, on_delete=models.SET_NULL, related_name="assigned_enquiries"
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "-created_at"), name="enquiries_status_idx")]

    def __str__(self) -> str:
        return f"{self.get_enquiry_type_display()}: {self.name}"
