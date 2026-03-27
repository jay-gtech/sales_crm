"""
POST /api/send-message

Authenticated endpoint to send a message via email or WhatsApp.
Provider failures return ok=False with a detail string — they never return 5xx.
"""
from typing import Optional, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services.communication_service import (
    send_message,
    email_configured,
    whatsapp_configured,
)

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
