"""
Modular email service.

Provides both sync and async wrappers around SMTP sending.
All functions are safe to call even when SMTP is not configured —
they log a warning and return False without raising.

Usage:
    from app.services.email_service import send_email_sync, send_email_async

    # synchronous
    ok = send_email_sync(to="user@example.com", subject="Hello", message="Body")

    # async (non-blocking, uses anyio thread offload)
    ok = await send_email_async(to="user@example.com", subject="Hello", message="Body")
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import anyio

from app.core.email_config import email_settings

logger = logging.getLogger(__name__)


def email_configured() -> bool:
    """Return True only when all three required SMTP fields are set."""
    return bool(
        email_settings.SMTP_SERVER
        and email_settings.SMTP_EMAIL
        and email_settings.SMTP_PASSWORD
    )


def send_email_sync(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """
    Send an email via SMTP (synchronous).
    Supports port 465 (SSL) and port 587 (STARTTLS).
    Returns True on success, False on any failure or missing config.
    Never raises.
    """
    if not email_configured():
        logger.warning(
            "[EMAIL] Not configured — set SMTP_SERVER / SMTP_EMAIL / SMTP_PASSWORD"
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{email_settings.SMTP_FROM_NAME} <{email_settings.SMTP_EMAIL}>"
        msg["To"]      = to

        msg.attach(MIMEText(message, "plain"))
        if html_message:
            msg.attach(MIMEText(html_message, "html"))

        # Strip accidental spaces from app-password style credentials
        password = email_settings.SMTP_PASSWORD.replace(" ", "").strip()

        if email_settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(
                email_settings.SMTP_SERVER, email_settings.SMTP_PORT, timeout=10
            ) as smtp:
                smtp.login(email_settings.SMTP_EMAIL, password)
                smtp.sendmail(email_settings.SMTP_EMAIL, to, msg.as_string())
        else:
            with smtplib.SMTP(
                email_settings.SMTP_SERVER, email_settings.SMTP_PORT, timeout=10
            ) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(email_settings.SMTP_EMAIL, password)
                smtp.sendmail(email_settings.SMTP_EMAIL, to, msg.as_string())

        logger.info("[EMAIL] Sent → %s | subject: %s", to, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[EMAIL] Auth failed — check SMTP_EMAIL / SMTP_PASSWORD")
    except smtplib.SMTPConnectError:
        logger.error("[EMAIL] Connection failed — check SMTP_SERVER / SMTP_PORT")
    except Exception as exc:
        logger.error("[EMAIL] Send failed to %s: %s", to, exc)

    return False


async def send_email_async(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """
    Async wrapper — offloads the blocking SMTP call to a thread via anyio.
    Safe to await from any async FastAPI route or background task.
    """
    return await anyio.to_thread.run_sync(
        lambda: send_email_sync(to, subject, message, html_message)
    )
