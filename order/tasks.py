import datetime
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import stripe
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from order.models import Order


stripe.api_key = settings.STRIPE_SECRET_KEY


@shared_task
def send_email(order_id: int) -> None:
    order = Order.objects.get(id=order_id)
    order.is_paid = True
    order.save()
    TO = [order.email, settings.EMAIL_HOST_USER]   # send notification to the owner
    FROM = "roksi4shop@gmail.com"
    message = MIMEMultipart("alternative")
    html_message = render_to_string(
        "email.html",
        {"order": order, "country": settings.CODES_OF_COUNTRIES.get(order.country)}
    )
    plain_message = strip_tags(html_message)
    message.attach(MIMEText(plain_message, "plain"))
    message.attach(MIMEText(html_message, "html"))
    message["Subject"] = "[Roksi] Order Created!"
    message["From"] = FROM

    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    server.ehlo()
    server.starttls()
    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    server.sendmail(FROM, TO, message.as_string())
    server.close()


@shared_task
def check_for_paid_orders():
    for order in Order.objects.prefetch_related("order_items"):
        if order.is_paid:
            continue
        tz = pytz.timezone(settings.TIME_ZONE)
        session = stripe.checkout.Session.retrieve(order.session_id)
        order_lifetime = datetime.datetime.now(tz=tz) - order.created_at

        if session.payment_status != "paid" and order_lifetime.seconds >= 900:
            order.delete()
        elif session.payment_status == "paid":
            send_email.delay(order.id)
