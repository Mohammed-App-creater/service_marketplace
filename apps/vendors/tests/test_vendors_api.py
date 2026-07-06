import pytest
from django.urls import reverse

from apps.vendors.models import VerificationStatus


@pytest.mark.django_db
def test_search_returns_verified_vendor_with_distance(api, vendor, service):
    url = reverse("api-v1:vendors:vendor-list")
    resp = api.get(url, {"lat": "9.02", "lng": "38.77", "order_by": "distance"})
    assert resp.status_code == 200
    results = resp.data["results"]
    assert len(results) == 1
    assert results[0]["distance_km"] is not None


@pytest.mark.django_db
def test_search_excludes_unverified_vendor(api, vendor):
    vendor.verification_status = VerificationStatus.PENDING
    vendor.save()
    url = reverse("api-v1:vendors:vendor-list")
    resp = api.get(url)
    assert resp.data["count"] == 0


@pytest.mark.django_db
def test_navigate_returns_deeplinks(api, vendor):
    url = reverse("api-v1:vendors:vendor-navigate", args=[vendor.id])
    resp = api.get(url)
    assert resp.status_code == 200
    assert "google_maps_url" in resp.data
    assert "waze_url" in resp.data


@pytest.mark.django_db
def test_customer_cannot_create_service(auth_customer, vendor, service):
    url = reverse("api-v1:catalog:me-service-list")
    resp = auth_customer.post(url, {"name": "X", "duration_minutes": 30, "price": "100"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unverified_vendor_cannot_manage_services(api, vendor_user, vendor):
    vendor.verification_status = VerificationStatus.PENDING
    vendor.save()
    api.force_authenticate(user=vendor_user)
    url = reverse("api-v1:catalog:me-service-list")
    resp = api.post(url, {"name": "X", "duration_minutes": 30, "price": "100"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_vendor_status_toggle(auth_vendor, vendor):
    url = reverse("api-v1:vendors:vendor-me-status")
    resp = auth_vendor.patch(url, {"status": "closed"})
    assert resp.status_code == 200
    vendor.refresh_from_db()
    assert vendor.status == "closed"
