from django.contrib import admin

from .models import Booking, BookingItem


class BookingItemInline(admin.TabularInline):
    model = BookingItem
    extra = 0
    readonly_fields = ["service", "service_name", "price", "duration_minutes"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
        "vendor",
        "scheduled_start",
        "status",
        "total",
    ]
    list_filter = ["status"]
    search_fields = ["customer__email", "customer__phone", "vendor__business_name"]
    readonly_fields = ["slot", "created_at", "updated_at"]
    inlines = [BookingItemInline]
