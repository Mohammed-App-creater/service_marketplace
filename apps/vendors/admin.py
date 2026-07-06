from django.contrib import admin

from .models import Category, Favorite, ScheduleBlock, Vendor, WorkingHours


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "business_name",
        "category",
        "status",
        "verification_status",
        "rating_avg",
        "rating_count",
    ]
    list_filter = ["verification_status", "status", "category"]
    search_fields = ["business_name", "owner__email", "owner__phone"]
    inlines = [WorkingHoursInline]


@admin.register(ScheduleBlock)
class ScheduleBlockAdmin(admin.ModelAdmin):
    list_display = ["id", "vendor", "start_datetime", "end_datetime", "reason"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "vendor", "created_at"]
