from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CustomerProfileView, CustomerReviewViewSet, ReviewViewSet

app_name = "reviews"

router = DefaultRouter()
router.register("reviews", ReviewViewSet, basename="review")
router.register("customer-reviews", CustomerReviewViewSet, basename="customer-review")

urlpatterns = [
    path("customers/<uuid:pk>/", CustomerProfileView.as_view(), name="customer-profile"),
] + router.urls
