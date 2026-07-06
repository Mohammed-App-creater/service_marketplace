from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DeviceToken, NotificationLog
from .serializers import DeviceTokenSerializer, NotificationLogSerializer


class DeviceTokenViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Register/list/remove FCM device tokens for the current user."""

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Upsert on token to avoid unique-constraint errors on re-register.
        token = serializer.validated_data["token"]
        DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": self.request.user,
                "platform": serializer.validated_data["platform"],
                "is_active": True,
            },
        )


class NotificationLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Feed of the current user's notifications, with read tracking.

    Filter with ?is_read=true|false.
    """

    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_read", "channel"]

    def get_queryset(self):
        return NotificationLog.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        updated = (
            self.get_queryset()
            .filter(pk=pk, is_read=False)
            .update(is_read=True, read_at=timezone.now())
        )
        if not updated and not self.get_queryset().filter(pk=pk).exists():
            return Response(status=404)
        return Response({"detail": "marked read"})

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        count = (
            self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        )
        return Response({"marked": count})
