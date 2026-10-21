"""Restricted catalogue maintenance before the custom dashboard stage."""

from django.contrib import admin

from .models import Category, InventoryRecord, Product, ProductImage, ProductSpecification


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "alt_text", "caption", "is_primary", "order")


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 0
    fields = ("label", "value", "order")


class InventoryRecordInline(admin.StackedInline):
    model = InventoryRecord
    extra = 0
    max_num = 1
    fields = ("quantity_on_hand", "reorder_level", "allow_backorder")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_published", "order", "updated_at")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "currency", "availability", "is_published")
    list_filter = ("is_published", "is_featured", "installation_available", "category")
    search_fields = ("name", "sku", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("category",)
    readonly_fields = ("sku",)
    list_select_related = ("category", "inventory")
    inlines = (InventoryRecordInline, ProductImageInline, ProductSpecificationInline)
    fieldsets = (
        ("Product", {"fields": ("name", "slug", "sku", "category", "short_description", "description")}),
        ("Commercial details", {"fields": ("price", "compare_at_price", "currency", "installation_available")}),
        ("Publishing", {"fields": ("is_published", "is_featured")}),
        ("Search metadata", {"classes": ("collapse",), "fields": ("meta_title", "meta_description")}),
    )

    @admin.display(description="Availability", ordering="inventory__quantity_on_hand")
    def availability(self, product: Product) -> str:
        return product.stock_status


@admin.register(InventoryRecord)
class InventoryRecordAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity_on_hand", "reorder_level", "allow_backorder", "is_low_stock")
    list_filter = ("allow_backorder",)
    search_fields = ("product__name", "product__sku")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)

    @admin.display(boolean=True, description="Low stock")
    def is_low_stock(self, inventory: InventoryRecord) -> bool:
        return inventory.is_low_stock
