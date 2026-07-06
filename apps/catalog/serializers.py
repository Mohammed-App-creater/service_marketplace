from rest_framework import serializers

from .models import Service, ServiceImage


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = ["id", "image", "position", "created_at"]
        read_only_fields = ["id", "created_at"]


class ServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "vendor",
            "name",
            "description",
            "duration_minutes",
            "price",
            "is_active",
            "has_discount",
            "discount_percent",
            "discount_description",
            "discounted_price",
            "images",
            "created_at",
        ]
        read_only_fields = ["id", "vendor", "discounted_price", "images", "created_at"]


class PublicServiceSerializer(serializers.ModelSerializer):
    images = ServiceImageSerializer(many=True, read_only=True)
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "duration_minutes",
            "price",
            "has_discount",
            "discount_percent",
            "discount_description",
            "discounted_price",
            "images",
        ]
        read_only_fields = fields
