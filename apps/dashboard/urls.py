"""Private staff dashboard routes."""

from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.overview, name="overview"),
    path("products/", views.product_list, name="products"),
    path("categories/", views.category_list, name="categories"),
    path("categories/new/", views.category_edit, name="category-new"),
    path("categories/<int:pk>/", views.category_edit, name="category-edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category-delete"),
    path("products/new/", views.product_edit, name="product-new"),
    path("products/<int:pk>/", views.product_edit, name="product-edit"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:reference>/", views.order_detail, name="order-detail"),
    path("customers/", views.customers, name="customers"),
    path("enquiries/", views.enquiries, name="enquiries"),
    path("enquiries/<int:pk>/delete/", views.enquiry_delete, name="enquiry-delete"),
    path("bookings/", views.bookings, name="bookings"),
    path("content/", views.content_hub, name="content"),
    path("content/services/", views.service_list, name="services"),
    path("content/services/new/", views.service_edit, name="service-new"),
    path("content/services/<int:pk>/", views.service_edit, name="service-edit"),
    path("content/services/<int:pk>/delete/", views.service_delete, name="service-delete"),
    path("content/projects/", views.project_list, name="projects"),
    path("content/projects/new/", views.project_edit, name="project-new"),
    path("content/projects/<int:pk>/", views.project_edit, name="project-edit"),
    path("content/<slug:content_type>/", views.editorial_list, name="editorial-list"),
    path("content/<slug:content_type>/new/", views.editorial_edit, name="editorial-new"),
    path("content/<slug:content_type>/<int:pk>/", views.editorial_edit, name="editorial-edit"),
    path("settings/", views.settings, name="settings"),
    path("activity/", views.activity_list, name="activity"),
    path("activity/<int:pk>/delete/", views.activity_delete, name="activity-delete"),
    path("activity/clear/", views.activity_clear, name="activity-clear"),
    path("staff/", views.staff_list, name="staff"),
    path("staff/profile/", views.staff_profile, name="staff_profile"),
    path("staff/new/", views.staff_create, name="staff-new"),
    path("staff/<int:pk>/", views.staff_edit, name="staff-edit"),
    path("roles/", views.role_list, name="roles"),
    path("roles/new/", views.role_edit, name="role-new"),
    path("roles/<int:pk>/", views.role_edit, name="role-edit"),
]
