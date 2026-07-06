"""Base settings shared across all environments."""

from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths & environment
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    JWT_ACCESS_LIFETIME_MIN=(int, 60),
    JWT_REFRESH_LIFETIME_DAYS=(int, 7),
    OTP_TTL_SECONDS=(int, 300),
    OTP_MAX_ATTEMPTS=(int, 5),
    DEFAULT_LANGUAGE=(str, "en"),
    CELERY_TASK_ALWAYS_EAGER=(bool, True),
    CELERY_BROKER_URL=(str, "redis://127.0.0.1:6379/0"),
    BOOKING_MIN_LEAD_MINUTES=(int, 15),
    BOOKING_SLOT_GRANULARITY_MINUTES=(int, 15),
    BOOKING_SERVICE_FEE_PERCENT=(str, "5"),
    SMS_PROVIDER=(str, "apps.notifications.providers.stubs.ConsoleSMSProvider"),
    PUSH_PROVIDER=(str, "apps.notifications.providers.stubs.ConsolePushProvider"),
    REALTIME_PROVIDER=(str, "apps.notifications.providers.stubs.ConsoleRealtimeProvider"),
    EMAIL_PROVIDER=(str, "apps.notifications.providers.stubs.ConsoleEmailProvider"),
)

# Read .env if present (not required in prod where env vars are injected).
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "phonenumber_field",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.notifications",
    "apps.vendors",
    "apps.catalog",
    "apps.subscriptions",
    "apps.search",
    "apps.bookings",
    "apps.reviews",
    "apps.dashboard",
    "apps.support",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://postgres:postgres@127.0.0.1:5432/service_marketplace",
    ),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = False

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.PhoneOrEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# argon2 first — satisfies the security NFR.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# DRF & JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.ScopedRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "otp": "5/min",
        "auth": "10/min",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_LIFETIME_MIN")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Smart Service Marketplace API",
    "DESCRIPTION": "Backend API for the Smart Service Marketplace (MVP).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("DEFAULT_LANGUAGE")
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("am", "Amharic"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = env("CORS_ALLOW_ALL_ORIGINS")

# ---------------------------------------------------------------------------
# Celery (eager async seam in MVP)
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = None

# ---------------------------------------------------------------------------
# Integration providers (stubbed — swap class paths to go live)
# ---------------------------------------------------------------------------
SMS_PROVIDER = env("SMS_PROVIDER")
PUSH_PROVIDER = env("PUSH_PROVIDER")
REALTIME_PROVIDER = env("REALTIME_PROVIDER")
EMAIL_PROVIDER = env("EMAIL_PROVIDER")

# ---------------------------------------------------------------------------
# Domain policy
# ---------------------------------------------------------------------------
OTP_TTL_SECONDS = env("OTP_TTL_SECONDS")
OTP_MAX_ATTEMPTS = env("OTP_MAX_ATTEMPTS")
BOOKING_MIN_LEAD_MINUTES = env("BOOKING_MIN_LEAD_MINUTES")
BOOKING_SLOT_GRANULARITY_MINUTES = env("BOOKING_SLOT_GRANULARITY_MINUTES")
# Platform service fee applied on top of the services subtotal (Decimal-parsed string).
BOOKING_SERVICE_FEE_PERCENT = env("BOOKING_SERVICE_FEE_PERCENT")

PHONENUMBER_DEFAULT_REGION = "ET"
