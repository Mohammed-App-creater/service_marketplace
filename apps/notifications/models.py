from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedUUIDModel


class Channel(models.TextChoices):
    SMS = "sms", _("SMS")
    PUSH = "push", _("Push")
    REALTIME = "realtime", _("Realtime")
    EMAIL = "email", _("Email")


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", _("Queued")
    SENT = "sent", _("Sent")
    FAILED = "failed", _("Failed")


class NotificationLog(TimeStampedUUIDModel):
    """DB sink for every (stubbed or real) outbound notification."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    template_key = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.QUEUED,
    )
    provider_ref = models.CharField(max_length=128, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "channel"])]

    def __str__(self):
        return f"{self.channel}:{self.template_key} -> {self.recipient_id}"


class DevicePlatform(models.TextChoices):
    IOS = "ios", _("iOS")
    ANDROID = "android", _("Android")
    WEB = "web", _("Web")


class DeviceToken(TimeStampedUUIDModel):
    """FCM device token store — captured now, used when push goes live."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=16, choices=DevicePlatform.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id}:{self.platform}"
