import datetime
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from liqpay import LiqPay

from order.models import Order


@shared_task
def send_email(order_id: int) -> None:
    """
    Sends order confirmation emails both to the customer and the shop owner.
    """
    order = Order.objects.get(id=order_id)
    verify_order_status(order)
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


def verify_order_status(order) -> None:
    liqpay = LiqPay(
        public_key=settings.LIQPAY_PUBLIC_KEY,
        private_key=settings.LIQPAY_PRIVATE_KEY
    )
    response = liqpay.api(
        "request", {
            "action": "status",
            "version": "3",
            "order_id": order.id,
        }
    )
    if response.get("status") == "success":
        order.status = "paid"
        order.save()
        order.refresh_from_db()
