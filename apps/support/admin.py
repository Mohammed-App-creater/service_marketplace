from django.contrib import admin

from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "complainant", "target_vendor", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["topic", "description", "complainant__email"]
