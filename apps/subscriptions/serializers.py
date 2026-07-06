from rest_framework import serializers

from .models import SubscriptionPlan, VendorSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ["id", "name", "price", "billing_period", "features", "max_services", "is_active"]
        read_only_fields = ["id"]


class VendorSubscriptionSerializer(serializers.ModelSerializer):
    plan_detail = SubscriptionPlanSerializer(source="plan", read_only=True)

    class Meta:
        model = VendorSubscription
        fields = ["id", "plan", "plan_detail", "status", "started_at"]
        read_only_fields = ["id", "status", "started_at", "plan_detail"]
