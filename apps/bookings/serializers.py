from rest_framework import serializers

from .models import Booking, BookingItem


class BookingCreateSerializer(serializers.Serializer):
    """FR-120 — select vendor, one or more services, and a start time."""

    vendor = serializers.UUIDField()
    services = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=20)
    scheduled_start = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BookingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingItem
        fields = ["id", "service", "service_name", "price", "duration_minutes"]
        read_only_fields = fields


class BookingSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    items = BookingItemSerializer(many=True, read_only=True)
    service_names = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "customer",
            "customer_name",
            "vendor",
            "vendor_name",
            "items",
            "service_names",
            "scheduled_start",
            "scheduled_end",
            "status",
            "notes",
            "subtotal",
            "service_fee",
            "total",
            "cancelled_by",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_service_names(self, obj):
        return [item.service_name for item in obj.items.all()]


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingDeclineSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
