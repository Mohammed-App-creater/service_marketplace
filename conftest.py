from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.catalog.models import Service
from apps.vendors.models import (
    Category,
    Vendor,
    VendorStatus,
    VerificationStatus,
    WorkingHours,
)

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def customer(db):
    user = User.objects.create_user(
        email="cust@example.com", password="CustPass123", role=Role.CUSTOMER, is_active=True
    )
    return user


@pytest.fixture
def vendor_user(db):
    return User.objects.create_user(
        email="vend@example.com", password="VendPass123", role=Role.VENDOR, is_active=True
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Barber", slug="barber")


@pytest.fixture
def vendor(db, vendor_user, category):
    v = Vendor.objects.create(
        owner=vendor_user,
        business_name="Sharp Cuts",
        category=category,
        location_lat=Decimal("9.010000"),
        location_lng=Decimal("38.760000"),
        status=VendorStatus.OPEN,
        verification_status=VerificationStatus.VERIFIED,
    )
    # Open every day 00:00–23:59 to simplify slot math in tests.
    for day in range(7):
        WorkingHours.objects.create(
            vendor=v, day_of_week=day, open_time="00:00", close_time="23:59", is_closed=False
        )
    return v


@pytest.fixture
def service(db, vendor):
    return Service.objects.create(
        vendor=vendor, name="Haircut", duration_minutes=30, price=Decimal("200")
    )


@pytest.fixture
def future_start():
    """A start time comfortably in the future, aligned to avoid lead-time issues."""
    return timezone.now() + timedelta(days=1)


@pytest.fixture
def auth_customer(api, customer):
    api.force_authenticate(user=customer)
    return api


@pytest.fixture
def auth_vendor(api, vendor_user):
    api.force_authenticate(user=vendor_user)
    return api
