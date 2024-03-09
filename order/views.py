from django.core.exceptions import PermissionDenied
from django.db import transaction
from rest_framework import viewsets, mixins
from rest_framework.exceptions import ValidationError

from order.models import OrderItem
from order.permissions import OrdersPermission
from order.serializers import OrderCreateSerializer, OrderItemListSerializer
from order.tasks import send_email
from shop.services import Cart


class OrderViewSet(viewsets.GenericViewSet,
                   mixins.CreateModelMixin,
                   mixins.ListModelMixin):
    permission_classes = [OrdersPermission]

    def get_queryset(self):
        queryset = OrderItem.objects.all()
        if self.action == "list" and not self.request.user.is_authenticated:
            raise PermissionDenied()

        if self.action == "list" and self.request.user.is_authenticated:
            return queryset.filter(
                order__email=self.request.user.email,
            ).order_by(
                "-order__created_at"
            )

        if self.action == "create":
            return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return OrderItemListSerializer

        if self.action == "create":
            return OrderCreateSerializer

    def perform_create(self, serializer):
        """
        Takes items from the cart and puts them into a new order
        """
        with transaction.atomic():
            cart = Cart(self.request)
            if not list(cart.cart.keys()):
                raise ValidationError("Put something in your cart please.")
            order = serializer.save(total=cart.get_total_price())
            product_ids = cart.cart.keys()
            for product_id in product_ids:
                OrderItem.objects.create(
                    order=order,
                    product_id=product_id,
                    quantity=cart.cart[product_id]["quantity"]
                )
            cart.clear()
            send_email.delay(order.id)
