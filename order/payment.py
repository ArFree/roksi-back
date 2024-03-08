import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from liqpay.liqpay3 import LiqPay

from order.models import Order


def create_payment(order_id: int, request):
    """
    Creates a LiqPay checkout session out of an order.
    """
    order = get_object_or_404(Order, id=order_id)
    server_url = request.build_absolute_uri(
        reverse_lazy("order:order-payment-callback", kwargs={"pk": order_id})
    )
    liqpay = LiqPay(
        public_key=settings.LIQPAY_PUBLIC_KEY,
        private_key=settings.LIQPAY_PRIVATE_KEY
    )
    params = {
        "public_key": settings.LIQPAY_PUBLIC_KEY,
        "private_key": settings.LIQPAY_PRIVATE_KEY,
        "action": "pay",
        "amount": str(order.total),
        "currency": "USD",
        "description": "Roksi art",
        "order_id": order.id,
        "version": "3",
        "server_url": server_url,
    }
    data, signature = liqpay.get_data_end_signature("cnb_form", params)
    return {"data": data, "signature": signature}
