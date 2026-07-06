from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, BookingItem, BookingStatus
from apps.common.exceptions import DomainError
from apps.common.permissions import IsVendor


def _vendor_or_400(request):
    vendor = getattr(request.user, "vendor", None)
    if vendor is None:
        raise DomainError(_("Register a vendor profile first."))
    return vendor


class VendorDashboardView(APIView):
    """FR-230..233 — vendor analytics summary."""

    permission_classes = [IsVendor]

    def get(self, request):
        vendor = _vendor_or_400(request)

        now = timezone.localtime()
        today = now.date()
        month_start = today.replace(day=1)

        bookings = Booking.objects.filter(vendor=vendor)
        completed = bookings.filter(status=BookingStatus.COMPLETED)

        daily_total = bookings.filter(scheduled_start__date=today).count()  # FR-230
        monthly_total = bookings.filter(scheduled_start__date__gte=month_start).count()  # FR-230

        # Estimated revenue from completed bookings (FR-231) — booking totals
        # snapshot service prices + fee at booking time.
        revenue = completed.aggregate(total=Sum("subtotal"))["total"] or 0

        # Repeat customers: customers with >1 completed booking (FR-232).
        repeat_customers = (
            completed.values("customer").annotate(n=Count("id")).filter(n__gt=1).count()
        )

        return Response(
            {
                "daily_bookings": daily_total,
                "monthly_bookings": monthly_total,
                "estimated_revenue": revenue,
                "repeat_customers": repeat_customers,
                "average_rating": float(vendor.rating_avg),  # FR-233
                "rating_count": vendor.rating_count,
            }
        )


class VendorAnalyticsView(APIView):
    """Chart-ready analytics for the vendor report screen:
    monthly income, weekly appointment counts, bookings by service."""

    permission_classes = [IsVendor]

    @extend_schema(
        parameters=[
            OpenApiParameter("months", int, description="Months of income history (default 6)")
        ]
    )
    def get(self, request):
        vendor = _vendor_or_400(request)
        try:
            months = min(max(int(request.query_params.get("months", 6)), 1), 24)
        except ValueError:
            months = 6

        now = timezone.localtime()
        today = now.date()

        completed = Booking.objects.filter(vendor=vendor, status=BookingStatus.COMPLETED)

        # Monthly income (completed bookings' subtotal), oldest first.
        window_start = (today.replace(day=1) - timedelta(days=31 * (months - 1))).replace(day=1)
        monthly = (
            completed.filter(scheduled_start__date__gte=window_start)
            .annotate(month=TruncMonth("scheduled_start"))
            .values("month")
            .annotate(income=Sum("subtotal"), bookings=Count("id"))
            .order_by("month")
        )
        monthly_income = [
            {
                "month": row["month"].date().isoformat(),
                "income": row["income"] or 0,
                "bookings": row["bookings"],
            }
            for row in monthly
        ]

        # Appointments per day, last 7 days (all statuses).
        week_start = today - timedelta(days=6)
        per_day = dict(
            Booking.objects.filter(
                vendor=vendor,
                scheduled_start__date__gte=week_start,
                scheduled_start__date__lte=today,
            )
            .values_list("scheduled_start__date")
            .annotate(n=Count("id"))
        )
        weekly_appointments = [
            {
                "date": (week_start + timedelta(days=i)).isoformat(),
                "count": per_day.get(week_start + timedelta(days=i), 0),
            }
            for i in range(7)
        ]

        # Bookings by service (completed, all time).
        by_service = (
            BookingItem.objects.filter(
                booking__vendor=vendor, booking__status=BookingStatus.COMPLETED
            )
            .values("service_name")
            .annotate(count=Count("id"), income=Sum("price"))
            .order_by("-count")[:20]
        )

        return Response(
            {
                "monthly_income": monthly_income,
                "weekly_appointments": weekly_appointments,
                "bookings_by_service": list(by_service),
            }
        )
