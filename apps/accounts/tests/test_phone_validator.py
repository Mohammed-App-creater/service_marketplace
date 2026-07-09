"""Ethiopian mobile number validation on registration."""

import pytest
from django.urls import reverse


def _register(api, phone):
    url = reverse("api-v1:accounts:register")
    return api.post(
        url, {"phone": phone, "password": "StrongPass123", "full_name": "Phone Tester"}
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "phone",
    [
        "+251911223344",  # Ethio Telecom, E.164
        "+251712345678",  # Safaricom ET, E.164
        "0911223344",     # local 09… form
        "0712345678",     # local 07… form
    ],
)
def test_valid_ethiopian_numbers_accepted(api, phone):
    resp = _register(api, phone)
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "phone",
    [
        "+251811223344",   # 8 — not a mobile prefix
        "+25191122334",    # too short
        "+2519112233445",  # too long
        "+15551234567",    # wrong country
        "091122334",       # local, too short
    ],
)
def test_invalid_numbers_rejected(api, phone):
    resp = _register(api, phone)
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_duplicate_phone_returns_400_not_500(api):
    first = _register(api, "0911223344")
    assert first.status_code == 201, first.content
    # Same number in a different format — still the same account.
    dup = _register(api, "+251911223344")
    assert dup.status_code == 400, dup.content
    assert b"already exists" in dup.content


@pytest.mark.django_db
def test_duplicate_email_returns_400_not_500(api):
    url = reverse("api-v1:accounts:register")
    body = {"email": "dup@example.com", "password": "StrongPass123", "full_name": "Dup"}
    assert api.post(url, body).status_code == 201
    dup = api.post(url, body)
    assert dup.status_code == 400, dup.content
    assert b"already exists" in dup.content
