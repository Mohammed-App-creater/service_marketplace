"""Resolve concrete provider instances from settings class paths.

Change SMS_PROVIDER / PUSH_PROVIDER / REALTIME_PROVIDER / EMAIL_PROVIDER in
settings (via env) to swap stubs for real providers — no caller changes.
"""

from functools import cache

from django.conf import settings
from django.utils.module_loading import import_string

from .base import EmailProvider, PushProvider, RealtimeProvider, SMSProvider


@cache
def get_sms_provider() -> SMSProvider:
    return import_string(settings.SMS_PROVIDER)()


@cache
def get_email_provider() -> EmailProvider:
    return import_string(settings.EMAIL_PROVIDER)()


@cache
def get_push_provider() -> PushProvider:
    return import_string(settings.PUSH_PROVIDER)()


@cache
def get_realtime_provider() -> RealtimeProvider:
    return import_string(settings.REALTIME_PROVIDER)()


def reset_provider_cache() -> None:
    """Clear cached providers — used by tests that override provider settings."""
    get_sms_provider.cache_clear()
    get_email_provider.cache_clear()
    get_push_provider.cache_clear()
    get_realtime_provider.cache_clear()
