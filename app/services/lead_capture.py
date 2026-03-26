"""
Lead Capture Service
====================
Unified entry point for all lead sources (website form, Facebook, Google Ads,
email simulation, WhatsApp simulation).

Rules:
- Never raises — all exceptions are caught and return None on failure.
- Deduplicates by email: if a lead with the same email already exists,
  returns the existing lead without creating a duplicate.
- source_details provides a free-text audit trail of how the lead arrived.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.lead import Lead

VALID_SOURCES = {"website", "facebook", "google_ads", "email", "whatsapp", "manual"}


def capture_lead(
    db: Session,
    first_name: str,
    last_name: str = "",
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    source: str = "manual",
    source_details: Optional[str] = None,
) -> Optional[Lead]:
    """
    Core lead creation used by all capture paths.
    Returns the existing lead if the email already exists (no duplicate).
    Returns None if an unexpected error occurs.
    """
    try:
        # Deduplicate by email
        if email:
            existing = db.query(Lead).filter(Lead.email == email).first()
            if existing:
                return existing

        safe_source = source if source in VALID_SOURCES else "manual"

        lead = Lead(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email or None,
            phone=phone or None,
            company=company or None,
            source=safe_source,
            source_details=source_details,
            status="New",
            lead_score=0,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead
    except Exception as exc:
        db.rollback()
        print(f"[lead_capture] capture_lead failed: {exc}")
        return None


def simulate_incoming_message(
    db: Session,
    source: str,
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
) -> Optional[Lead]:
    """
    Simulates an inbound message (email / WhatsApp) arriving as a new lead.
    For demo purposes — no real API or messaging service is called.
    """
    parts = name.strip().split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else ""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return capture_lead(
        db=db,
        first_name=first,
        last_name=last,
        email=email,
        phone=phone,
        company=company,
        source=source,
        source_details=f"Simulated {source} message — received {timestamp}",
    )
