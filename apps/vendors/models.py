from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedUUIDModel


class Category(TimeStampedUUIDModel):
    """Service category, e.g. Barber, Salon, Spa (FR-110).

    Two-level hierarchy: top-level "parent" pillars (e.g. Services,
    Reservations, Tickets) contain child categories vendors register under.
    """

    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    icon = models.CharField(max_length=64, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class VendorStatus(models.TextChoices):
    OPEN = "open", _("Open")
    CLOSED = "closed", _("Closed")


class VerificationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    VERIFIED = "verified", _("Verified")
    SUSPENDED = "suspended", _("Suspended")
    REJECTED = "rejected", _("Rejected")


class Vendor(TimeStampedUUIDModel):
    """Vendor business profile (FR-201)."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor"
    )
    business_name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="vendors")
    description = models.TextField(blank=True)
    address = models.TextField(blank=True)
    location_lat = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, db_index=True
    )
    location_lng = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, db_index=True
    )
    contact_phone = models.CharField(max_length=32, blank=True)
    cover_photo = models.ImageField(upload_to="vendors/", null=True, blank=True)

    status = models.CharField(
        max_length=8, choices=VendorStatus.choices, default=VendorStatus.CLOSED
    )
    verification_status = models.CharField(
        max_length=16,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )

    # Denormalized rating aggregate (updated by reviews signal) — FR-131.
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    rating_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["business_name"]
        indexes = [
            models.Index(fields=["category", "verification_status"]),
            models.Index(fields=["location_lat", "location_lng"]),
        ]

    def __str__(self):
        return self.business_name

    @property
    def is_verified(self):
        return self.verification_status == VerificationStatus.VERIFIED

    @property
    def is_live(self):
        return self.is_verified and self.owner.is_active

    @property
    def is_open(self):
        return self.status == VendorStatus.OPEN


class WorkingHours(TimeStampedUUIDModel):
    """Per-day availability window (FR-211)."""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="working_hours")
    day_of_week = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="0=Monday ... 6=Sunday",
    )
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day_of_week"]
        constraints = [
            models.UniqueConstraint(fields=["vendor", "day_of_week"], name="unique_vendor_day"),
        ]

    def __str__(self):
        return f"{self.vendor_id} day={self.day_of_week}"


class ScheduleBlock(TimeStampedUUIDModel):
    """Blocked date/time range, e.g. holiday (FR-213)."""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="schedule_blocks")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=140, blank=True)

    class Meta:
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                name="scheduleblock_end_after_start",
                condition=models.Q(end_datetime__gt=models.F("start_datetime")),
            ),
        ]

    def __str__(self):
        return f"{self.vendor_id} block {self.start_datetime:%Y-%m-%d %H:%M}"


class Favorite(TimeStampedUUIDModel):
    """A customer's saved vendor (server-synced favorites)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "vendor"], name="unique_user_vendor_favorite"),
        ]

    def __str__(self):
        return f"{self.user_id} ♥ {self.vendor_id}"
