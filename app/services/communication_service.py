"""
Communication service — Email (SMTP) and WhatsApp (Twilio).

OPTIONAL: All functions are safe to call even if credentials are not configured.
Failures are logged and never re-raised to the caller — the CRM continues working
regardless of communication provider availability.

Usage:
    from app.services.communication_service import send_message
    ok = send_message(channel="email", to="user@example.com",
                      message="Hello", subject="CRM Update")
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Readiness checks ──────────────────────────────────────────────────────────

def email_configured() -> bool:
    """Return True if all required SMTP settings are present."""
    return bool(settings.SMTP_SERVER and settings.SMTP_EMAIL and settings.SMTP_PASSWORD)


def whatsapp_configured() -> bool:
    """Return True if all required Twilio settings are present."""
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_WHATSAPP_NUMBER
    )


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """
    Send an email via SMTP (TLS on port 587).
    Returns True on success, False on any failure or missing config.
    Never raises.
    """
    if not email_configured():
        logger.warning(
            "[COMM] Email not configured — set SMTP_SERVER / SMTP_EMAIL / SMTP_PASSWORD"
        )
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_EMAIL}>"
        msg["To"]      = to

        msg.attach(MIMEText(message, "plain"))
        if html_message:
            msg.attach(MIMEText(html_message, "html"))

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            smtp.sendmail(settings.SMTP_EMAIL, to, msg.as_string())

        logger.info("[COMM] Email sent → %s | subject: %s", to, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[COMM] Email auth failed — check SMTP_EMAIL / SMTP_PASSWORD")
    except smtplib.SMTPConnectError:
        logger.error("[COMM] Email connection failed — check SMTP_SERVER / SMTP_PORT")
    except Exception as exc:
        logger.error("[COMM] Email send failed → %s : %s", to, exc)

    return False


# ── WhatsApp (Twilio) ─────────────────────────────────────────────────────────

def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message via the Twilio API.
    to_number can be bare ('+14155551234') or prefixed ('whatsapp:+14155551234').
    Returns True on success, False on any failure or missing config.
    Never raises.
    """
    if not whatsapp_configured():
        logger.warning(
            "[COMM] WhatsApp not configured — set TWILIO_ACCOUNT_SID / "
            "TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER"
        )
        return False
    try:
        from twilio.rest import Client  # optional dependency

        def _wa(number: str) -> str:
            return number if number.startswith("whatsapp:") else f"whatsapp:{number}"

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        result = client.messages.create(
            body=message,
            from_=_wa(settings.TWILIO_WHATSAPP_NUMBER),
            to=_wa(to_number),
        )
        logger.info("[COMM] WhatsApp sent → %s | SID: %s", to_number, result.sid)
        return True

    except ImportError:
        logger.error(
            "[COMM] twilio package not installed. "
            "Add it with: pip install twilio  (then add to requirements.txt)"
        )
    except Exception as exc:
        logger.error("[COMM] WhatsApp send failed → %s : %s", to_number, exc)

    return False


# ── Unified dispatcher ────────────────────────────────────────────────────────

def send_message(
    channel: str,
    to: str,
    message: str,
    subject: str = "CRM Notification",
    html_message: Optional[str] = None,
) -> bool:
    """
    Unified dispatcher. channel must be 'email' or 'whatsapp'.
    Returns True on success, False on failure or unconfigured provider.
    Never raises — safe to call from anywhere in the CRM.
    """
    try:
        ch = channel.lower().strip()
        if ch == "email":
            return send_email(to=to, subject=subject, message=message,
                              html_message=html_message)
        if ch == "whatsapp":
            return send_whatsapp(to_number=to, message=message)

        logger.warning("[COMM] Unknown channel '%s' — use 'email' or 'whatsapp'", channel)
        return False

    except Exception as exc:
        # Last-resort safety net — should never reach here
        logger.error("[COMM] send_message unexpected error: %s", exc)
        return False
