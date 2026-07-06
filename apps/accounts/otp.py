"""OTP generation, delivery, and verification."""

import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.exceptions import DomainError
from apps.notifications import services as notify

from .models import OTPChannel, OTPCode, OTPPurpose

CODE_LENGTH = 6


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))


def issue_otp(user, purpose: str) -> OTPCode:
    """Create + deliver an OTP for the given purpose.

    Returns the OTPCode row. The plaintext code is only ever sent via the
    provider; it is never persisted.
    """
    channel = (
        OTPChannel.EMAIL
        if (purpose == OTPPurpose.EMAIL_VERIFY or not user.phone)
        else OTPChannel.SMS
    )
    if purpose == OTPPurpose.PHONE_VERIFY and not user.phone:
        raise DomainError(_("No phone number on file to verify."))
    if channel == OTPChannel.EMAIL and not user.email:
        raise DomainError(_("No email address on file to verify."))

    code = _generate_code()
    otp = OTPCode.objects.create(
        user=user,
        code_hash=make_password(code),
        purpose=purpose,
        channel=channel,
        expires_at=timezone.now() + timezone.timedelta(seconds=settings.OTP_TTL_SECONDS),
    )

    message = _("Your verification code is %(code)s. It expires in %(mins)s minutes.") % {
        "code": code,
        "mins": settings.OTP_TTL_SECONDS // 60,
    }
    if channel == OTPChannel.SMS:
        notify.send_sms(
            recipient=user,
            to=str(user.phone),
            template_key=f"otp.{purpose}",
            message=str(message),
        )
    else:
        notify.send_email(
            recipient=user,
            to=user.email,
            template_key=f"otp.{purpose}",
            subject=str(_("Your verification code")),
            message=str(message),
        )
    return otp


def verify_otp(user, purpose: str, code: str) -> bool:
    """Validate a submitted code; consume it on success. Raises DomainError otherwise."""
    otp = (
        OTPCode.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise DomainError(_("No active code. Please request a new one."))
    if otp.is_expired:
        raise DomainError(_("This code has expired. Please request a new one."))
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise DomainError(_("Too many attempts. Please request a new code."))

    if not check_password(code, otp.code_hash):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise DomainError(_("Incorrect code."))

    otp.consumed_at = timezone.now()
    otp.save(update_fields=["consumed_at"])

    # Apply the side effect of a successful verification.
    if purpose == OTPPurpose.PHONE_VERIFY:
        user.is_phone_verified = True
        user.is_active = True
        user.save(update_fields=["is_phone_verified", "is_active"])
    elif purpose == OTPPurpose.EMAIL_VERIFY:
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])
    return True
