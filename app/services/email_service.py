import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import anyio

from app.core.email_config import email_settings

logger = logging.getLogger(__name__)

def email_configured() -> bool:
    """Return True if all required SMTP settings are present."""
    return bool(email_settings.SMTP_SERVER and email_settings.SMTP_EMAIL and email_settings.SMTP_PASSWORD)

def send_email_sync(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """
    Synchronous email sending logic.
    """
    if not email_configured():
        logger.warning("[EMAIL] Not configured — SMTP_SERVER / SMTP_EMAIL / SMTP_PASSWORD missing")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{email_settings.SMTP_FROM_NAME} <{email_settings.SMTP_EMAIL}>"
        msg["To"]      = to

        msg.attach(MIMEText(message, "plain"))
        if html_message:
            msg.attach(MIMEText(html_message, "html"))

        password = email_settings.SMTP_PASSWORD.replace(" ", "").strip()
        if email_settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(email_settings.SMTP_SERVER, email_settings.SMTP_PORT, timeout=10) as smtp:
                smtp.login(email_settings.SMTP_EMAIL, password)
                smtp.sendmail(email_settings.SMTP_EMAIL, to, msg.as_string())
        else:
            with smtplib.SMTP(email_settings.SMTP_SERVER, email_settings.SMTP_PORT, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(email_settings.SMTP_EMAIL, password)
                smtp.sendmail(email_settings.SMTP_EMAIL, to, msg.as_string())

        logger.info("[EMAIL] Sent → %s | subject: %s", to, subject)
        return True

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
    Asynchronous version of send_email using anyio.to_thread to avoid blocking.
    """
    return await anyio.to_thread.run_sync(
        send_email_sync, to, subject, message, html_message
    )
