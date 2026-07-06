from datetime import timedelta

import pytest
from django.utils import timezone

from apps.bookings.models import BookingStatus
from apps.bookings.services import (
    accept_booking,
    available_slots,
    cancel_booking,
    create_booking,
    mark_completed,
)
from apps.common.exceptions import ConflictError, DomainError


def _future(hour=10):
    return (timezone.now() + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


@pytest.mark.django_db
def test_create_booking_success(customer, vendor, service):
    booking = create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=_future()
    )
    assert booking.status == BookingStatus.PENDING
    assert booking.scheduled_end == booking.scheduled_start + timedelta(minutes=30)


@pytest.mark.django_db
def test_sequential_overlap_raises_conflict(customer, vendor, service):
    start = _future()
    create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=start
    )
    with pytest.raises(ConflictError):
        create_booking(
            customer=customer,
            vendor_id=vendor.id,
            service_ids=[service.id],
            scheduled_start=start + timedelta(minutes=15),
        )


@pytest.mark.django_db
def test_booking_in_past_rejected(customer, vendor, service):
    past = timezone.now() - timedelta(hours=1)
    with pytest.raises(DomainError):
        create_booking(
            customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=past
        )


@pytest.mark.django_db
def test_cancel_after_appointment_time_blocked(customer, vendor, service):
    booking = create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=_future()
    )
    # Force the start into the past to simulate a passed appointment.
    booking.scheduled_start = timezone.now() - timedelta(minutes=5)
    booking.save(update_fields=["scheduled_start"])
    with pytest.raises(DomainError):
        cancel_booking(booking)


@pytest.mark.django_db
def test_cancel_frees_the_slot(customer, vendor, service):
    start = _future()
    b1 = create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=start
    )
    cancel_booking(b1)
    # Same slot is now bookable again (cancelled excluded from the constraint).
    b2 = create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=start
    )
    assert b2.status == BookingStatus.PENDING


@pytest.mark.django_db
def test_availability_excludes_booked_slot(customer, vendor, service):
    start = _future()
    create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=start
    )
    slots = available_slots(vendor=vendor, services=[service], date=start.date())
    assert start not in slots
    # A slot well after the 30-min booking should still be available.
    assert (start + timedelta(hours=2)) in slots


@pytest.mark.django_db
def test_state_machine_completion(customer, vendor, service):
    booking = create_booking(
        customer=customer, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=_future()
    )
    accept_booking(booking)
    assert booking.status == BookingStatus.CONFIRMED
    mark_completed(booking)
    assert booking.status == BookingStatus.COMPLETED
    # Cannot re-complete a completed booking.
    with pytest.raises(DomainError):
        mark_completed(booking)
