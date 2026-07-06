from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.bookings.models import BookingStatus

from .models import CustomerReview, Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "booking",
            "vendor",
            "customer",
            "customer_name",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "vendor", "customer", "customer_name", "created_at"]

    def validate_booking(self, booking):
        request = self.context["request"]
        if booking.customer_id != request.user.id:
            raise serializers.ValidationError(_("You can only review your own bookings."))
        if booking.status != BookingStatus.COMPLETED:
            raise serializers.ValidationError(_("You can only review completed appointments."))
        if Review.objects.filter(booking=booking).exists():
            raise serializers.ValidationError(_("This booking has already been reviewed."))
        return booking

    def create(self, validated_data):
        booking = validated_data["booking"]
        validated_data["customer"] = booking.customer
        validated_data["vendor"] = booking.vendor
        return super().create(validated_data)


class CustomerReviewSerializer(serializers.ModelSerializer):
    """Vendor rates the customer after a completed booking."""

    vendor_name = serializers.CharField(source="vendor.business_name", read_only=True)

    class Meta:
        model = CustomerReview
        fields = [
            "id",
            "booking",
            "vendor",
            "vendor_name",
            "customer",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "vendor", "vendor_name", "customer", "created_at"]

    def validate_booking(self, booking):
        request = self.context["request"]
        vendor = getattr(request.user, "vendor", None)
        if vendor is None or booking.vendor_id != vendor.id:
            raise serializers.ValidationError(
                _("You can only rate customers of your own bookings.")
            )
        if booking.status != BookingStatus.COMPLETED:
            raise serializers.ValidationError(_("You can only rate completed appointments."))
        if CustomerReview.objects.filter(booking=booking).exists():
            raise serializers.ValidationError(
                _("This customer has already been rated for this booking.")
            )
        return booking

    def create(self, validated_data):
        booking = validated_data["booking"]
        validated_data["vendor"] = booking.vendor
        validated_data["customer"] = booking.customer
        return super().create(validated_data)
