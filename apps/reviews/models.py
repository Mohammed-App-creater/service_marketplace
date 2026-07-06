from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedUUIDModel


class Review(TimeStampedUUIDModel):
    """A customer's rating of a completed booking (FR-130/131/132).

    OneToOne on booking enforces "rate once per booking" at the DB level.
    """

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="review"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["vendor"])]
        constraints = [
            models.CheckConstraint(
                name="review_rating_range",
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
            ),
        ]

    def __str__(self):
        return f"{self.vendor_id} {self.rating}★ by {self.customer_id}"


class CustomerReview(TimeStampedUUIDModel):
    """A vendor's rating of a customer after a completed booking.

    Feeds the customer's reliability/profile score shown to vendors.
    OneToOne on booking enforces one rating per booking.
    """

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="customer_review"
    )
    vendor = models.ForeignKey(
        "vendors.Vendor", on_delete=models.CASCADE, related_name="given_customer_reviews"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["customer"])]
        constraints = [
            models.CheckConstraint(
                name="customer_review_rating_range",
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
            ),
        ]

    def __str__(self):
        return f"{self.customer_id} {self.rating}★ by vendor {self.vendor_id}"
