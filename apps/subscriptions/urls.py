from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SubscriptionPlanViewSet, VendorSubscriptionView

app_name = "subscriptions"

router = DefaultRouter()
router.register("subscription-plans", SubscriptionPlanViewSet, basename="subscription-plan")

urlpatterns = [
    path("vendors/me/subscription/", VendorSubscriptionView.as_view(), name="vendor-subscription"),
] + router.urls
