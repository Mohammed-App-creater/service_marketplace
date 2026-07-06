from django.db import transaction

from .models import SubscriptionChange, VendorSubscription


@transaction.atomic
def set_vendor_plan(vendor, plan):
    """Create or change a vendor's subscription plan (FR-202/203), logging the change."""
    sub = VendorSubscription.objects.select_for_update().filter(vendor=vendor).first()
    if sub is None:
        sub = VendorSubscription.objects.create(vendor=vendor, plan=plan)
        SubscriptionChange.objects.create(subscription=sub, from_plan=None, to_plan=plan)
        return sub
    if sub.plan_id != plan.id:
        SubscriptionChange.objects.create(subscription=sub, from_plan=sub.plan, to_plan=plan)
        sub.plan = plan
        sub.save(update_fields=["plan", "updated_at"])
    return sub
