
from flask import render_template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app import settings


def send_reset_password_email(email, password):
    template = render_template('emails/reset_password.html', password=password)

    if settings.DEBUG:
        email = 'raphael@futurefitbusiness.org'

    message = Mail(
        from_email='no-reply@em796.futurefit.business',
        to_emails=email,
        subject='Password Reset',
        html_content=template)

    sendgrid_client = SendGridAPIClient(api_key=settings.secrets.SENDGRID_API_KEY)
    response = sendgrid_client.send(message)


def send_welcome_email(email, password):
    template = render_template('emails/welcome.html', password=password, email=email)

    if settings.DEBUG:
        email = 'raphael@futurefitbusiness.org'

    message = Mail(
        from_email='no-reply@em796.futurefit.business',
        to_emails=email,
        subject='Welcome to the Impact Benchmark Tool',
        html_content=template)

    sendgrid_client = SendGridAPIClient(api_key=settings.secrets.SENDGRID_API_KEY)
    response = sendgrid_client.send(message)
