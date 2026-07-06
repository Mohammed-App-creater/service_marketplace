"""Category hierarchy, favorites, complaints, notifications read-tracking."""

import pytest
from django.urls import reverse

from apps.notifications.models import Channel, NotificationLog
from apps.vendors.models import Category, Favorite


@pytest.mark.django_db
def test_category_hierarchy(api, category):
    parent = Category.objects.create(name="Services", slug="services")
    category.parent = parent
    category.save()

    url = reverse("api-v1:vendors:category-list")
    top = api.get(url, {"top": "true"})
    assert top.status_code == 200
    names = [c["name"] for c in top.data]
    assert "Services" in names and "Barber" not in names
    services = next(c for c in top.data if c["name"] == "Services")
    assert [c["name"] for c in services["children"]] == ["Barber"]

    children = api.get(url, {"parent": "services"})
    assert [c["name"] for c in children.data] == ["Barber"]


@pytest.mark.django_db
def test_favorites_roundtrip(auth_customer, customer, vendor):
    url = reverse("api-v1:vendors:favorite-list")
    resp = auth_customer.post(url, {"vendor": str(vendor.id)})
    assert resp.status_code == 201, resp.content
    # Idempotent re-add
    auth_customer.post(url, {"vendor": str(vendor.id)})
    assert Favorite.objects.filter(user=customer).count() == 1

    listing = auth_customer.get(url)
    assert listing.data["count"] == 1
    assert listing.data["results"][0]["vendor_detail"]["business_name"] == "Sharp Cuts"

    # Delete by vendor id
    detail = reverse("api-v1:vendors:favorite-detail", args=[vendor.id])
    resp = auth_customer.delete(detail)
    assert resp.status_code == 204
    assert Favorite.objects.filter(user=customer).count() == 0


@pytest.mark.django_db
def test_complaint_flow(auth_customer, customer, vendor):
    url = reverse("api-v1:support:complaint-list")
    resp = auth_customer.post(
        url,
        {
            "topic": "Vendor was late",
            "description": "Waited 40 minutes",
            "target_vendor": str(vendor.id),
        },
    )
    assert resp.status_code == 201, resp.content
    assert resp.data["status"] == "open"

    listing = auth_customer.get(url)
    assert listing.data["count"] == 1


@pytest.mark.django_db
def test_notification_mark_read(auth_customer, customer):
    log = NotificationLog.objects.create(
        recipient=customer, channel=Channel.PUSH, template_key="test", payload={}
    )
    url = reverse("api-v1:notifications:notification-mark-read", args=[log.id])
    resp = auth_customer.patch(url)
    assert resp.status_code == 200
    log.refresh_from_db()
    assert log.is_read is True and log.read_at is not None

    # read-all
    NotificationLog.objects.create(
        recipient=customer, channel=Channel.PUSH, template_key="t2", payload={}
    )
    all_url = reverse("api-v1:notifications:notification-mark-all-read")
    resp = auth_customer.post(all_url)
    assert resp.status_code == 200
    assert NotificationLog.objects.filter(recipient=customer, is_read=False).count() == 0
