"""Keep Vendor.rating_avg / rating_count in sync with reviews (FR-131)."""

from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.vendors.models import Vendor

from .models import Review


def _recompute(vendor_id):
    agg = Review.objects.filter(vendor_id=vendor_id).aggregate(avg=Avg("rating"), count=Count("id"))
    Vendor.objects.filter(id=vendor_id).update(
        rating_avg=round(agg["avg"] or 0, 2),
        rating_count=agg["count"] or 0,
    )


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    _recompute(instance.vendor_id)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    _recompute(instance.vendor_id)
