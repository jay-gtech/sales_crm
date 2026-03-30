"""
Communication service — Dispatcher for Email and WhatsApp.
Refactored to use modular email_service.
"""
import logging
from typing import Optional

from app.services.email_service import send_email_sync, send_email_async, email_configured
from app.core.config import settings # for WhatsApp settings

logger = logging.getLogger(__name__)

def whatsapp_configured() -> bool:
    """Return True if all required Twilio settings are present."""
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_WHATSAPP_NUMBER
    )

def send_email(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """
    Sync legacy wrapper for modular email_service.
    """
    return send_email_sync(to, subject, message, html_message)

async def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message via the Twilio API.
    """
    if not whatsapp_configured():
        return False
    try:
        from twilio.rest import Client
        def _wa(number: str) -> str:
            return number if number.startswith("whatsapp:") else f"whatsapp:{number}"
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        result = client.messages.create(
            body=message,
            from_=_wa(settings.TWILIO_WHATSAPP_NUMBER),
            to=_wa(to_number),
        )
        logger.info("[COMM] WhatsApp sent → %s", to_number)
        return True
    except Exception as exc:
        logger.error("[COMM] WhatsApp failed: %s", exc)
        return False

def send_message(
    channel: str,
    to: str,
    message: str,
    subject: str = "CRM Notification",
    html_message: Optional[str] = None,
) -> bool:
    """
    Unified dispatcher (Sync).
    """
    ch = channel.lower().strip()
    if ch == "email":
        return send_email_sync(to, subject, message, html_message)
    if ch == "whatsapp":
        # Note: WhatsApp is currently sync here because Twilio Client is sync.
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(send_whatsapp(to, message))
    return False
