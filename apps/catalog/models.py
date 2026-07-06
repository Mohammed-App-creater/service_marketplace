from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedUUIDModel


class Service(TimeStampedUUIDModel):
    """A bookable service offered by a vendor (FR-210)."""

    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text="Service duration in minutes."
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    # Discounts (mobile app: hasDiscount / discountPercent / discountDescription).
    has_discount = models.BooleanField(default=False)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    discount_description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["vendor", "is_active"])]

    def __str__(self):
        return f"{self.name} ({self.vendor_id})"

    @property
    def discounted_price(self):
        if not self.has_discount or not self.discount_percent:
            return self.price
        factor = (Decimal("100") - self.discount_percent) / Decimal("100")
        return (self.price * factor).quantize(Decimal("0.01"))

    @property
    def effective_price(self):
        """Price actually charged — discounted when a discount is active."""
        return self.discounted_price


class ServiceImage(TimeStampedUUIDModel):
    """Gallery image for a service (mobile app shows multiple per service)."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="services/")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]

    def __str__(self):
        return f"{self.service_id} image #{self.position}"
