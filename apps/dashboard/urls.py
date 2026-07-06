from django.urls import path

from .views import VendorAnalyticsView, VendorDashboardView

app_name = "dashboard"

urlpatterns = [
    path("vendors/me/dashboard/", VendorDashboardView.as_view(), name="vendor-dashboard"),
    path("vendors/me/analytics/", VendorAnalyticsView.as_view(), name="vendor-analytics"),
]
