from django.contrib import admin

from .models import SubscriptionChange, SubscriptionPlan, VendorSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "billing_period", "max_services", "is_active"]
    list_filter = ["is_active", "billing_period"]


@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "vendor", "plan", "status", "started_at"]
    list_filter = ["status", "plan"]


@admin.register(SubscriptionChange)
class SubscriptionChangeAdmin(admin.ModelAdmin):
    list_display = ["id", "subscription", "from_plan", "to_plan", "created_at"]
