"""Booking domain logic: creation (concurrency-safe), availability, transitions."""

from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from psycopg.types.range import Range

from apps.common.exceptions import ConflictError, DomainError
from apps.vendors.models import Vendor, VendorStatus

from .models import ACTIVE_STATUSES, Booking, BookingStatus, CancelledBy


def _validate_bookable(vendor, services, start, end):
    """Business validations run inside the transaction before the DB constraint."""
    now = timezone.now()
    lead = timedelta(minutes=settings.BOOKING_MIN_LEAD_MINUTES)
    if start < now + lead:
        raise DomainError(
            _("Please pick a time at least %(m)s minutes from now.")
            % {"m": settings.BOOKING_MIN_LEAD_MINUTES}
        )
    if not vendor.is_verified:
        raise DomainError(_("This vendor is not available for booking."))
    if vendor.status != VendorStatus.OPEN:
        raise DomainError(_("This vendor is currently closed."))
    for service in services:
        if not service.is_active or service.vendor_id != vendor.id:
            raise DomainError(_("The selected service is unavailable."))

    # Within working hours for that weekday.
    local_start = timezone.localtime(start)
    local_end = timezone.localtime(end)
    wh = vendor.working_hours.filter(day_of_week=local_start.weekday()).first()
    if wh is None or wh.is_closed or wh.open_time is None or wh.close_time is None:
        raise DomainError(_("The vendor is not open on the selected day."))
    if not (wh.open_time <= local_start.time() and local_end.time() <= wh.close_time):
        raise DomainError(_("The selected time is outside the vendor's working hours."))

    # Not inside a schedule block.
    if vendor.schedule_blocks.filter(start_datetime__lt=end, end_datetime__gt=start).exists():
        raise DomainError(_("The selected time is unavailable."))


def _quantize(amount):
    from decimal import Decimal

    return Decimal(amount).quantize(Decimal("0.01"))


@transaction.atomic
def create_booking(*, customer, vendor_id, service_ids, scheduled_start, notes="") -> Booking:
    """Create a pending booking for one or more services, preventing
    double-booking under concurrency.

    Layer 1: select_for_update on the vendor serializes concurrent attempts.
    Layer 2: the DB exclusion constraint is the final arbiter — an IntegrityError
    is translated to HTTP 409.

    The slot spans the combined duration of all selected services. Prices are
    snapshotted onto BookingItem rows; a platform service fee
    (settings.BOOKING_SERVICE_FEE_PERCENT) is added to the total.
    """
    from decimal import Decimal

    from apps.catalog.models import Service

    from .models import BookingItem

    if not service_ids:
        raise DomainError(_("Select at least one service."))

    vendor = Vendor.objects.select_for_update().select_related("owner").filter(id=vendor_id).first()
    if vendor is None:
        raise DomainError(_("Vendor not found."))

    services = list(Service.objects.filter(id__in=service_ids, vendor_id=vendor_id, is_active=True))
    if len(services) != len(set(service_ids)):
        raise DomainError(_("One or more selected services are unavailable."))

    total_minutes = sum(s.duration_minutes for s in services)
    end = scheduled_start + timedelta(minutes=total_minutes)
    _validate_bookable(vendor, services, scheduled_start, end)

    subtotal = _quantize(sum((s.effective_price for s in services), Decimal("0")))
    fee_percent = Decimal(str(settings.BOOKING_SERVICE_FEE_PERCENT))
    service_fee = _quantize(subtotal * fee_percent / Decimal("100"))

    booking = Booking(
        customer=customer,
        vendor=vendor,
        scheduled_start=scheduled_start,
        scheduled_end=end,
        slot=Range(scheduled_start, end, bounds="[)"),
        status=BookingStatus.PENDING,
        notes=notes,
        subtotal=subtotal,
        service_fee=service_fee,
        total=subtotal + service_fee,
    )
    try:
        booking.save()
    except IntegrityError as exc:
        if "excl_vendor_overlapping_active_booking" in str(exc):
            raise ConflictError(_("That time slot was just taken. Please pick another.")) from exc
        raise

    BookingItem.objects.bulk_create(
        [
            BookingItem(
                booking=booking,
                service=s,
                service_name=s.name,
                price=_quantize(s.effective_price),
                duration_minutes=s.duration_minutes,
            )
            for s in services
        ]
    )

    _dispatch_created(booking)
    return booking


def _dispatch_created(booking):
    """Fire notifications after commit (FR-123 customer, FR-220 vendor)."""
    from apps.notifications import services as notify

    def _send():
        notify.publish_realtime(
            recipient=booking.vendor.owner,
            channel_name=f"vendor.{booking.vendor_id}",
            event="booking.created",
            payload={"booking_id": str(booking.id)},
        )
        notify.send_push(
            recipient=booking.vendor.owner,
            title=str(_("New booking")),
            body=str(_("You have a new booking request.")),
            template_key="booking.created.vendor",
        )
        if booking.customer.phone:
            notify.send_sms(
                recipient=booking.customer,
                to=str(booking.customer.phone),
                template_key="booking.created.customer",
                message=str(_("Your booking is placed and awaiting confirmation.")),
            )

    transaction.on_commit(_send)


