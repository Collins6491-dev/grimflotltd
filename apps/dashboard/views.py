"""Custom staff operations interface built on the platform's domain services."""

from __future__ import annotations

import secrets

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group
from django.contrib.admin.views.decorators import staff_member_required as django_staff_member_required
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.accounts.forms import StaffAuthenticationForm
from apps.bookings.models import ConsultationBooking
from apps.catalog.models import Category, InventoryRecord, Product, StockMovement
from apps.core.models import (
    BrandingSettings, CompanyProfile, FAQ, HeroSlide, HomepageCapability,
    HomepageProcessStep, HomepageSettings, SocialLink,
)
from apps.enquiries.models import Enquiry
from apps.orders.forms import OrderStatusForm
from apps.orders.models import Order
from apps.orders.services import change_order_status
from apps.payments.models import PaymentTransaction
from apps.projects.models import Project
from apps.services.models import Service

from .forms import (
    BrandingSettingsForm,
    CategoryDashboardForm,
    CompanyProfileForm,
    HomepageSettingsForm,
    FAQDashboardForm,
    HeroSlideDashboardForm,
    HomepageCapabilityDashboardForm,
    HomepageProcessStepDashboardForm,
    InventoryDashboardForm,
    ProductDashboardForm,
    ProjectDashboardForm,
    ServiceDashboardForm,
    SocialLinkDashboardForm,
    StaffCreateForm,
    StaffEditForm,
    RoleForm,
)
from .models import AuditEvent


def staff_member_required(view):
    """Protect dashboard views with the dedicated staff sign-in route."""
    return django_staff_member_required(view, login_url="dashboard:login")


def dashboard_permission(permission: str):
    """Require dashboard access and a real Django permission server-side."""
    return lambda view: staff_member_required(permission_required(permission, raise_exception=True)(view))


def _safe_next(request, fallback: str) -> str:
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}):
        return candidate
    return fallback


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Keep operations access separate from customer account sign-in."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect(_safe_next(request, "dashboard:overview"))

    form = StaffAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next(request, "dashboard:overview"))
    return render(
        request,
        "dashboard/login.html",
        {
            "form": form,
            "next_url": request.POST.get("next") or request.GET.get("next", ""),
            "page_title": "Dashboard sign in",
        },
    )


@require_http_methods(["POST"])
def logout_view(request):
    """End a staff session and return to the dashboard sign-in page."""
    logout(request)
    messages.info(request, "You have been signed out of the operations dashboard.")
    return redirect("dashboard:login")


EDITORIAL_CONTENT = {
    "hero-slides": ("Hero slides", HeroSlide, HeroSlideDashboardForm, "title", "summary"),
    "faqs": ("Frequently asked questions", FAQ, FAQDashboardForm, "question", "answer"),
    "capabilities": ("Homepage capabilities", HomepageCapability, HomepageCapabilityDashboardForm, "title", "summary"),
    "process-steps": ("Homepage process steps", HomepageProcessStep, HomepageProcessStepDashboardForm, "title", "summary"),
    "social-links": ("Social links", SocialLink, SocialLinkDashboardForm, "label", "url"),
}


def _audit(request, action: str, instance, summary: str, **metadata):
    AuditEvent.objects.create(
        actor=request.user,
        action=action,
        object_type=instance._meta.label_lower,
        object_id=str(instance.pk or ""),
        summary=summary,
        metadata=metadata,
    )


@staff_member_required
def overview(request):
    # Database comparisons belong in the query so the same status is reliable across staff views.
    low_stock = InventoryRecord.objects.select_related("product").filter(quantity_on_hand__lte=F("reorder_level"))
    return render(
        request,
        "dashboard/overview.html",
        {
            "order_count": Order.objects.count(),
            "pending_orders": Order.objects.filter(status=Order.PENDING_PAYMENT).count(),
            "unread_enquiries": Enquiry.objects.filter(status=Enquiry.NEW).count(),
            "pending_bookings": ConsultationBooking.objects.filter(status=ConsultationBooking.PENDING).count(),
            "low_stock": low_stock[:8],
            "recent_orders": Order.objects.select_related("user").all()[:8],
            "recent_events": AuditEvent.objects.select_related("actor").all()[:8],
            "page_title": "Operations overview",
        },
    )

