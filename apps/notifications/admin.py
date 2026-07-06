from django.contrib import admin

from .models import DeviceToken, NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "channel", "template_key", "recipient", "status", "sent_at", "created_at"]
    list_filter = ["channel", "status"]
    search_fields = ["template_key", "recipient__email", "recipient__phone"]
    readonly_fields = [f.name for f in NotificationLog._meta.fields]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "platform", "is_active", "created_at"]
    list_filter = ["platform", "is_active"]
