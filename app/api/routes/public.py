"""
Public & Mock Lead Capture Routes
===================================
Phase 5: Lead Source Integration

/api/public/lead        — real public endpoint (no auth, for website forms)
/api/mock/facebook-lead — simulated Facebook Lead Ad
/api/mock/google-lead   — simulated Google Ads form
/api/mock/email-lead    — simulated inbound email
/api/mock/whatsapp-lead — simulated WhatsApp message

All mock endpoints are demo-only — no external APIs are called.
All endpoints are non-blocking: failure returns a JSON error, never a 500 crash.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.lead_capture import capture_lead, simulate_incoming_message

router = APIRouter()


# ── Shared request schema ──────────────────────────────────────────────────

class LeadCapturePayload(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None


def _split_name(full_name: str):
    parts = full_name.strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


# ── Public endpoint (website form) ────────────────────────────────────────

@router.post("/api/public/lead", tags=["Public Lead Capture"])
def public_lead_capture(payload: LeadCapturePayload, db: Session = Depends(get_db)):
    """
    Accepts a lead from any public website form.
    No authentication required.
    """
    first, last = _split_name(payload.name)
    lead = capture_lead(
        db=db,
        first_name=first,
        last_name=last,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        source="website",
        source_details="Captured via public website form",
    )
    if not lead:
        raise HTTPException(status_code=500, detail="Lead capture failed")
    return {"status": "ok", "lead_id": lead.id, "source": lead.source}


# ── Mock: Facebook Lead Ad ─────────────────────────────────────────────────

@router.post("/api/mock/facebook-lead", tags=["Mock Sources"])
def mock_facebook_lead(payload: LeadCapturePayload, db: Session = Depends(get_db)):
    """
    Simulates a lead arriving from a Facebook Lead Ad campaign.
    Demo only — no real Facebook API is called.
    """
    first, last = _split_name(payload.name)
    lead = capture_lead(
        db=db,
        first_name=first,
        last_name=last,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        source="facebook",
        source_details="Mock: Facebook Lead Ad — campaign simulation",
    )
    if not lead:
        raise HTTPException(status_code=500, detail="Lead capture failed")
    return {"status": "ok", "lead_id": lead.id, "source": lead.source}


# ── Mock: Google Ads ───────────────────────────────────────────────────────

@router.post("/api/mock/google-lead", tags=["Mock Sources"])
def mock_google_lead(payload: LeadCapturePayload, db: Session = Depends(get_db)):
    """
    Simulates a lead arriving from a Google Ads lead form extension.
    Demo only — no real Google Ads API is called.
    """
    first, last = _split_name(payload.name)
    lead = capture_lead(
        db=db,
        first_name=first,
        last_name=last,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        source="google_ads",
        source_details="Mock: Google Ads Lead Form Extension — simulation",
    )
    if not lead:
        raise HTTPException(status_code=500, detail="Lead capture failed")
    return {"status": "ok", "lead_id": lead.id, "source": lead.source}


# ── Mock: Inbound Email ────────────────────────────────────────────────────

@router.post("/api/mock/email-lead", tags=["Mock Sources"])
def mock_email_lead(payload: LeadCapturePayload, db: Session = Depends(get_db)):
    """
    Simulates a lead captured from an inbound email.
    Demo only — uses simulate_incoming_message().
    """
    lead = simulate_incoming_message(
        db=db,
        source="email",
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
    )
    if not lead:
        raise HTTPException(status_code=500, detail="Lead capture failed")
    return {"status": "ok", "lead_id": lead.id, "source": lead.source}


# ── Mock: WhatsApp Message ─────────────────────────────────────────────────

@router.post("/api/mock/whatsapp-lead", tags=["Mock Sources"])
def mock_whatsapp_lead(payload: LeadCapturePayload, db: Session = Depends(get_db)):
    """
    Simulates a lead captured from a WhatsApp Business message.
    Demo only — uses simulate_incoming_message().
    """
    lead = simulate_incoming_message(
        db=db,
        source="whatsapp",
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
    )
    if not lead:
        raise HTTPException(status_code=500, detail="Lead capture failed")
    return {"status": "ok", "lead_id": lead.id, "source": lead.source}
