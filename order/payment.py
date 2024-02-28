import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_payment(order):
    """
    Creates a Stripe checkout session out of an order.
    """
    price = int(order.total * 100)
    success_url = "http://localhost:3000/#/success/"
    cancel_url = "http://localhost:3000/"
    session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Order {order.id}"
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

    order.session_id = session.id
    order.save()

    return session.url
