from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["id", "email", "phone", "full_name", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff", "is_phone_verified", "is_email_verified"]
    search_fields = ["email", "phone", "full_name"]
    readonly_fields = ["id", "date_joined", "last_login"]
    fieldsets = (
        (None, {"fields": ("id", "email", "phone", "password")}),
        (
            "Profile",
            {
                "fields": (
                    "full_name",
                    "profile_photo",
                    "preferred_language",
                    "location_lat",
                    "location_lng",
                )
            },
        ),
        (
            "Role & status",
            {"fields": ("role", "is_active", "is_phone_verified", "is_email_verified")},
        ),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {"classes": ("wide",), "fields": ("email", "phone", "password1", "password2", "role")},
        ),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "purpose", "channel", "expires_at", "consumed_at", "attempts"]
    list_filter = ["purpose", "channel"]
    readonly_fields = ["id", "code_hash", "created_at"]
