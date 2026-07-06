from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    FavoriteViewSet,
    ScheduleBlockViewSet,
    VendorMeView,
    VendorViewSet,
    WorkingHoursViewSet,
)

app_name = "vendors"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("favorites", FavoriteViewSet, basename="favorite")
router.register("vendors/me/working-hours", WorkingHoursViewSet, basename="me-working-hours")
router.register("vendors/me/blocks", ScheduleBlockViewSet, basename="me-blocks")
router.register("vendors", VendorViewSet, basename="vendor")

me_urls = [
    path(
        "vendors/me/",
        VendorMeView.as_view({"get": "retrieve", "post": "create", "patch": "partial_update"}),
        name="vendor-me",
    ),
    path(
        "vendors/me/status/",
        VendorMeView.as_view({"patch": "set_status"}),
        name="vendor-me-status",
    ),
]

# me_urls must precede the router so 'vendors/me/...' is not captured by the
# 'vendors/<pk>' detail route.
urlpatterns = me_urls + router.urls
