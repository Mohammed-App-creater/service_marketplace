import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from .managers import UserManager
from .validators import validate_ethiopian_phone


class Role(models.TextChoices):
    CUSTOMER = "customer", _("Customer")
    VENDOR = "vendor", _("Vendor")
    ADMIN = "admin", _("Admin")


class Language(models.TextChoices):
    EN = "en", _("English")
    AM = "am", _("Amharic")


class User(AbstractBaseUser, PermissionsMixin):
    """Single custom user for all roles (customer/vendor/admin).

    Login via phone OR email (see accounts.backends.PhoneOrEmailBackend).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, null=True, blank=True)
    phone = PhoneNumberField(
        _("phone number"),
        unique=True,
        null=True,
        blank=True,
        validators=[validate_ethiopian_phone],
    )
    full_name = models.CharField(_("full name"), max_length=150, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CUSTOMER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    profile_photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    preferred_language = models.CharField(
        max_length=8, choices=Language.choices, default=Language.EN
    )
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    # No username; either identifier works. USERNAME_FIELD points at a stable
    # unique column for Django internals; auth is handled by the custom backend.
    USERNAME_FIELD = "id"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="user_email_or_phone_required",
                condition=Q(email__isnull=False) | Q(phone__isnull=False),
            ),
        ]

    def __str__(self):
        return self.email or str(self.phone) or str(self.id)

    @property
    def is_customer(self):
        return self.role == Role.CUSTOMER

    @property
    def is_vendor(self):
        return self.role == Role.VENDOR

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN


class OTPPurpose(models.TextChoices):
    PHONE_VERIFY = "phone_verify", _("Phone verification")
    EMAIL_VERIFY = "email_verify", _("Email verification")
    PASSWORD_RESET = "password_reset", _("Password reset")


class OTPChannel(models.TextChoices):
    SMS = "sms", _("SMS")
    EMAIL = "email", _("Email")


class OTPCode(models.Model):
    """One-time codes for verification and password reset.

    The code itself is stored HASHED (never plaintext).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=OTPPurpose.choices)
    channel = models.CharField(max_length=8, choices=OTPChannel.choices)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "purpose", "consumed_at"])]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None
