"""Auditable records for actions performed through the staff dashboard."""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AuditEvent(TimeStampedModel):
    """A compact, append-only staff activity record for sensitive operations."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80, blank=True)
    summary = models.CharField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("object_type", "object_id"), name="dashboard_audit_object_idx")]
        permissions = (("clear_auditevent", "Can clear dashboard activity"),)

    def __str__(self) -> str:
        return f"{self.action}: {self.object_type} {self.object_id}"
