import datetime
from decimal import Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from shop.models import Product


class Order(models.Model):
    email = models.EmailField(max_length=255)
    instagram = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                r"^\s*-?[0-9]{1,15}\s*$",
                message="Make sure your phone number contains up to 10 digits"
            )
        ]
    )

    country = models.CharField(
        max_length=65, blank=True, null=True, choices=settings.CODES_OF_COUNTRIES.items()
    )
    city = models.CharField(
        max_length=255, blank=True, null=True
    )
    postal_code = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.email}, {self.created_at}"


class OrderItem(models.Model):
    objects = None
    product = models.ForeignKey(
        "shop.Product", on_delete=models.CASCADE, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items"
    )

    def calculate_total(self) -> Decimal:
        return self.product.price * self.quantity

    @property
    def get_date(self) -> str:
        return self.order.created_at.strftime("%Y.%m.%d")

    def __str__(self) -> str:
        return f"{self.product}, quantity = {self.quantity}"


class Payment(models.Model):
    class StatusChoices(models.TextChoices):
        PAID = "PAID"
        PENDING = "PENDING"
        EXPIRED = "EXPIRED"

    status = models.CharField(max_length=7, choices=StatusChoices.choices)
    order = models.OneToOneField("Order", on_delete=models.CASCADE)
    session_url = models.URLField(max_length=512, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
