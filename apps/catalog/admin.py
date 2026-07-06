from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "vendor", "duration_minutes", "price", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "vendor__business_name"]
