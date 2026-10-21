"""Testimonials approved for publication by staff.

Product reviews are intentionally deferred to the catalogue and commerce stages.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Testimonial(TimeStampedModel):
    """An attributable testimonial with an explicit demonstration marker."""

    person_name = models.CharField(max_length=120)
    role_or_company = models.CharField(blank=True, max_length=160)
    quote = models.TextField(max_length=2_000)
    source_reference = models.CharField(
        blank=True,
        max_length=255,
        help_text="Internal consent or source reference; never shown publicly.",
    )
    is_demonstration = models.BooleanField(
        default=True,
        help_text="Keep selected until a real, consented testimonial is verified.",
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "id")
        indexes = [models.Index(fields=("is_published", "order"))]

    def __str__(self) -> str:
        return self.person_name


class ProductReview(TimeStampedModel):
    """A verified-purchase-compatible customer review awaiting staff moderation."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = ((PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected"))

    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="product_reviews")
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    body = models.TextField(max_length=2_000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("product", "user"), name="reviews_one_review_per_product_customer"),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="reviews_rating_between_one_and_five"),
        ]

    def __str__(self) -> str:
        return f"{self.product}: {self.rating}/5"
