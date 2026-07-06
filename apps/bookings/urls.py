from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, VendorBookingViewSet

app_name = "bookings"

router = DefaultRouter()
router.register("vendors/me/bookings", VendorBookingViewSet, basename="vendor-booking")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = router.urls
