import stripe
from django.conf import settings
from django.urls import reverse_lazy

from order.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment(request, order):

    payment = Payment.objects.create(
        order=order,
        status="PENDING",
    )

    price = int(order.total * 100)
    success_url = "http://localhost:3000/success"
    cancel_url = request.build_absolute_uri(
        reverse_lazy("order:payment-cancel", kwargs={"pk": payment.id})
    )
    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": order.id,
                    },
                    "unit_amount": price,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        customer_creation="always",
    )

    payment.session_id = session.id
    payment.save()
    payment.session_url = session.url
    payment.save()

    return session.url