def _dispatch_status_change(booking, event):
    from apps.notifications import services as notify

    def _send():
        notify.send_push(
            recipient=booking.customer,
            title=str(_("Booking update")),
            body=str(_("Your booking status is now %(s)s.") % {"s": booking.get_status_display()}),
            template_key=f"booking.{event}.customer",
        )

    transaction.on_commit(_send)


# --- State transitions -----------------------------------------------------


def _require_status(booking, allowed):
    if booking.status not in allowed:
        raise DomainError(_("This action is not allowed for the booking's current state."))


@transaction.atomic
def accept_booking(booking):
    _require_status(booking, [BookingStatus.PENDING])
    booking.status = BookingStatus.CONFIRMED
    booking.save(update_fields=["status", "updated_at"])
    _dispatch_status_change(booking, "confirmed")
    return booking


@transaction.atomic
def decline_booking(booking, reason=""):
    _require_status(booking, [BookingStatus.PENDING])
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_by = CancelledBy.VENDOR
    booking.cancellation_reason = reason
    booking.save(update_fields=["status", "cancelled_by", "cancellation_reason", "updated_at"])
    _dispatch_status_change(booking, "declined")
    return booking


@transaction.atomic
def cancel_booking(booking, *, by=CancelledBy.CUSTOMER, reason=""):
    """FR-124 — cancel before the appointment time."""
    _require_status(booking, [BookingStatus.PENDING, BookingStatus.CONFIRMED])
    if booking.scheduled_start <= timezone.now():
        raise DomainError(_("Bookings can only be cancelled before the appointment time."))
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_by = by
    booking.cancellation_reason = reason
    booking.save(update_fields=["status", "cancelled_by", "cancellation_reason", "updated_at"])
    _dispatch_status_change(booking, "cancelled")
    return booking


@transaction.atomic
def admin_force_cancel(booking, reason=""):
    """Admin dispute resolution — cancel regardless of appointment time."""
    _require_status(
        booking, [BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.NO_SHOW]
    )
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_by = CancelledBy.ADMIN
    booking.cancellation_reason = reason
    booking.save(update_fields=["status", "cancelled_by", "cancellation_reason", "updated_at"])
    _dispatch_status_change(booking, "cancelled")
    return booking


@transaction.atomic
def mark_completed(booking):
    _require_status(booking, [BookingStatus.CONFIRMED])
    booking.status = BookingStatus.COMPLETED
    booking.save(update_fields=["status", "updated_at"])
    return booking


@transaction.atomic
def mark_no_show(booking):
    _require_status(booking, [BookingStatus.CONFIRMED, BookingStatus.PENDING])
    booking.status = BookingStatus.NO_SHOW
    booking.save(update_fields=["status", "updated_at"])
    return booking


# --- Availability ----------------------------------------------------------


def available_slots(*, vendor, services, date):
    """Return bookable start datetimes for a vendor on a given date, sized to
    the combined duration of the selected services.

    Advisory only — the exclusion constraint remains authoritative against races.
    """
    wh = vendor.working_hours.filter(day_of_week=date.weekday()).first()
    if wh is None or wh.is_closed or wh.open_time is None or wh.close_time is None:
        return []

    tz = timezone.get_current_timezone()
    total_minutes = sum(s.duration_minutes for s in services)
    duration = timedelta(minutes=total_minutes)
    granularity = timedelta(minutes=settings.BOOKING_SLOT_GRANULARITY_MINUTES)
    now = timezone.now()
    lead = timedelta(minutes=settings.BOOKING_MIN_LEAD_MINUTES)

    day_open = timezone.make_aware(datetime.combine(date, wh.open_time), tz)
    day_close = timezone.make_aware(datetime.combine(date, wh.close_time), tz)

    # Existing active bookings and blocks intersecting the day window.
    active = list(
        Booking.objects.filter(
            vendor=vendor,
            status__in=ACTIVE_STATUSES,
            scheduled_start__lt=day_close,
            scheduled_end__gt=day_open,
        ).values_list("scheduled_start", "scheduled_end")
    )
    blocks = list(
        vendor.schedule_blocks.filter(
            start_datetime__lt=day_close, end_datetime__gt=day_open
        ).values_list("start_datetime", "end_datetime")
    )

    def overlaps(a_start, a_end, ranges):
        return any(a_start < r_end and a_end > r_start for r_start, r_end in ranges)

    slots = []
    cursor = day_open
    while cursor + duration <= day_close:
        slot_end = cursor + duration
        if (
            cursor >= now + lead
            and not overlaps(cursor, slot_end, active)
            and not overlaps(cursor, slot_end, blocks)
        ):
            slots.append(cursor)
        cursor += granularity
    return slots
