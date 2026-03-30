"""
Communication service — unified dispatcher for Email and WhatsApp.

Email logic is delegated to app.services.email_service (modular, supports
both port 465 SSL and port 587 STARTTLS, has sync + async variants).

All functions are safe to call even when providers are not configured —
they log a warning and return False without raising.
"""
import logging
from typing import Optional

from app.services.email_service import (
    send_email_sync,
    send_email_async,   # noqa: F401 — re-exported for callers that need async
    email_configured,   # noqa: F401 — re-exported for route-level config checks
)
from app.core.config import settings   # WhatsApp credentials live in main config

logger = logging.getLogger(__name__)


# ── re-export email helpers so existing callers don't need to change ──────────

def send_email(
    to: str,
    subject: str,
    message: str,
    html_message: Optional[str] = None,
) -> bool:
    """Synchronous email send — backward-compatible wrapper for email_service."""
    return send_email_sync(to, subject, message, html_message)


# ── WhatsApp (Twilio) — kept synchronous to avoid event-loop issues ───────────

def whatsapp_configured() -> bool:
    """Return True if all required Twilio settings are present."""
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_WHATSAPP_NUMBER
    )


def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message via the Twilio API (synchronous).
    Returns True on success, False on failure or missing config.
    Never raises.
    """
    if not whatsapp_configured():
        logger.warning(
            "[COMM] WhatsApp not configured — set TWILIO_ACCOUNT_SID / "
            "TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER"
        )
        return False
    try:
        from twilio.rest import Client   # optional dependency

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
            "Run: pip install twilio"
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
    Unified synchronous dispatcher.
    channel must be 'email' or 'whatsapp'.
    Returns True on success, False on failure or unconfigured provider.
    Never raises.
    """
    try:
        ch = channel.lower().strip()
        if ch == "email":
            return send_email_sync(to, subject, message, html_message)
        if ch == "whatsapp":
            return send_whatsapp(to_number=to, message=message)

        logger.warning("[COMM] Unknown channel '%s' — use 'email' or 'whatsapp'", channel)
        return False

    except Exception as exc:
        logger.error("[COMM] send_message unexpected error: %s", exc)
        return False
