from rest_framework import serializers

from .models import DeviceToken, NotificationLog


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "token", "platform", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "channel",
            "template_key",
            "payload",
            "status",
            "is_read",
            "read_at",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
