import smtplib
import socket
import ssl

from django.conf import settings


CONFIGURATION_FAILURE = "configuration"
AUTHENTICATION_FAILURE = "authentication"
CONNECTION_FAILURE = "connection"
TIMEOUT_FAILURE = "timeout"
RECIPIENT_FAILURE = "recipient"
UNKNOWN_FAILURE = "unknown"


class ContactEmailConfigurationError(Exception):
    """Raised when the SMTP backend lacks a required protected setting."""


class ContactEmailDeliveryCountError(Exception):
    """Raised when the email backend does not accept exactly one message."""


def validate_contact_email_configuration():
    """Fail safely when production SMTP settings are incomplete."""
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        return

    required_values = (
        settings.EMAIL_HOST,
        settings.EMAIL_HOST_USER,
        settings.EMAIL_HOST_PASSWORD,
        settings.DEFAULT_FROM_EMAIL,
        settings.OMNILAB_CONTACT_TO_EMAIL,
    )
    if not all(required_values) or settings.EMAIL_PORT < 1:
        raise ContactEmailConfigurationError


def get_contact_email_failure_category(error):
    """Map mail exceptions to a stable category without exposing details."""
    if isinstance(error, (TimeoutError, socket.timeout)):
        return TIMEOUT_FAILURE
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return AUTHENTICATION_FAILURE
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        return RECIPIENT_FAILURE
    if isinstance(
        error,
        (
            ContactEmailConfigurationError,
            smtplib.SMTPNotSupportedError,
        ),
    ):
        return CONFIGURATION_FAILURE
    if isinstance(
        error,
        (
            smtplib.SMTPConnectError,
            smtplib.SMTPHeloError,
            smtplib.SMTPServerDisconnected,
            ConnectionError,
            socket.gaierror,
            ssl.SSLError,
            OSError,
        ),
    ):
        return CONNECTION_FAILURE
    return UNKNOWN_FAILURE
