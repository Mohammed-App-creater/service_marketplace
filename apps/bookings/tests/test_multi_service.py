"""Multi-service bookings: combined duration, totals, and the 5% service fee."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.services import available_slots, create_booking
from apps.catalog.models import Service


def _future(hour=10):
    return (timezone.now() + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


@pytest.fixture
def second_service(vendor):
    return Service.objects.create(
        vendor=vendor, name="Beard Trim", duration_minutes=15, price=Decimal("100")
    )


@pytest.mark.django_db
def test_multi_service_booking_spans_combined_duration(customer, vendor, service, second_service):
    start = _future()
    booking = create_booking(
        customer=customer,
        vendor_id=vendor.id,
        service_ids=[service.id, second_service.id],
        scheduled_start=start,
        notes="Please be quick",
    )
    # 30 + 15 minutes
    assert booking.scheduled_end == start + timedelta(minutes=45)
    assert booking.items.count() == 2
    assert booking.notes == "Please be quick"
    # 200 + 100 subtotal, 5% fee
    assert booking.subtotal == Decimal("300.00")
    assert booking.service_fee == Decimal("15.00")
    assert booking.total == Decimal("315.00")


@pytest.mark.django_db
def test_discounted_price_used_in_totals(customer, vendor, service):
    service.has_discount = True
    service.discount_percent = Decimal("50")
    service.save()
    booking = create_booking(
        customer=customer,
        vendor_id=vendor.id,
        service_ids=[service.id],
        scheduled_start=_future(),
    )
    assert booking.subtotal == Decimal("100.00")  # 200 * 50%
    assert booking.total == Decimal("105.00")


@pytest.mark.django_db
def test_availability_uses_combined_duration(vendor, service, second_service):
    date = (_future()).date()
    combined = available_slots(vendor=vendor, services=[service, second_service], date=date)
    single = available_slots(vendor=vendor, services=[service], date=date)
    # Longer combined duration → fewer or equal possible start slots.
    assert len(combined) <= len(single)


@pytest.mark.django_db
def test_api_create_multi_service_booking(auth_customer, vendor, service, second_service):
    url = reverse("api-v1:bookings:booking-list")
    resp = auth_customer.post(
        url,
        {
            "vendor": str(vendor.id),
            "services": [str(service.id), str(second_service.id)],
            "scheduled_start": _future().isoformat(),
            "notes": "hello",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert len(resp.data["items"]) == 2
    assert sorted(resp.data["service_names"]) == ["Beard Trim", "Haircut"]
    assert Decimal(resp.data["total"]) == Decimal("315.00")
