"""Vendor-rates-customer reviews and the customer profile endpoint."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from psycopg.types.range import Range

from apps.bookings.models import Booking, BookingItem, BookingStatus


def _completed_booking(customer, vendor, service):
    start = timezone.now() + timedelta(days=1)
    end = start + timedelta(minutes=service.duration_minutes)
    booking = Booking.objects.create(
        customer=customer,
        vendor=vendor,
        scheduled_start=start,
        scheduled_end=end,
        slot=Range(start, end, bounds="[)"),
        status=BookingStatus.COMPLETED,
    )
    BookingItem.objects.create(
        booking=booking,
        service=service,
        service_name=service.name,
        price=service.price,
        duration_minutes=service.duration_minutes,
    )
    return booking


@pytest.mark.django_db
def test_vendor_rates_customer(auth_vendor, customer, vendor, service):
    booking = _completed_booking(customer, vendor, service)
    url = reverse("api-v1:reviews:customer-review-list")
    resp = auth_vendor.post(url, {"booking": str(booking.id), "rating": 4, "comment": "Punctual"})
    assert resp.status_code == 201, resp.content

    # Rating twice for the same booking is rejected.
    again = auth_vendor.post(url, {"booking": str(booking.id), "rating": 1})
    assert again.status_code == 400


@pytest.mark.django_db
def test_customer_cannot_rate_customers(auth_customer, customer, vendor, service):
    booking = _completed_booking(customer, vendor, service)
    url = reverse("api-v1:reviews:customer-review-list")
    resp = auth_customer.post(url, {"booking": str(booking.id), "rating": 5})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_customer_profile_view_for_vendor(auth_vendor, customer, vendor, service):
    booking = _completed_booking(customer, vendor, service)
    url = reverse("api-v1:reviews:customer-review-list")
    auth_vendor.post(url, {"booking": str(booking.id), "rating": 5, "comment": "Great"})

    profile_url = reverse("api-v1:reviews:customer-profile", args=[customer.id])
    resp = auth_vendor.get(profile_url)
    assert resp.status_code == 200, resp.content
    assert resp.data["rating_avg"] == 5.0
    assert resp.data["rating_count"] == 1
    assert "Haircut" in resp.data["previous_services"]
