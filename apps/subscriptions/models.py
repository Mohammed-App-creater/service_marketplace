from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedUUIDModel


class PlanTier(models.TextChoices):
    BASIC = "basic", _("Basic")
    STANDARD = "standard", _("Standard")
    PREMIUM = "premium", _("Premium")


class BillingPeriod(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")


class SubscriptionPlan(TimeStampedUUIDModel):
    """Admin-managed plan (FR-202/303)."""

    name = models.CharField(max_length=32, choices=PlanTier.choices, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(
        max_length=16, choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY
    )
    features = models.JSONField(default=dict, blank=True)
    max_services = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return self.get_name_display()


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    CANCELLED = "cancelled", _("Cancelled")


class VendorSubscription(TimeStampedUUIDModel):
    """A vendor's current plan (FR-202/203)."""

    vendor = models.OneToOneField(
        "vendors.Vendor", on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField(
        max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE
    )
    started_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vendor_id} -> {self.plan}"


class SubscriptionChange(TimeStampedUUIDModel):
    """Audit log of plan changes (upgrade/downgrade history)."""

    subscription = models.ForeignKey(
        VendorSubscription, on_delete=models.CASCADE, related_name="changes"
    )
    from_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    to_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-created_at"]
