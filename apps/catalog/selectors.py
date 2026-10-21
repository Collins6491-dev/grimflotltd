"""Read-only catalogue queries shared by public views and future APIs."""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet

from .forms import CatalogueFilterForm
from .models import Product, ProductImage


def published_products(*, filters: dict | None = None) -> QuerySet[Product]:
    """Return efficient, publishable products for a safe filter set."""
    filters = filters or {}
    queryset = (
        Product.objects.filter(is_published=True, category__is_published=True)
        .select_related("category", "inventory")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.order_by("-is_primary", "order", "id"),
            )
        )
    )

    query = filters.get("q")
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
        )

    if category := filters.get("category"):
        queryset = queryset.filter(category=category)
    if (minimum := filters.get("min_price")) is not None:
        queryset = queryset.filter(price__gte=minimum)
    if (maximum := filters.get("max_price")) is not None:
        queryset = queryset.filter(price__lte=maximum)
    if filters.get("availability"):
        queryset = queryset.filter(
            Q(inventory__quantity_on_hand__gt=0) | Q(inventory__allow_backorder=True)
        )

    ordering = {
        CatalogueFilterForm.SORT_NAME: ("name",),
        CatalogueFilterForm.SORT_PRICE_ASC: ("price", "name"),
        CatalogueFilterForm.SORT_PRICE_DESC: ("-price", "name"),
    }.get(filters.get("sort"), ("-is_featured", "name"))
    return queryset.order_by(*ordering)
