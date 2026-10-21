"""Top-level URL configuration.

Public and operational app routes are added progressively in later delivery
stages. The health endpoint remains deliberately tiny and unauthenticated so a
hosting provider can determine whether the process is available.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.core.views import health_check

urlpatterns = [
    path("", include("apps.core.urls")),
    path("services/", include("apps.services.urls")),
    path("projects/", include("apps.projects.urls")),
    path("products/", include("apps.catalog.urls")),
    path("cart/", include("apps.cart.urls")),
    path("account/", include("apps.accounts.urls")),
    path("orders/", include("apps.orders.urls")),
    path("payments/", include("apps.payments.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.enquiries.urls")),
    path("", include("apps.bookings.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("health/", health_check, name="health-check"),
]
if settings.ADMIN_URL:
    urlpatterns.append(path(f"{settings.ADMIN_URL}/", admin.site.urls))


handler400 = "apps.core.views.error_400"
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"


from django.conf import settings
from django.conf.urls.static import static


# his enables local media serving during development. It will not recreate missing images, and it won't enable this development-only route when DEBUG=False.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )