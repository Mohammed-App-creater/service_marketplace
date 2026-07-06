from rest_framework.routers import DefaultRouter

from .views import DeviceTokenViewSet, NotificationLogViewSet

app_name = "notifications"

router = DefaultRouter()
router.register("device-tokens", DeviceTokenViewSet, basename="device-token")
router.register("notifications", NotificationLogViewSet, basename="notification")

urlpatterns = router.urls
