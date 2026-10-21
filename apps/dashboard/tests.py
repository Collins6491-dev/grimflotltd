from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.dashboard.models import AuditEvent
from apps.enquiries.models import Enquiry
from apps.services.models import Service


class DashboardSecurityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="secure-password", is_staff=True)
        self.admin.user_permissions.add(*Permission.objects.filter(codename__in=[
            "view_auditevent", "delete_auditevent", "clear_auditevent", "delete_service",
        ]))
        self.other_staff = User.objects.create_user(email="staff@example.com", password="secure-password", is_staff=True)

    def test_activity_delete_is_post_only_and_permission_protected(self):
        event = AuditEvent.objects.create(action="updated", object_type="test", summary="Test event")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("dashboard:activity-delete", args=[event.pk])).status_code, 405)
        self.client.force_login(self.other_staff)
        self.assertEqual(self.client.post(reverse("dashboard:activity-delete", args=[event.pk])).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:activity-delete", args=[event.pk]))
        self.assertFalse(AuditEvent.objects.filter(pk=event.pk).exists())

    def test_service_delete_uses_confirmation_and_post(self):
        service = Service.objects.create(title="Solar", slug="solar", short_description="Solar", description="Solar")
        self.client.force_login(self.admin)
        url = reverse("dashboard:service-delete", args=[service.pk])
        self.assertContains(self.client.get(url), "Delete service")
        self.client.post(url)
        self.assertFalse(Service.objects.filter(pk=service.pk).exists())


class EnquiryDeletionTests(TestCase):
    def setUp(self):
        self.authorized_staff = User.objects.create_user(
            email="enquiry-manager@example.com", password="secure-password", is_staff=True
        )
        self.authorized_staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="enquiries", codename="delete_enquiry")
        )
        self.unauthorized_staff = User.objects.create_user(
            email="staff-without-delete@example.com", password="secure-password", is_staff=True
        )

    def create_enquiry(self, **kwargs):
        return Enquiry.objects.create(
            name="Ada Lovelace",
            email="ada@example.com",
            message="Please contact me about a system design.",
            **kwargs,
        )

    def test_authorized_staff_confirm_then_delete_enquiry(self):
        enquiry = self.create_enquiry()
        enquiry_pk = enquiry.pk
        url = reverse("dashboard:enquiry-delete", args=[enquiry_pk])
        self.client.force_login(self.authorized_staff)

        self.assertContains(self.client.get(reverse("dashboard:enquiries")), url)
        response = self.client.get(url)
        self.assertContains(response, "Ada Lovelace")
        self.assertContains(response, "cannot be undone")
        self.assertContains(response, "Cancel")

        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse("dashboard:enquiries"))
        self.assertContains(response, "permanently deleted")
        self.assertFalse(Enquiry.objects.filter(pk=enquiry_pk).exists())
        self.assertTrue(AuditEvent.objects.filter(
            action="deleted", object_type="enquiries.enquiry", object_id=str(enquiry_pk)
        ).exists())

    def test_get_and_cancel_do_not_delete_enquiry(self):
        enquiry = self.create_enquiry()
        url = reverse("dashboard:enquiry-delete", args=[enquiry.pk])
        self.client.force_login(self.authorized_staff)

        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry.pk).exists())
        self.assertEqual(self.client.get(reverse("dashboard:enquiries")).status_code, 200)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry.pk).exists())

    def test_unauthorized_staff_cannot_view_or_delete_enquiry(self):
        enquiry = self.create_enquiry()
        url = reverse("dashboard:enquiry-delete", args=[enquiry.pk])
        self.client.force_login(self.unauthorized_staff)

        self.assertNotContains(self.client.get(reverse("dashboard:enquiries")), url)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry.pk).exists())

    def test_csrf_protection_is_enforced_for_deletion(self):
        enquiry = self.create_enquiry()
        enquiry_pk = enquiry.pk
        url = reverse("dashboard:enquiry-delete", args=[enquiry_pk])
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.authorized_staff)

        response = csrf_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(csrf_client.post(url).status_code, 403)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry_pk).exists())

        token = csrf_client.cookies["csrftoken"].value
        response = csrf_client.post(url, {"csrfmiddlewaretoken": token}, follow=True)
        self.assertRedirects(response, reverse("dashboard:enquiries"))
        self.assertFalse(Enquiry.objects.filter(pk=enquiry_pk).exists())

    def test_deleting_enquiry_does_not_delete_its_assigned_staff_member(self):
        assignee = User.objects.create_user(email="assigned@example.com", password="secure-password", is_staff=True)
        enquiry = self.create_enquiry(assigned_to=assignee)
        self.client.force_login(self.authorized_staff)

        self.client.post(reverse("dashboard:enquiry-delete", args=[enquiry.pk]))

        self.assertTrue(User.objects.filter(pk=assignee.pk).exists())


class CategoryDashboardTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(email="category-manager@example.com", password="secure-password", is_staff=True)
        self.manager.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="catalog",
            codename__in=("view_category", "add_category", "change_category", "delete_category"),
        ))
        self.client.force_login(self.manager)

    def test_staff_can_create_edit_and_delete_an_empty_category(self):
        response = self.client.post(reverse("dashboard:category-new"), {
            "name": "Smart Technology", "slug": "", "description": "Connected home systems.",
            "order": "2", "is_published": "on",
        })
        category = Category.objects.get(name="Smart Technology")
        self.assertRedirects(response, reverse("dashboard:categories"))
        self.assertEqual(category.slug, "smart-technology")
        self.assertTrue(category.is_published)
        self.assertContains(self.client.get(reverse("catalogue:product-list")), category.name)

        response = self.client.post(reverse("dashboard:category-edit", args=[category.pk]), {
            "name": "Smart Technology", "slug": "smart-tech", "description": "Updated.", "order": "3",
        })
        category.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:categories"))
        self.assertEqual(category.slug, "smart-tech")
        self.assertFalse(category.is_published)

        delete_url = reverse("dashboard:category-delete", args=[category.pk])
        self.assertContains(self.client.get(delete_url), "Delete category")
        self.client.post(delete_url)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_category_with_products_cannot_be_deleted(self):
        category = Category.objects.create(name="Security", slug="security")
        Product.objects.create(
            category=category, name="Camera", slug="camera", sku="CAM-001",
            short_description="Camera.", description="Camera description.", price="1.00",
        )
        url = reverse("dashboard:category-delete", args=[category.pk])

        self.assertContains(self.client.get(url), "Reassign those products")
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse("dashboard:categories"))
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
