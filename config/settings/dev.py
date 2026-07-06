"""Development settings."""

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Permissive CORS for local frontend dev.
CORS_ALLOW_ALL_ORIGINS = True

INTERNAL_IPS = ["127.0.0.1"]

# django-debug-toolbar (optional; only if installed)
try:
    import debug_toolbar  # noqa: F401

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
except ImportError:
    pass
