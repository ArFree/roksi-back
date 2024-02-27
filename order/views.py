from django.db import transaction
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from order.models import Order, OrderItem
from order.payment import create_payment
from order.serializers import OrderCreateSerializer, OrderItemListSerializer
from shop.services import Cart


class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    queryset = Order.objects.all()
    permission_classes = []
    authentication_classes = []

    def perform_create(self, serializer):
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

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        order = Order.objects.get(id=response.data.get("id"))
        return Response(data={"link": create_payment(order)}, status=201)


class OrderListView(generics.ListAPIView):
    serializer_class = OrderItemListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(
            order__email=self.request.user.email,
            order__is_paid=True,
        ).order_by(
            "-order__created_at"
        )
