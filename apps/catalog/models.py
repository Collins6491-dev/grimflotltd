"""Database models for the public product catalogue.

The catalogue owns product facts, presentation media, and the current stock
position. Cart reservations, stock movements, and order snapshots deliberately
arrive in later stages so this bounded domain stays useful without pretending
that a checkout process already exists.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.validators import safe_upload_filename, validate_content_image


sku_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9._-]{1,63}$",
    message="Use 2–64 uppercase letters, numbers, periods, underscores, or hyphens.",
)
currency_validator = RegexValidator(
    regex=r"^[A-Z]{3}$",
    message="Use a three-letter ISO currency code such as NGN.",
)


def category_image_upload_path(instance: "Category", filename: str) -> str:
    """Store category artwork under a stable, non-user-controlled prefix."""
    return f"catalogue/categories/{instance.slug or slugify(instance.name)}/{safe_upload_filename(filename)}"


def product_image_upload_path(instance: "ProductImage", filename: str) -> str:
    """Store product media by product slug while retaining a safe extension."""
    return f"catalogue/products/{instance.product.slug}/{safe_upload_filename(filename)}"


class Category(TimeStampedModel):
    """A public-facing grouping for related products."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True, max_length=1_000)
    image = models.ImageField(
        upload_to=category_image_upload_path,
        blank=True,
        validators=[validate_content_image],
    )
    image_alt = models.CharField(blank=True, max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order", "name")
        verbose_name_plural = "categories"
        indexes = [
            models.Index(
                fields=("is_published", "order"),
                name="catalog_ca_published_idx",
            ),
            models.Index(fields=("name",), name="catalogue_ca_name_f5e48e_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class SKUSequence(TimeStampedModel):
    """One locked, per-prefix counter used to allocate product SKUs."""

    prefix = models.CharField(max_length=12, unique=True)
    next_value = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "SKU sequence"
        verbose_name_plural = "SKU sequences"

    def __str__(self) -> str:
        return f"{self.prefix}: {self.next_value}"


class Product(TimeStampedModel):
    """A purchasable product, intentionally independent from order snapshots."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    sku = models.CharField(max_length=64, unique=True, validators=[sku_validator])
    short_description = models.CharField(max_length=500)
    description = models.TextField(max_length=8_000)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(
        blank=True,
        null=True,
        max_digits=12,
        decimal_places=2,
        help_text="Optional former price. It must be greater than or equal to the selling price.",
    )
    currency = models.CharField(max_length=3, default="NGN", validators=[currency_validator])
    installation_available = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    meta_title = models.CharField(blank=True, max_length=70)
    meta_description = models.CharField(blank=True, max_length=160)

    class Meta:
        ordering = ("-is_featured", "name")
        indexes = [
            models.Index(
                fields=("is_published", "is_featured", "category"),
                name="catalog_pr_published_idx",
            ),
            models.Index(fields=("name",), name="catalogue_pr_name_44240b_idx"),
            models.Index(fields=("sku",), name="catalogue_pr_sku_1f16b3_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="catalogue_product_price_nonnegative"),
            models.CheckConstraint(
                condition=Q(compare_at_price__isnull=True) | Q(compare_at_price__gte=models.F("price")),
                name="catalogue_product_compare_price_valid",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.compare_at_price is not None and self.price is not None:
            if self.compare_at_price < self.price:
                raise ValidationError(
                    {"compare_at_price": "The former price cannot be lower than the selling price."}
                )

    def save(self, *args, **kwargs) -> None:
        if self._state.adding and not self.sku:
            from .sku import allocate_sku

            # The sequence reservation and product insert must succeed or fail
            # together, preventing a partial allocation on failed writes.
            with transaction.atomic():
                self.sku = allocate_sku(self.category)
                self.currency = self.currency.strip().upper()
                super().save(*args, **kwargs)
            return

        self.sku = self.sku.strip().upper()
        self.currency = self.currency.strip().upper()
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        """Use preloaded images where available to avoid catalogue N+1 queries."""
        images = getattr(self, "_prefetched_objects_cache", {}).get("images")
        if images is not None:
            return next(iter(images), None)
        return self.images.order_by("-is_primary", "order", "id").first()

    @property
    def stock_status(self) -> str:
        """Return a presentation-safe stock label without exposing quantities."""
        try:
            inventory = self.inventory
        except InventoryRecord.DoesNotExist:
            return "Availability to be confirmed"
        if inventory.available_quantity > 0:
            return "In stock"
        if inventory.allow_backorder:
            return "Available on backorder"
        return "Currently unavailable"

    @property
    def is_available_for_sale(self) -> bool:
        """Expose availability without treating an absent inventory row as stock."""
        try:
            inventory = self.inventory
        except InventoryRecord.DoesNotExist:
            return False
        return inventory.available_quantity > 0 or inventory.allow_backorder

    def get_absolute_url(self) -> str:
        return reverse("catalogue:product-detail", kwargs={"slug": self.slug})

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"


class ProductImage(TimeStampedModel):
    """An ordered, accessible product image. One image may be marked primary."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_upload_path, validators=[validate_content_image])
    alt_text = models.CharField(max_length=255)
    caption = models.CharField(blank=True, max_length=500)
    order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_primary", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product",),
                condition=Q(is_primary=True),
                name="catalogue_one_primary_image_per_product",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product}: image {self.order}"


class ProductSpecification(TimeStampedModel):
    """A concise, ordered technical fact displayed on a product detail page."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specifications")
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "label"),
                name="catalogue_unique_product_specification_label",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product}: {self.label}"


class InventoryRecord(TimeStampedModel):
    """Current stock position for one product.

    Inventory adjustments and their audit trail are introduced with operational
    workflows later; this record is intentionally a small, trustworthy source
    of public availability for the catalogue stage.
    """

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity_on_hand = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Units held for pending orders. This is managed only by checkout services.",
    )
    reorder_level = models.PositiveIntegerField(default=0)
    allow_backorder = models.BooleanField(default=False)

    class Meta:
        verbose_name = "inventory record"
        verbose_name_plural = "inventory records"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0),
                name="catalogue_inventory_quantity_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reorder_level__gte=0),
                name="catalogue_inventory_reorder_level_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=0),
                name="catalogue_inventory_reserved_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=models.F("reserved_quantity")),
                name="catalogue_inventory_reservations_within_stock",
            ),
        ]

    @property
    def is_low_stock(self) -> bool:
        return self.available_quantity <= self.reorder_level

    @property
    def available_quantity(self) -> int:
        """Stock currently available to a new customer after active holds."""
        return self.quantity_on_hand - self.reserved_quantity

    def __str__(self) -> str:
        return f"{self.product}: {self.quantity_on_hand} on hand"


class StockMovement(TimeStampedModel):
    """Append-only operational explanation for every inventory adjustment."""

    RECEIPT = "receipt"
    RESERVATION = "reservation"
    RELEASE = "release"
    FULFILMENT = "fulfilment"
    ADJUSTMENT = "adjustment"
    MOVEMENT_CHOICES = (
        (RECEIPT, "Receipt"),
        (RESERVATION, "Reservation"),
        (RELEASE, "Reservation release"),
        (FULFILMENT, "Fulfilment"),
        (ADJUSTMENT, "Manual adjustment"),
    )

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_movements")
    quantity_delta = models.IntegerField()
    reserved_delta = models.IntegerField(default=0)
    movement_type = models.CharField(max_length=16, choices=MOVEMENT_CHOICES)
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(
        "accounts.User",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="stock_movements",
    )

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("product", "-created_at"), name="catalogue_stock_history_idx")]

    def __str__(self) -> str:
        return f"{self.product.sku}: {self.movement_type} ({self.quantity_delta:+d})"
