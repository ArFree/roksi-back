import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import stripe
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from order.models import Order, Payment


stripe.api_key = settings.STRIPE_SECRET_KEY


@shared_task
def send_email(order_id: int) -> None:
    order = Order.objects.get(id=order_id)
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


def get_expired_sessions():
    sessions = stripe.checkout.Session.list().data
    return [
        session.id
        for session in sessions
        if session.status == "expired" and session.payment_status == "unpaid"
    ]


@shared_task
def mark_expired_payments():
    expired_sessions = get_expired_sessions()
    for payment in Payment.objects.all():
        if payment.session_id in expired_sessions:
            payment.status = "EXPIRED"
            payment.save()
