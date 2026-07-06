from django.contrib import admin

from .models import CustomerReview, Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "vendor", "customer", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["vendor__business_name", "comment"]


@admin.register(CustomerReview)
class CustomerReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "vendor", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["customer__email", "vendor__business_name", "comment"]
