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

# No rate limiting in tests — the suite makes many auth calls in one minute,
# and hitting the throttle turns expected 400s into flaky 429s.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": ()}  # noqa: F405

# Tests assert the strict FR-102 flow (inactive until OTP), regardless of the
# dev convenience flag in .env.
AUTO_VERIFY_NEW_ACCOUNTS = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Ensure stubbed providers during tests.
SMS_PROVIDER = "apps.notifications.providers.stubs.ConsoleSMSProvider"
PUSH_PROVIDER = "apps.notifications.providers.stubs.ConsolePushProvider"
REALTIME_PROVIDER = "apps.notifications.providers.stubs.ConsoleRealtimeProvider"
EMAIL_PROVIDER = "apps.notifications.providers.stubs.ConsoleEmailProvider"
