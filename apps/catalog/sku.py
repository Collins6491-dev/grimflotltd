"""Database-safe product SKU allocation."""

from __future__ import annotations

from django.db import IntegrityError, transaction


CATEGORY_PREFIXES = {
    "solar": "SOL",
    "solar-panels": "SOL",
    "inverters": "INV",
    "inverter": "INV",
    "cctv": "CCTV",
    "security": "CCTV",
    "security-cameras": "CCTV",
    "smart-locks": "LOCK",
    "access-control": "LOCK",
    "networking": "NET",
    "starlink": "NET",
    "electrical": "ELEC",
}


def category_prefix(category) -> str:
    """Return the stable SKU code for a category, with a safe fallback."""
    return CATEGORY_PREFIXES.get(getattr(category, "slug", ""), "GEN")


def allocate_sku(category) -> str:
    """Reserve the next SKU for a category inside the caller's transaction."""
    from .models import SKUSequence

    prefix = category_prefix(category)
    try:
        sequence = SKUSequence.objects.select_for_update().get(prefix=prefix)
    except SKUSequence.DoesNotExist:
        try:
            # A savepoint keeps a simultaneous insert from invalidating the
            # surrounding Product.save transaction.
            with transaction.atomic():
                sequence = SKUSequence.objects.create(prefix=prefix, next_value=2)
            value = 1
        except IntegrityError:
            sequence = SKUSequence.objects.select_for_update().get(prefix=prefix)
            value = sequence.next_value
            sequence.next_value = value + 1
            sequence.save(update_fields=("next_value", "updated_at"))
    else:
        value = sequence.next_value
        sequence.next_value = value + 1
        sequence.save(update_fields=("next_value", "updated_at"))

    return f"GRM-{prefix}-{value:04d}"
