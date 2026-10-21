"""Regression coverage for completed public flows and commerce safeguards."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, InventoryRecord, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import ProductReview


class PublicRouteTests(TestCase):
    def test_public_information_routes_render_without_missing_templates(self):
        for route_name in (
            "about",
            "faq",
            "solar-estimator",
            "privacy",
            "terms",
            "shipping",
            "returns",
            "services:list",
            "projects:list",
            "projects:gallery",
            "enquiries:contact",
            "enquiries:quote",
            "bookings:consultation",
            "cart:detail",
        ):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_solar_estimator_returns_non_binding_numeric_direction(self):
        response = self.client.post(
            reverse("solar-estimator"),
            {"monthly_kwh": "450", "peak_load_kw": "2.5", "backup_hours": "4", "solar_hours": "4.5"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indicative solar array")
        self.assertContains(response, "Planning direction")


class DashboardAuthenticationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email="operator@example.com",
            password="safe-password-123",
            is_staff=True,
        )

    def test_dashboard_redirects_anonymous_visitors_to_the_staff_login(self):
        response = self.client.get(reverse("dashboard:overview"))

        self.assertRedirects(
            response,
            f"{reverse('dashboard:login')}?next={reverse('dashboard:overview')}",
        )

    def test_staff_login_honours_a_safe_dashboard_destination(self):
        response = self.client.post(
            reverse("dashboard:login"),
            {
                "username": self.staff.email,
                "password": "safe-password-123",
                "next": reverse("dashboard:overview"),
            },
        )

        self.assertRedirects(response, reverse("dashboard:overview"))
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 200)

    def test_customer_account_cannot_sign_in_to_the_dashboard(self):
        customer = User.objects.create_user(email="customer@example.com", password="safe-password-123")

        response = self.client.post(
            reverse("dashboard:login"),
            {"username": customer.email, "password": "safe-password-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not have access to the operations dashboard")

    def test_dashboard_logout_is_a_csrf_protected_post_flow(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse("dashboard:logout"))

        self.assertRedirects(response, reverse("dashboard:login"))
        protected_response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(protected_response.status_code, 302)

    def test_dashboard_template_includes_the_post_logout_control(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:overview"))

        self.assertContains(response, 'action="/dashboard/logout/"')
        self.assertContains(response, "Log out")


class ReviewWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="customer@example.com", password="safe-password-123")
        self.category = Category.objects.create(name="Security", slug="security", is_published=True)
        self.product = Product.objects.create(
            category=self.category,
            name="Network camera",
            slug="network-camera",
            sku="CAM-01",
            short_description="Compact camera.",
            description="A complete compact camera.",
            price=Decimal("120000.00"),
            is_published=True,
        )
        InventoryRecord.objects.create(product=self.product, quantity_on_hand=5)
        self.client.force_login(self.user)

    def _paid_order_item(self):
        order = Order.objects.create(
            user=self.user,
            email=self.user.email,
            status=Order.COMPLETED,
            subtotal=Decimal("120000.00"),
            total=Decimal("120000.00"),
            recipient_name="A Customer",
            recipient_phone="08000000000",
            address_line_1="1 Test Street",
            city="Lagos",
            state="Lagos",
        )
        return OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            sku=self.product.sku,
            unit_price=self.product.price,
            quantity=1,
            line_total=self.product.price,
        )

    def test_review_submission_requires_a_verified_purchase(self):
        response = self.client.post(
            reverse("reviews:submit-product-review", args=[self.product.slug]),
            {"rating": 5, "title": "Excellent", "body": "Reliable installation-ready equipment."},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProductReview.objects.exists())

    def test_verified_purchase_review_is_saved_pending_moderation(self):
        self._paid_order_item()
        response = self.client.post(
            reverse("reviews:submit-product-review", args=[self.product.slug]),
            {"rating": 5, "title": "Excellent", "body": "Reliable installation-ready equipment."},
        )

        review = ProductReview.objects.get()
        self.assertRedirects(response, self.product.get_absolute_url())
        self.assertEqual(review.status, ProductReview.PENDING)
        self.assertEqual(review.user, self.user)
