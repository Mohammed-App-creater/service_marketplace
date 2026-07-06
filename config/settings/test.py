"""Test settings — Postgres required (exclusion constraint can't run on SQLite)."""

from .base import *  # noqa: F401,F403

DEBUG = False

# Keep argon2 (security tests rely on it) but it is slow; that's acceptable for
# the small test suite. Switch to MD5 only if suite speed becomes a problem AND
# no test asserts on hashing.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ensure stubbed providers during tests.
SMS_PROVIDER = "apps.notifications.providers.stubs.ConsoleSMSProvider"
PUSH_PROVIDER = "apps.notifications.providers.stubs.ConsolePushProvider"
REALTIME_PROVIDER = "apps.notifications.providers.stubs.ConsoleRealtimeProvider"
EMAIL_PROVIDER = "apps.notifications.providers.stubs.ConsoleEmailProvider"
