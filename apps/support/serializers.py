from rest_framework import serializers

from .models import Complaint, ComplaintStatus


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            "id",
            "topic",
            "description",
            "target_vendor",
            "target_booking",
            "status",
            "resolution_note",
            "created_at",
        ]
        read_only_fields = ["id", "status", "resolution_note", "created_at"]


class ComplaintResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            (ComplaintStatus.IN_REVIEW, "In review"),
            (ComplaintStatus.RESOLVED, "Resolved"),
            (ComplaintStatus.DISMISSED, "Dismissed"),
        ]
    )
    resolution_note = serializers.CharField(required=False, allow_blank=True, default="")
