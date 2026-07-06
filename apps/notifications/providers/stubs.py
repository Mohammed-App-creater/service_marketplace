"""Console/DB stub providers used for the MVP.

Each stub logs the outbound message and returns a successful ProviderResult.
The high-level notifications.services layer is responsible for writing the
NotificationLog row; these providers only simulate delivery.
"""

import logging

from .base import (
    EmailProvider,
    ProviderResult,
    PushProvider,
    RealtimeProvider,
    SMSProvider,
)

logger = logging.getLogger("apps.notifications")


class ConsoleSMSProvider(SMSProvider):
    def send(self, to, message, *, context=None):
        logger.info("[STUB SMS] to=%s message=%s", to, message)
        return ProviderResult(success=True, provider_ref="stub-sms", detail="logged")


class ConsoleEmailProvider(EmailProvider):
    def send(self, to, subject, message, *, context=None):
        logger.info("[STUB EMAIL] to=%s subject=%s message=%s", to, subject, message)
        return ProviderResult(success=True, provider_ref="stub-email", detail="logged")


class ConsolePushProvider(PushProvider):
    def send(self, tokens, title, body, *, data=None):
        logger.info("[STUB PUSH] tokens=%s title=%s body=%s data=%s", tokens, title, body, data)
        return ProviderResult(success=True, provider_ref="stub-push", detail="logged")


class ConsoleRealtimeProvider(RealtimeProvider):
    def publish(self, channel, event, payload):
        logger.info("[STUB REALTIME] channel=%s event=%s payload=%s", channel, event, payload)
        return ProviderResult(success=True, provider_ref="stub-realtime", detail="logged")
