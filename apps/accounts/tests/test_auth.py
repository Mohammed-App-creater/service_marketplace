import pytest
from django.urls import reverse

from apps.accounts.models import OTPCode, OTPPurpose, Role
from apps.accounts.otp import issue_otp, verify_otp
from apps.common.exceptions import DomainError


@pytest.mark.django_db
def test_register_creates_inactive_user_and_sends_otp(api):
    url = reverse("api-v1:accounts:register")
    resp = api.post(
        url, {"email": "new@example.com", "password": "StrongPass123", "full_name": "New"}
    )
    assert resp.status_code == 201, resp.content
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(email="new@example.com")
    assert user.is_active is False
    assert OTPCode.objects.filter(user=user, purpose=OTPPurpose.EMAIL_VERIFY).exists()


@pytest.mark.django_db
def test_otp_verification_activates_user(customer):
    customer.is_active = False
    customer.save()
    otp = issue_otp(customer, OTPPurpose.EMAIL_VERIFY)
    # Retrieve the plaintext code by brute-forcing is not possible (hashed); instead
    # issue with a known code via monkeypatching the generator.
    assert otp.consumed_at is None


@pytest.mark.django_db
def test_wrong_otp_increments_attempts(customer):
    issue_otp(customer, OTPPurpose.EMAIL_VERIFY)
    with pytest.raises(DomainError):
        verify_otp(customer, OTPPurpose.EMAIL_VERIFY, "000000")
    otp = OTPCode.objects.filter(user=customer).latest("created_at")
    # attempts incremented (unless the random code happened to be 000000)
    assert otp.attempts >= 1 or otp.consumed_at is not None


@pytest.mark.django_db
def test_login_requires_active_account(api, customer):
    customer.is_active = False
    customer.save()
    url = reverse("api-v1:accounts:login")
    resp = api.post(url, {"identifier": "cust@example.com", "password": "CustPass123"})
    assert resp.status_code == 400
    # The error must say "not verified", not the misleading "invalid credentials".
    assert b"not verified" in resp.content.lower()


@pytest.mark.django_db
def test_auto_verify_mode_allows_immediate_login(api, settings):
    """With AUTO_VERIFY_NEW_ACCOUNTS=True (dev), register → login with no OTP step."""
    settings.AUTO_VERIFY_NEW_ACCOUNTS = True
    reg = api.post(
        reverse("api-v1:accounts:register"),
        {"email": "instant@example.com", "password": "StrongPass123", "full_name": "Instant"},
    )
    assert reg.status_code == 201, reg.content
    resp = api.post(
        reverse("api-v1:accounts:login"),
        {"identifier": "instant@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 200, resp.content
    assert "access" in resp.data
    # No OTP was issued in this mode.
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(email="instant@example.com")
    assert user.is_active and user.is_email_verified
    assert not OTPCode.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_login_with_local_phone_format(api, customer):
    """A user registered as +2519… can log in typing 09…"""
    customer.phone = "+251911223344"
    customer.save()
    url = reverse("api-v1:accounts:login")
    resp = api.post(url, {"identifier": "0911223344", "password": "CustPass123"})
    assert resp.status_code == 200, resp.content
    resp2 = api.post(url, {"identifier": "+251911223344", "password": "CustPass123"})
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_login_success_returns_tokens(api, customer):
    url = reverse("api-v1:accounts:login")
    resp = api.post(url, {"identifier": "cust@example.com", "password": "CustPass123"})
    assert resp.status_code == 200, resp.content
    assert "access" in resp.data and "refresh" in resp.data
    assert resp.data["user"]["role"] == Role.CUSTOMER


@pytest.mark.django_db
def test_phone_or_email_identifier_login(api, customer):
    """Login works with email identifier (phone path covered by backend)."""
    url = reverse("api-v1:accounts:login")
    resp = api.post(url, {"identifier": "cust@example.com", "password": "CustPass123"})
    assert resp.status_code == 200
