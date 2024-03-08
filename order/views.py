import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from liqpay import LiqPay
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response

from order.models import Order, OrderItem
from order.payment import create_payment
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
                order__is_paid=True,
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

    def create(self, request, *args, **kwargs):
        """
        Creates a stripe checkout session and returns its URL.
        """
        response = super().create(request, *args, **kwargs)
        payment_data = create_payment(response.data.get("id"), request)
        payment_url = requests.post(
            "https://www.liqpay.ua/api/3/checkout/",
            data=payment_data
        ).url
        return Response(
            data={"link": payment_url},
            status=201
        )

    @action(methods=["POST"], detail=True, url_path="payment-callback")
    def payment_callback(self, request, pk=None):
        order = get_object_or_404(Order, pk)
        liqpay = LiqPay(
            public_key=settings.LIQPAY_PUBLIC_KEY,
            private_key=settings.LIQPAY_PRIVATE_KEY
        )
        data = request.data.get("data")
        signature = request.data.get("signature")
        sign = liqpay.str_to_sign(settings.LIQPAY_PRIVATE_KEY + data + settings.LIQPAY_PRIVATE_KEY)
        if sign == signature:
            send_email.apply_async(args=(order.id,), countdown=60)
        return Response()
