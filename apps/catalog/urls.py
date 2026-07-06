from rest_framework.routers import DefaultRouter

from .views import ServiceViewSet

app_name = "catalog"

router = DefaultRouter()
router.register("vendors/me/services", ServiceViewSet, basename="me-service")

urlpatterns = router.urls
