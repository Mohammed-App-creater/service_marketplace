"""FR-122 — the critical no-double-booking guarantee under concurrency.

Runs against real Postgres (the exclusion constraint cannot exist on SQLite).
"""

import threading
from datetime import timedelta

import pytest
from django.db import connection

from apps.bookings.models import ACTIVE_STATUSES, Booking
from apps.bookings.services import create_booking
from apps.common.exceptions import ConflictError


@pytest.mark.django_db(transaction=True)
def test_no_double_booking_under_concurrency(customer, vendor, service, django_db_blocker):
    # Two customers, same vendor, exact same overlapping slot.
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role

    User = get_user_model()
    other = User.objects.create_user(
        email="cust2@example.com", password="Pass12345", role=Role.CUSTOMER, is_active=True
    )

    start = _aligned_future_start()
    results = []
    barrier = threading.Barrier(2)

    def attempt(user):
        barrier.wait()  # release both threads simultaneously
        try:
            booking = create_booking(
                customer=user, vendor_id=vendor.id, service_ids=[service.id], scheduled_start=start
            )
            results.append(("ok", booking.id))
        except ConflictError:
            results.append(("conflict", None))
        finally:
            connection.close()

    t1 = threading.Thread(target=attempt, args=(customer,))
    t2 = threading.Thread(target=attempt, args=(other,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    outcomes = sorted(r[0] for r in results)
    assert outcomes == ["conflict", "ok"], outcomes
    assert Booking.objects.filter(vendor=vendor, status__in=ACTIVE_STATUSES).count() == 1


@pytest.mark.django_db
def test_exclusion_constraint_blocks_overlap_directly(customer, vendor, service):
    """Defense-in-depth: the DB constraint itself rejects an overlap even if the
    app-level checks were bypassed."""
    from django.contrib.auth import get_user_model
    from django.db import IntegrityError
    from psycopg.types.range import Range

    from apps.accounts.models import Role

    start = _aligned_future_start()
    end = start + timedelta(minutes=service.duration_minutes)
    Booking.objects.create(
        customer=customer,
        vendor=vendor,
        scheduled_start=start,
        scheduled_end=end,
        slot=Range(start, end, bounds="[)"),
    )

    User = get_user_model()
    other = User.objects.create_user(
        email="c3@example.com", password="Pass12345", role=Role.CUSTOMER, is_active=True
    )
    # Overlapping (starts 15 min into the first booking).
    o_start = start + timedelta(minutes=15)
    o_end = o_start + timedelta(minutes=service.duration_minutes)
    with pytest.raises(IntegrityError):
        Booking.objects.create(
            customer=other,
            vendor=vendor,
            scheduled_start=o_start,
            scheduled_end=o_end,
            slot=Range(o_start, o_end, bounds="[)"),
        )


def _aligned_future_start():
    from django.utils import timezone

    base = timezone.now() + timedelta(days=1)
    return base.replace(hour=10, minute=0, second=0, microsecond=0)
