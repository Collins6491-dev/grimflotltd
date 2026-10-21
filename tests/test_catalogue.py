"""Stage 5 tests for public catalogue discovery and stock-aware content."""

from __future__ import annotations

from io import BytesIO
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User
from apps.catalog.forms import CatalogueFilterForm
from apps.catalog.models import Category, InventoryRecord, Product, ProductImage, ProductSpecification, StockMovement
from apps.dashboard.forms import ProductDashboardForm
from apps.catalog.selectors import published_products


class CatalogueFactoryMixin:
    def create_category(self, *, name="Security", slug="security", published=True):
        return Category.objects.create(name=name, slug=slug, is_published=published)

    def create_product(
        self,
        *,
        category,
        name="Network Camera",
        slug="network-camera",
        sku="CAM-001",
        price=Decimal("125000.00"),
        published=True,
        featured=False,
    ):
        return Product.objects.create(
            category=category,
            name=name,
            slug=slug,
            sku=sku,
            short_description=f"A concise description of {name}.",
            description=f"A complete description of {name}.",
            price=price,
            is_published=published,
            is_featured=featured,
        )


class ProductModelTests(CatalogueFactoryMixin, TestCase):
    def test_new_product_without_a_sku_receives_a_category_sequence(self):
        category = self.create_category(name="Solar", slug="solar")
        first = Product.objects.create(
            category=category, name="Solar panel", slug="solar-panel", short_description="Panel", description="Panel description", price=Decimal("1.00")
        )
        second = Product.objects.create(
            category=category, name="Solar battery", slug="solar-battery", short_description="Battery", description="Battery description", price=Decimal("1.00")
        )

        self.assertEqual(first.sku, "GRM-SOL-0001")
        self.assertEqual(second.sku, "GRM-SOL-0002")

    def test_sku_is_preserved_when_a_product_category_changes(self):
        security = self.create_category(name="Security", slug="security")
        solar = self.create_category(name="Solar", slug="solar")
        product = Product.objects.create(
            category=security, name="Camera", slug="camera", short_description="Camera", description="Camera description", price=Decimal("1.00")
        )
        product.category = solar
        product.save()

        self.assertEqual(product.sku, "GRM-CCTV-0001")

    def test_dashboard_product_form_does_not_accept_a_manual_sku(self):
        self.assertNotIn("sku", ProductDashboardForm().fields)

    def test_product_normalises_sku_and_currency_on_save(self):
        category = self.create_category()
        product = self.create_product(category=category, sku="cam-01", price=Decimal("1.00"))

        self.assertEqual(product.sku, "CAM-01")
        self.assertEqual(product.currency, "NGN")

    def test_form_validation_rejects_a_former_price_lower_than_the_selling_price(self):
        product = Product(
            category=self.create_category(),
            name="Solar inverter",
            slug="solar-inverter",
            sku="INV-001",
            short_description="A concise description.",
            description="A complete description.",
            price=Decimal("200.00"),
            compare_at_price=Decimal("199.99"),
        )

        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_one_product_can_only_have_one_primary_image(self):
        product = self.create_product(category=self.create_category())
        ProductImage.objects.create(
            product=product,
            image="catalogue/products/network-camera/one.jpg",
            alt_text="The first product image.",
            is_primary=True,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductImage.objects.create(
                product=product,
                image="catalogue/products/network-camera/two.jpg",
                alt_text="The second product image.",
                is_primary=True,
            )

    def test_inventory_status_distinguishes_stock_backorder_and_missing_records(self):
        category = self.create_category()
        stocked = self.create_product(category=category, sku="STOCK-1")
        backorder = self.create_product(
            category=category,
            name="Backorder camera",
            slug="backorder-camera",
            sku="BACK-1",
        )
        untracked = self.create_product(
            category=category,
            name="Untracked camera",
            slug="untracked-camera",
            sku="TRACK-1",
        )
        InventoryRecord.objects.create(product=stocked, quantity_on_hand=2)
        InventoryRecord.objects.create(product=backorder, allow_backorder=True)

        self.assertEqual(stocked.stock_status, "In stock")
        self.assertEqual(backorder.stock_status, "Available on backorder")
        self.assertEqual(untracked.stock_status, "Availability to be confirmed")


class CatalogueSelectorTests(CatalogueFactoryMixin, TestCase):
    def test_only_published_products_in_published_categories_are_public(self):
        public_category = self.create_category()
        private_category = self.create_category(name="Private", slug="private", published=False)
        visible = self.create_product(category=public_category, sku="VISIBLE-1")
        self.create_product(
            category=public_category,
            name="Draft product",
            slug="draft-product",
            sku="DRAFT-1",
            published=False,
        )
        self.create_product(
            category=private_category,
            name="Hidden category product",
            slug="hidden-category-product",
            sku="HIDDEN-1",
        )

        self.assertEqual(list(published_products()), [visible])

    def test_search_matches_product_name_sku_and_category(self):
        category = self.create_category(name="Energy systems", slug="energy")
        product = self.create_product(
            category=category,
            name="Hybrid inverter",
            slug="hybrid-inverter",
            sku="INV-230",
        )

        self.assertEqual(list(published_products(filters={"q": "INV-230"})), [product])
        self.assertEqual(list(published_products(filters={"q": "energy"})), [product])

    def test_zero_is_a_valid_price_boundary(self):
        category = self.create_category()
        free_product = self.create_product(
            category=category,
            name="Demonstration item",
            slug="demonstration-item",
            sku="FREE-1",
            price=Decimal("0.00"),
        )
        self.create_product(
            category=category,
            name="Priced item",
            slug="priced-item",
            sku="PRICE-1",
            price=Decimal("1.00"),
        )

        results = published_products(
            filters={"min_price": Decimal("0.00"), "max_price": Decimal("0.00")}
        )

        self.assertEqual(list(results), [free_product])

    def test_filter_form_rejects_an_inverted_price_range(self):
        form = CatalogueFilterForm(
            {"min_price": "200", "max_price": "100"},
            categories=Category.objects.none(),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("max_price", form.errors)


class CatalogueViewTests(CatalogueFactoryMixin, TestCase):
    def test_listing_search_and_availability_filter_hide_unavailable_products(self):
        category = self.create_category()
        stocked = self.create_product(category=category, name="Indoor camera", slug="indoor-camera", sku="IN-1")
        backorder = self.create_product(category=category, name="Outdoor camera", slug="outdoor-camera", sku="OUT-1")
        unavailable = self.create_product(category=category, name="Offline camera", slug="offline-camera", sku="OFF-1")
        InventoryRecord.objects.create(product=stocked, quantity_on_hand=1)
        InventoryRecord.objects.create(product=backorder, allow_backorder=True)
        InventoryRecord.objects.create(product=unavailable)

        response = self.client.get(reverse("catalogue:product-list"), {"q": "camera", "availability": "on"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, stocked.name)
        self.assertContains(response, backorder.name)
        self.assertNotContains(response, unavailable.name)
        self.assertContains(response, "Available on backorder")

    def test_product_detail_renders_specifications_and_only_allows_published_products(self):
        category = self.create_category()
        product = self.create_product(category=category)
        InventoryRecord.objects.create(product=product, quantity_on_hand=3)
        ProductSpecification.objects.create(product=product, label="Power input", value="12 V DC")
        ProductImage.objects.create(
            product=product,
            image="catalogue/products/network-camera/camera.jpg",
            alt_text="A compact network camera.",
            is_primary=True,
        )
        draft = self.create_product(
            category=category,
            name="Draft camera",
            slug="draft-camera",
            sku="DRAFT-CAM",
            published=False,
        )

        response = self.client.get(product.get_absolute_url())
        draft_response = self.client.get(draft.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Power input")
        self.assertContains(response, "A compact network camera.")
        self.assertContains(response, "Add to cart")
        self.assertContains(response, "Practical feedback, moderated before publication.")
        self.assertEqual(draft_response.status_code, 404)

    def test_global_header_product_search_submits_to_the_catalogue(self):
        response = self.client.get(reverse("catalogue:product-list"))

        self.assertContains(response, 'action="/products/"')
        self.assertContains(response, "placeholder=\"Search products\"")


class DashboardProductWorkflowTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.staff = User.objects.create_user(
            email="catalogue-staff@example.com", password="secure-password", is_staff=True
        )
        self.category = Category.objects.create(name="Security", slug="security", is_published=True)
        self.client.force_login(self.staff)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()
        super().tearDown()

    @staticmethod
    def uploaded_image(name="camera.png"):
        buffer = BytesIO()
        Image.new("RGB", (20, 20), color="navy").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def product_payload(self, **overrides):
        payload = {
            "category": self.category.pk,
            "name": "Network camera",
            "slug": "network-camera",
            "short_description": "A compact network camera.",
            "description": "A complete network-camera description.",
            "price": "125000.00",
            "compare_at_price": "",
            "currency": "NGN",
            "quantity_on_hand": "5",
            "reorder_level": "1",
            "image": self.uploaded_image(),
            "is_published": "on",
        }
        payload.update(overrides)
        return payload

    def test_staff_can_create_a_published_product_with_inventory_image_and_stock_audit(self):
        response = self.client.post(reverse("dashboard:product-new"), self.product_payload())

        product = Product.objects.get(slug="network-camera")
        image = product.primary_image
        self.assertRedirects(response, reverse("dashboard:product-edit", args=[product.pk]))
        self.assertTrue(product.is_published)
        self.assertTrue(product.sku)
        self.assertEqual(product.inventory.quantity_on_hand, 5)
        self.assertIsNotNone(image)
        self.assertEqual(image.product, product)
        self.assertTrue(image.is_primary)
        self.assertEqual(image.alt_text, product.name)
        self.assertTrue(StockMovement.objects.filter(product=product, quantity_delta=5).exists())
        self.assertContains(self.client.get(reverse("catalogue:product-list")), product.name)

    def test_replacing_primary_image_updates_the_existing_image_record(self):
        product = Product.objects.create(
            category=self.category,
            name="Network camera",
            slug="network-camera",
            sku="CAM-001",
            short_description="A compact network camera.",
            description="A complete network-camera description.",
            price=Decimal("125000.00"),
            is_published=True,
        )
        InventoryRecord.objects.create(product=product, quantity_on_hand=5)
        primary = ProductImage.objects.create(
            product=product,
            image=self.uploaded_image("original.png"),
            alt_text="Original camera image.",
            is_primary=True,
        )

        response = self.client.post(
            reverse("dashboard:product-edit", args=[product.pk]),
            self.product_payload(image=self.uploaded_image("replacement.png")),
        )

        primary.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:product-edit", args=[product.pk]))
        self.assertEqual(ProductImage.objects.filter(product=product, is_primary=True).count(), 1)
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(primary.alt_text, product.name)
        self.assertIn("replacement", primary.image.name)
