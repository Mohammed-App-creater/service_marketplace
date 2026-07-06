from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
from apps.reviews.models import Review


def _completed_booking(customer, vendor, service):
    start = timezone.now() + timedelta(days=1)
    end = start + timedelta(minutes=service.duration_minutes)
    from psycopg.types.range import Range

    return Booking.objects.create(
        customer=customer,
        vendor=vendor,
        scheduled_start=start,
        scheduled_end=end,
        slot=Range(start, end, bounds="[)"),
        status=BookingStatus.COMPLETED,
    )


@pytest.mark.django_db
def test_review_completed_booking_updates_aggregate(auth_customer, customer, vendor, service):
    booking = _completed_booking(customer, vendor, service)
    url = reverse("api-v1:reviews:review-list")
    resp = auth_customer.post(url, {"booking": str(booking.id), "rating": 5, "comment": "Great"})
    assert resp.status_code == 201, resp.content
    vendor.refresh_from_db()
    assert vendor.rating_count == 1
    assert float(vendor.rating_avg) == 5.0


@pytest.mark.django_db
def test_cannot_review_twice(auth_customer, customer, vendor, service):
    booking = _completed_booking(customer, vendor, service)
    url = reverse("api-v1:reviews:review-list")
    first = auth_customer.post(url, {"booking": str(booking.id), "rating": 4})
    assert first.status_code == 201
    second = auth_customer.post(url, {"booking": str(booking.id), "rating": 2})
    assert second.status_code == 400
    assert Review.objects.filter(booking=booking).count() == 1


@pytest.mark.django_db
def test_cannot_review_incomplete_booking(auth_customer, customer, vendor, service):
    from psycopg.types.range import Range

    start = timezone.now() + timedelta(days=1)
    end = start + timedelta(minutes=30)
    booking = Booking.objects.create(
        customer=customer,
        vendor=vendor,
        scheduled_start=start,
        scheduled_end=end,
        slot=Range(start, end, bounds="[)"),
        status=BookingStatus.CONFIRMED,
    )
    url = reverse("api-v1:reviews:review-list")
    resp = auth_customer.post(url, {"booking": str(booking.id), "rating": 5})
    assert resp.status_code == 400
