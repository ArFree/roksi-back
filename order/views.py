import stripe
from django.db import transaction
from django.http import HttpResponseRedirect
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from order.models import Order, OrderItem, Payment
from order.payment import create_payment
from order.serializers import OrderCreateSerializer, PaymentSerializer, OrderItemListSerializer
from order.tasks import send_email
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
            if order.payment_method == "CASH":
                send_email.delay(order.id)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        order = Order.objects.get(id=response.data.get("id"))
        if order.payment_method == "CARD":
            return HttpResponseRedirect(redirect_to=create_payment(request, order))
        return response


class OrderListView(generics.ListAPIView):
    serializer_class = OrderItemListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderItem.objects.filter(order__email=self.request.user.email).order_by(
            "-order__created_at"
        )


class PaymentViewSet(
    viewsets.GenericViewSet, ListModelMixin, RetrieveModelMixin
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.select_related("order").prefetch_related("order__order_items")

        return queryset.filter(order__email=self.request.user.email)

    def get_serializer_class(self):
        return PaymentSerializer

    @action(methods=["GET"], detail=True, url_path="success", permission_classes=[])
    def success(self, request, pk=None):
        """
        Endpoint to which Stripe redirects users after a successful payment.
        Here Payment status becomes "PAID"
        """
        payment = Payment.objects.get(id=pk)
        session = stripe.checkout.Session.retrieve(payment.session_id)
        if session.payment_status == "paid":
            customer = stripe.Customer.retrieve(session.customer)
            payment.status = "PAID"
            payment.save()
            send_email(payment.order.id)
            return Response(f"Thank you, {customer.name}!", status=200)

        return Response(f"Not yet, pay first: {session.url}", status=403)

    @action(methods=["GET"], detail=True, url_path="cancel", permission_classes=[])
    def cancel(self, request, pk=None):
        """
        Endpoint to which Stripe redirects users after a canceled payment.
        """
        return Response(
            "Please don't forget to complete this payment "
            "later (the session is active for 24 hours). "
            "Link to the session can be found on the payment detail page.",
            status=200,
        )
