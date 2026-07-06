from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from apps.bookings.views import AdminBookingViewSet
from apps.support.views import AdminComplaintViewSet
from apps.vendors.views import AdminVendorViewSet

# Admin platform-management API (FR-301/302/303).
admin_router = DefaultRouter()
admin_router.register("vendors", AdminVendorViewSet, basename="admin-vendor")
admin_router.register("bookings", AdminBookingViewSet, basename="admin-booking")
admin_router.register("complaints", AdminComplaintViewSet, basename="admin-complaint")

api_v1 = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.catalog.urls")),
    path("", include("apps.vendors.urls")),
    path("", include("apps.subscriptions.urls")),
    path("", include("apps.bookings.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.support.urls")),
    path("admin/", include((admin_router.urls, "admin-api"), namespace="admin-api")),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "api-v1"))),
    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
