"""High-level, provider-agnostic notification API.

The rest of the codebase calls ONLY these functions — never a provider directly.
Every send writes a NotificationLog row and dispatches through the configured
provider (stub in MVP).
"""

import logging

from django.utils import timezone

from .models import Channel, DeviceToken, NotificationLog, NotificationStatus
from .providers.factory import (
    get_email_provider,
    get_push_provider,
    get_realtime_provider,
    get_sms_provider,
)

logger = logging.getLogger("apps.notifications")


def _log(recipient, channel, template_key, payload, result):
    return NotificationLog.objects.create(
        recipient=recipient,
        channel=channel,
        template_key=template_key,
        payload=payload or {},
        status=NotificationStatus.SENT if result.success else NotificationStatus.FAILED,
        provider_ref=result.provider_ref,
        sent_at=timezone.now() if result.success else None,
    )


def send_sms(*, recipient=None, to, template_key, message, payload=None):
    result = get_sms_provider().send(to, message, context=payload)
    return _log(
        recipient, Channel.SMS, template_key, payload or {"to": to, "message": message}, result
    )


def send_email(*, recipient=None, to, template_key, subject, message, payload=None):
    result = get_email_provider().send(to, subject, message, context=payload)
    return _log(
        recipient, Channel.EMAIL, template_key, payload or {"to": to, "subject": subject}, result
    )


def send_push(*, recipient, title, body, template_key, data=None):
    tokens = list(
        DeviceToken.objects.filter(user=recipient, is_active=True).values_list("token", flat=True)
    )
    if not tokens:
        logger.info(
            "No active device tokens for user=%s; skipping push", getattr(recipient, "id", None)
        )
        result = get_push_provider().send([], title, body, data=data)
    else:
        result = get_push_provider().send(tokens, title, body, data=data)
    return _log(
        recipient, Channel.PUSH, template_key, data or {"title": title, "body": body}, result
    )


def publish_realtime(*, recipient=None, channel_name, event, payload):
    result = get_realtime_provider().publish(channel_name, event, payload)
    return _log(recipient, Channel.REALTIME, event, {"channel": channel_name, **payload}, result)
