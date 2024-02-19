from django.contrib import admin
from django.contrib.admin import ModelAdmin

from order.models import Order, Payment


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    search_fields = ("email", "phone_number")
    list_display = ("email", "phone_number", "created_at", "total")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "status",
        "order",
        "session_url",
        "session_id",
    )
    list_filter = ("status",)
    search_fields = ("email", "session_id")
