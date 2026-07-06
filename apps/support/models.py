from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedUUIDModel


class ComplaintStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_REVIEW = "in_review", _("In review")
    RESOLVED = "resolved", _("Resolved")
    DISMISSED = "dismissed", _("Dismissed")


class Complaint(TimeStampedUUIDModel):
    """A complaint filed by a customer or vendor (topic lists live in the app)."""

    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints"
    )
    topic = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    target_vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_against",
    )
    target_booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    status = models.CharField(
        max_length=16, choices=ComplaintStatus.choices, default=ComplaintStatus.OPEN, db_index=True
    )
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic} ({self.status}) by {self.complainant_id}"
