"""
POST /api/send-message   — send email or WhatsApp (generic, no DB log)
POST /api/send-email     — send email and persist an EmailLog row
GET  /api/communication/status — which channels are configured

Provider failures return ok=False — never return 5xx.
"""
import logging
from typing import Optional, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.communication_service import (
    send_message,
    send_email,
    email_configured,
    whatsapp_configured,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["communication"])


class SendMessageRequest(BaseModel):
    channel: Literal["email", "whatsapp"] = Field(
        ..., description="Delivery channel: 'email' or 'whatsapp'"
    )
    recipient: str = Field(
        ..., description="Email address (email) or phone number with country code (whatsapp)"
    )
    message: str = Field(..., min_length=1, description="Message body")
    subject: Optional[str] = Field(
        "CRM Notification", description="Subject line (email only, ignored for WhatsApp)"
    )


class SendMessageResponse(BaseModel):
    ok: bool
    channel: str
    recipient: str
    detail: str


class ChannelStatusResponse(BaseModel):
    email: bool
    whatsapp: bool


@router.post("/send-message", response_model=SendMessageResponse)
def send_message_endpoint(
    body: SendMessageRequest,
    _user=Depends(get_current_user),
):
    """
    Send a message via the specified channel.
    Never raises on provider failure — returns ok=False with a detail message.
    """
    ok = send_message(
        channel=body.channel,
        to=body.recipient,
        message=body.message,
        subject=body.subject or "CRM Notification",
    )
    return SendMessageResponse(
        ok=ok,
        channel=body.channel,
        recipient=body.recipient,
        detail=(
            "Message sent successfully."
            if ok
            else "Message could not be delivered. Check server logs or verify provider config."
        ),
    )


@router.get("/communication/status", response_model=ChannelStatusResponse)
def channel_status(_user=Depends(get_current_user)):
    """
    Returns which communication channels are currently configured.
    Useful for the UI to show/hide send options.
    """
    return ChannelStatusResponse(
        email=email_configured(),
        whatsapp=whatsapp_configured(),
    )


# ── Dedicated email endpoint with DB logging ──────────────────────────────────

class SendEmailRequest(BaseModel):
    to:           str           = Field(..., description="Recipient email address")
    subject:      str           = Field(..., min_length=1)
    body:         str           = Field(..., min_length=1)
    related_type: Optional[str] = Field(None, description="'lead' or 'deal'")
    related_id:   Optional[int] = Field(None, description="PK of the related record")


class SendEmailResponse(BaseModel):
    ok:      bool
    detail:  str
    log_id:  Optional[int] = None


@router.post("/send-email", response_model=SendEmailResponse)
def send_email_endpoint(
    body:  SendEmailRequest,
    db:    Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Send an email via SMTP and persist an EmailLog row regardless of outcome.
    Never raises on SMTP failure — returns ok=False with a safe detail message.
    """
    from app.models.email_log import EmailLog

    ok = send_email(to=body.to, subject=body.subject, message=body.body)

    status_str = "sent" if ok else "failed"
    log = EmailLog(
        to_email     = body.to,
        subject      = body.subject,
        body         = body.body,
        status       = status_str,
        related_type = body.related_type,
        related_id   = body.related_id,
        sent_by_id   = user.id,
    )
    log_id: Optional[int] = None
    try:
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id
        logger.info(
            "[EMAIL] log_id=%s status=%s to=%s subject=%r related=%s/%s",
            log_id, status_str, body.to, body.subject, body.related_type, body.related_id,
        )
    except Exception as exc:
        logger.error("[EMAIL] Failed to persist EmailLog: %s", exc)
        db.rollback()

    return SendEmailResponse(
        ok=ok,
        detail="Email sent successfully." if ok else "Email could not be delivered. Check SMTP configuration.",
        log_id=log_id,
    )


@router.post("/test-email", response_model=SendEmailResponse)
async def test_email_endpoint(user=Depends(get_current_user)):
    """
    Send a test email to the currently logged-in user to verify SMTP config.
    Uses the async email service to avoid blocking the event loop.
    """
    from app.services.email_service import send_email_async

    subject = "CRM Email Test"
    body = (
        f"Hello {user.email},\n\n"
        "This is a test email from your CRM Platform to verify SMTP configuration.\n\n"
        "Regards,\nThe CRM Team"
    )
    html_body = (
        f"<h3>Hello {user.email}</h3>"
        "<p>This is a <b>test email</b> from your CRM Platform to verify SMTP configuration.</p>"
        "<p>Regards,<br>The CRM Team</p>"
    )

    ok = await send_email_async(
        to=user.email, subject=subject, message=body, html_message=html_body
    )

    return SendEmailResponse(
        ok=ok,
        detail="Test email sent successfully." if ok
               else "Test email failed. Check SMTP configuration and server logs.",
    )
