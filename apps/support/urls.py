from rest_framework.routers import DefaultRouter

from .views import ComplaintViewSet

app_name = "support"

router = DefaultRouter()
router.register("complaints", ComplaintViewSet, basename="complaint")

urlpatterns = router.urls