@staff_member_required
def staff_profile(request):
    """Display the currently authenticated staff member's profile."""

    user = request.user

    return render(
        request,
        "dashboard/staff_profile.html",
        {
            "profile_user": user,
            "page_title": "My Staff Profile",
            "staff_groups": user.groups.all(),
            "staff_permissions": user.get_all_permissions(),
        },
    )


@staff_member_required
def product_list(request):
    products = Product.objects.select_related("category", "inventory").all()
    return render(request, "dashboard/product_list.html", {"products": products, "page_title": "Products"})


@dashboard_permission("catalog.view_category")
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products")).all()
    return render(request, "dashboard/category_list.html", {"categories": categories, "page_title": "Categories"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def category_edit(request, pk: int | None = None):
    required_permission = "catalog.change_category" if pk else "catalog.add_category"
    if not request.user.has_perm(required_permission):
        raise PermissionDenied("You do not have permission to save categories.")
    category = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryDashboardForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        _audit(request, "updated" if pk else "created", category, f"Category {category.name} saved.")
        messages.success(request, f"Category {category.name} was saved.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/model_form.html", {
        "form": form,
        "heading": "Edit category" if category else "Add category",
        "page_title": "Category editor",
    })


@dashboard_permission("catalog.delete_category")
@require_http_methods(["GET", "POST"])
def category_delete(request, pk: int):
    category = get_object_or_404(Category, pk=pk)
    product_count = category.products.count()
    if request.method == "POST":
        if product_count:
            messages.error(request, f"{category.name} cannot be deleted while it contains {product_count} product(s). Reassign them first.")
        else:
            name = category.name
            _audit(request, "deleted", category, f"Category {name} deleted.")
            category.delete()
            messages.success(request, f"Category {name} was deleted.")
        return redirect("dashboard:categories")
    return render(request, "dashboard/confirm_delete.html", {
        "object": category,
        "object_label": "category",
        "related_products": product_count,
        "deletion_blocked": bool(product_count),
        "cancel_url": "dashboard:categories",
        "page_title": "Delete category",
    })

@staff_member_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk: int | None = None):
    from apps.catalog.models import ProductImage

    product = get_object_or_404(Product, pk=pk) if pk else None

    product_form = ProductDashboardForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )

    inventory_instance = (
        product.inventory
        if product and hasattr(product, "inventory")
        else None
    )

    inventory_form = InventoryDashboardForm(
        request.POST or None,
        instance=inventory_instance,
    )

    if request.method == "POST":
        if product_form.is_valid() and inventory_form.is_valid():

            before = (
                inventory_instance.quantity_on_hand
                if inventory_instance
                else 0
            )

            inventory = inventory_form.save(commit=False)

            if inventory.reserved_quantity > inventory.quantity_on_hand:
                inventory_form.add_error(
                    "quantity_on_hand",
                    "On-hand stock cannot be lower than units already reserved.",
                )

            else:
                uploaded_image = product_form.cleaned_data.get("image")

                with transaction.atomic():
                    product = product_form.save()

                    inventory.product = product
                    inventory.save()

                    if uploaded_image:
                        primary_image = product.images.filter(
                            is_primary=True
                        ).first()

                        if primary_image:
                            primary_image.image = uploaded_image
                            primary_image.alt_text = product.name

                            primary_image.save(
                                update_fields=["image", "alt_text"]
                            )

                        else:
                            ProductImage.objects.create(
                                product=product,
                                image=uploaded_image,
                                alt_text=product.name,
                                is_primary=True,
                                order=0,
                            )

                    if inventory.quantity_on_hand != before:
                        StockMovement.objects.create(
                            product=product,
                            quantity_delta=(
                                inventory.quantity_on_hand - before
                            ),
                            movement_type=StockMovement.ADJUSTMENT,
                            note="Updated through the staff dashboard.",
                            actor=request.user,
                        )

                _audit(
                    request,
                    "updated" if pk else "created",
                    product,
                    f"Product {product.sku} saved.",
                )

                messages.success(
                    request,
                    "Product and inventory were saved.",
                )

                return redirect(
                    "dashboard:product-edit",
                    pk=product.pk,
                )

    return render(
        request,
        "dashboard/product_form.html",
        {
            "form": product_form,
            "secondary_form": inventory_form,
            "product": product,
            "heading": (
                "Edit product" if product else "Create product"
            ),
            "page_title": "Product editor",
        },
    )

