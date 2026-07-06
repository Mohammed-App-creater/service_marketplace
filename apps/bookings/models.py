from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedUUIDModel


class BookingStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    NO_SHOW = "no_show", _("No-show")


# Statuses that occupy a time slot (block overlapping bookings).
ACTIVE_STATUSES = [BookingStatus.PENDING, BookingStatus.CONFIRMED]


class CancelledBy(models.TextChoices):
    CUSTOMER = "customer", _("Customer")
    VENDOR = "vendor", _("Vendor")
    ADMIN = "admin", _("Admin")


class Booking(TimeStampedUUIDModel):
    """A customer's appointment with a vendor for one or more services.

    Services are attached as BookingItem line items (the mobile app books
    multiple services in one appointment). The slot spans the combined
    duration. Double-booking is prevented at the DB level via a partial
    exclusion constraint on (vendor, slot) for active statuses.
    """

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.PROTECT, related_name="bookings")

    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    # Stored range [start, end) — the exclusion constraint operates on this.
    slot = DateTimeRangeField()

    status = models.CharField(
        max_length=16, choices=BookingStatus.choices, default=BookingStatus.PENDING, db_index=True
    )
    cancelled_by = models.CharField(
        max_length=16, choices=CancelledBy.choices, null=True, blank=True
    )
    cancellation_reason = models.CharField(max_length=200, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    # Price snapshots taken at booking time (services may change later).
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["customer", "status"]),
        ]
        constraints = [
            ExclusionConstraint(
                name="excl_vendor_overlapping_active_booking",
                expressions=[
                    ("vendor", RangeOperators.EQUAL),
                    ("slot", RangeOperators.OVERLAPS),
                ],
                condition=Q(status__in=ACTIVE_STATUSES),
            ),
        ]

    def __str__(self):
        return f"{self.customer_id} @ {self.vendor_id} [{self.scheduled_start:%Y-%m-%d %H:%M}]"

    @property
    def is_active(self):
        return self.status in ACTIVE_STATUSES


class BookingItem(TimeStampedUUIDModel):
    """One service line within a booking, with price/duration snapshots."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(
        "catalog.Service", on_delete=models.PROTECT, related_name="booking_items"
    )
    service_name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["booking", "service"], name="unique_booking_service"),
        ]

    def __str__(self):
        return f"{self.booking_id}: {self.service_name}"