@staff_member_required
def order_list(request):
    orders = Order.objects.select_related("user").prefetch_related("payments").all()
    return render(request, "dashboard/order_list.html", {"orders": orders, "page_title": "Order operations"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def order_detail(request, reference: str):
    order = get_object_or_404(Order.objects.prefetch_related("items", "payments", "status_events"), reference=reference)
    form = OrderStatusForm(request.POST or None, initial={"status": order.status})
    if request.method == "POST" and form.is_valid():
        try:
            change_order_status(order=order, status=form.cleaned_data["status"], actor=request.user, note=form.cleaned_data["note"])
        except Exception as error:
            form.add_error(None, str(error))
        else:
            _audit(request, "status_changed", order, f"Order {order.reference} set to {form.cleaned_data['status']}.")
            messages.success(request, "Order status updated.")
            return redirect("dashboard:order-detail", reference=order.reference)
    return render(request, "dashboard/order_detail.html", {"order": order, "form": form, "page_title": order.reference})


@staff_member_required
def customers(request):
    customers = User.objects.annotate(order_total=Count("orders"), paid_total=Sum("orders__total", filter=Q(orders__status__in=[Order.PAID, Order.PROCESSING, Order.SHIPPED, Order.COMPLETED]))).order_by("-date_joined")
    return render(request, "dashboard/customers.html", {"customers": customers, "page_title": "Customers"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def enquiries(request):
    if request.method == "POST":
        enquiry = get_object_or_404(Enquiry, pk=request.POST.get("enquiry_id"))
        status = request.POST.get("status")
        if status in dict(Enquiry.STATUS_CHOICES):
            enquiry.status = status
            enquiry.assigned_to = request.user
            enquiry.save(update_fields=("status", "assigned_to", "updated_at"))
            _audit(request, "status_changed", enquiry, f"Enquiry from {enquiry.email} set to {status}.")
    return render(request, "dashboard/enquiries.html", {"enquiries": Enquiry.objects.select_related("assigned_to"), "page_title": "Enquiries"})


@dashboard_permission("enquiries.delete_enquiry")
@require_http_methods(["GET", "POST"])
def enquiry_delete(request, pk: int):
    """Confirm and permanently remove one enquiry without affecting its assignee."""
    enquiry = get_object_or_404(Enquiry.objects.select_related("assigned_to"), pk=pk)
    if request.method == "POST":
        name, email = enquiry.name, enquiry.email
        # Enquiry has no dependent business records.  Its optional assignee is
        # retained because the relationship points from Enquiry to User.
        with transaction.atomic():
            _audit(request, "deleted", enquiry, f"Enquiry from {email} ({name}) deleted.")
            enquiry.delete()
        messages.success(request, f"Enquiry from {name} was permanently deleted.")
        return redirect("dashboard:enquiries")
    return render(request, "dashboard/confirm_delete.html", {
        "object": enquiry,
        "object_label": "enquiry",
        "cancel_url": "dashboard:enquiries",
        "page_title": "Delete enquiry",
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def bookings(request):
    if request.method == "POST":
        booking = get_object_or_404(ConsultationBooking, pk=request.POST.get("booking_id"))
        status = request.POST.get("status")
        if status in dict(ConsultationBooking.STATUS_CHOICES):
            booking.status = status
            booking.assigned_to = request.user
            booking.save(update_fields=("status", "assigned_to", "updated_at"))
            _audit(request, "status_changed", booking, f"Booking for {booking.name} set to {status}.")
    return render(request, "dashboard/bookings.html", {"bookings": ConsultationBooking.objects.select_related("assigned_to"), "page_title": "Consultations"})


@staff_member_required
def content_hub(request):
    return render(request, "dashboard/content_hub.html", {"service_count": Service.objects.count(), "project_count": Project.objects.count(), "page_title": "Content management"})


def _editorial_definition(content_type: str):
    try:
        return EDITORIAL_CONTENT[content_type]
    except KeyError as error:
        raise Http404("Unknown editorial content type.") from error


@staff_member_required
def editorial_list(request, content_type: str):
    heading, model, _, label_field, summary_field = _editorial_definition(content_type)
    rows = [
        {
            "instance": item,
            "label": getattr(item, label_field),
            "summary": getattr(item, summary_field, ""),
            "published": getattr(item, "is_published", None),
            "order": getattr(item, "order", None),
        }
        for item in model.objects.all()
    ]
    return render(request, "dashboard/editorial_list.html", {"heading": heading, "content_type": content_type, "rows": rows, "page_title": heading})


@staff_member_required
@require_http_methods(["GET", "POST"])
def editorial_edit(request, content_type: str, pk: int | None = None):
    heading, model, form_class, label_field, _ = _editorial_definition(content_type)
    instance = get_object_or_404(model, pk=pk) if pk else None
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        instance = form.save()
        label = getattr(instance, label_field)
        _audit(request, "updated" if pk else "created", instance, f"{heading}: {label} saved.")
        messages.success(request, f"{heading.rstrip('s')} saved.")
        return redirect("dashboard:editorial-edit", content_type=content_type, pk=instance.pk)
    return render(request, "dashboard/model_form.html", {"form": form, "heading": f"Edit {heading.rstrip('s')}" if instance else f"Create {heading.rstrip('s')}", "page_title": heading})


@dashboard_permission("services.view_service")
def service_list(request):
    return render(request, "dashboard/content_list.html", {"items": Service.objects.all(), "kind": "service", "page_title": "Service content"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def service_edit(request, pk: int | None = None):
    required_permission = "services.change_service" if pk else "services.add_service"
    if not request.user.has_perm(required_permission):
        raise PermissionDenied("You do not have permission to save services.")
    service = get_object_or_404(Service, pk=pk) if pk else None
    form = ServiceDashboardForm(request.POST or None, request.FILES or None, instance=service)
    if request.method == "POST" and form.is_valid():
        service = form.save()
        _audit(request, "updated" if pk else "created", service, f"Service {service.title} saved.")
        messages.success(request, "Service content saved.")
        return redirect("dashboard:service-edit", pk=service.pk)
    return render(request, "dashboard/model_form.html", {"form": form, "heading": "Edit service" if service else "Create service", "page_title": "Service editor"})


@dashboard_permission("services.delete_service")
@require_http_methods(["GET", "POST"])
def service_delete(request, pk: int):
    service = get_object_or_404(Service, pk=pk)
    related_projects = service.projects.count()
    if request.method == "POST":
        title = service.title
        # M2M project links are removed by Django; no project or customer data is deleted.
        service.delete()
        _audit(request, "deleted", service, f"Service {title} deleted.")
        messages.success(request, f"Service {title} was deleted.")
        return redirect("dashboard:services")
    return render(request, "dashboard/confirm_delete.html", {
        "object": service, "object_label": "service", "related_projects": related_projects,
        "cancel_url": "dashboard:services", "page_title": "Delete service",
    })


@dashboard_permission("dashboard.view_auditevent")
def activity_list(request):
    query = request.GET.get("q", "").strip()
    events = AuditEvent.objects.select_related("actor")
    if query:
        events = events.filter(Q(summary__icontains=query) | Q(action__icontains=query) | Q(actor__email__icontains=query))
    from django.core.paginator import Paginator
    page_obj = Paginator(events, 25).get_page(request.GET.get("page"))
    return render(request, "dashboard/activity_list.html", {"page_obj": page_obj, "query": query, "page_title": "Staff activity"})


@dashboard_permission("dashboard.delete_auditevent")
@require_http_methods(["POST"])
def activity_delete(request, pk: int):
    event = get_object_or_404(AuditEvent, pk=pk)
    event.delete()
    messages.success(request, "Activity record removed.")
    return redirect("dashboard:activity")


@dashboard_permission("dashboard.clear_auditevent")
@require_http_methods(["POST"])
def activity_clear(request):
    ids = request.POST.getlist("event_ids")
    if not ids:
        messages.error(request, "Select one or more activity records to clear.")
    else:
        deleted, _ = AuditEvent.objects.filter(pk__in=ids).delete()
        messages.success(request, f"{deleted} activity record(s) removed.")
    return redirect("dashboard:activity")


@dashboard_permission("accounts.manage_staff")
def staff_list(request):
    staff = User.objects.filter(is_staff=True).prefetch_related("groups").order_by("-date_joined")
    return render(request, "dashboard/staff_list.html", {"staff": staff, "page_title": "Staff management"})


def _send_setup_email(request, user):
    form = PasswordResetForm({"email": user.email})
    if not form.is_valid():
        return False
    try:
        form.save(request=request, use_https=request.is_secure(), email_template_name="accounts/password_reset_email.html", subject_template_name="accounts/password_reset_subject.txt")
    except Exception:
        return False
    return True


@dashboard_permission("accounts.manage_staff")
@require_http_methods(["GET", "POST"])
def staff_create(request):
    form = StaffCreateForm(request.POST or None)
    form.limit_roles(can_manage_privileged=request.user.is_superuser)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_staff = True
        # PasswordResetForm intentionally skips unusable-password accounts.
        # Store an unguessable one-time secret hash so the standard reset flow
        # can issue the staff member's password-setup link without a default.
        user.set_password(secrets.token_urlsafe(48))
        user.save()
        if form.cleaned_data["role"]:
            user.groups.add(form.cleaned_data["role"])
        _audit(request, "created", user, f"Staff account {user.email} created.")
        if _send_setup_email(request, user):
            messages.success(request, "Staff account created and password-setup email sent.")
        else:
            messages.warning(request, "Staff account created, but the password-setup email could not be sent.")
        return redirect("dashboard:staff-edit", pk=user.pk)
    return render(request, "dashboard/model_form.html", {"form": form, "heading": "Add staff member", "page_title": "Add staff"})


@dashboard_permission("accounts.manage_staff")
@require_http_methods(["GET", "POST"])
def staff_edit(request, pk: int):
    member = get_object_or_404(User, pk=pk, is_staff=True)
    if member.is_superuser and not request.user.is_superuser:
        raise PermissionDenied("Only a superuser can modify a superuser account.")
    form = StaffEditForm(request.POST or None, instance=member)
    form.limit_roles(can_manage_privileged=request.user.is_superuser)
    if request.method == "POST" and form.is_valid():
        if member == request.user and not form.cleaned_data["is_active"]:
            form.add_error("is_active", "You cannot deactivate your own account.")
        else:
            member = form.save()
            member.groups.clear()
            if form.cleaned_data["role"]:
                member.groups.add(form.cleaned_data["role"])
            _audit(request, "updated", member, f"Staff account {member.email} updated.")
            messages.success(request, "Staff account updated.")
            return redirect("dashboard:staff-edit", pk=member.pk)
    return render(request, "dashboard/model_form.html", {"form": form, "heading": "Edit staff member", "page_title": "Edit staff"})


@dashboard_permission("accounts.manage_roles")
def role_list(request):
    roles = Group.objects.prefetch_related("user_set").order_by("name")
    return render(request, "dashboard/role_list.html", {"roles": roles, "page_title": "Roles & permissions"})


@dashboard_permission("accounts.manage_roles")
@require_http_methods(["GET", "POST"])
def role_edit(request, pk: int | None = None):
    role = get_object_or_404(Group, pk=pk) if pk else None
    form = RoleForm(request.POST or None, instance=role)
    if request.method == "POST" and form.is_valid():
        role = form.save()
        _audit(request, "updated" if pk else "created", role, f"Role {role.name} saved.")
        messages.success(request, "Role saved.")
        return redirect("dashboard:roles")
    return render(request, "dashboard/model_form.html", {"form": form, "heading": "Edit role" if role else "Create role", "page_title": "Role editor"})


@staff_member_required
def project_list(request):
    return render(request, "dashboard/content_list.html", {"items": Project.objects.all(), "kind": "project", "page_title": "Project content"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def project_edit(request, pk: int | None = None):
    project = get_object_or_404(Project, pk=pk) if pk else None
    form = ProjectDashboardForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        _audit(request, "updated" if pk else "created", project, f"Project {project.title} saved.")
        messages.success(request, "Project content saved.")
        return redirect("dashboard:project-edit", pk=project.pk)
    return render(request, "dashboard/model_form.html", {"form": form, "heading": "Edit project" if project else "Create project", "page_title": "Project editor"})


@staff_member_required
@require_http_methods(["GET", "POST"])
def settings(request):
    company, _ = CompanyProfile.objects.get_or_create(site_id=1)
    branding, _ = BrandingSettings.objects.get_or_create(site_id=1)
    homepage, _ = HomepageSettings.objects.get_or_create(site_id=1)
    forms = {
        "company": CompanyProfileForm(request.POST or None, instance=company, prefix="company"),
        "branding": BrandingSettingsForm(request.POST or None, request.FILES or None, instance=branding, prefix="branding"),
        "homepage": HomepageSettingsForm(request.POST or None, request.FILES or None, instance=homepage, prefix="homepage"),
    }
    if request.method == "POST":
        section = request.POST.get("section")
        form = forms.get(section)
        if form and form.is_valid():
            instance = form.save()
            _audit(request, "updated", instance, f"{section.title()} settings saved.")
            messages.success(request, f"{section.title()} settings saved.")
            return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"forms": forms, "page_title": "Brand and site settings"})
