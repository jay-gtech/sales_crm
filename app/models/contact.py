"""
Contact model — production-ready, matching all form fields in contacts.html.
Uses the same Base as all other models in the project.
"""
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base


class Contact(Base):
    __tablename__ = "contacts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # ── Core identity ────────────────────────────────────────────────────────
    salutation        = Column(String, nullable=True)           # Mr./Mrs./Ms./Dr./Prof.
    first_name        = Column(String, nullable=True, index=True)
    last_name         = Column(String, nullable=False, index=True)  # required
    contact_owner     = Column(String, nullable=True)
    lead_source       = Column(String, nullable=True)

    # ── Links ────────────────────────────────────────────────────────────────
    account_name      = Column(String, nullable=True)
    vendor_name       = Column(String, nullable=True)

    # Soft FK → leads (nullable so contacts can exist without a lead)
    lead_id           = Column(Integer, ForeignKey("leads.id"), nullable=True)

    # ── Contact details ──────────────────────────────────────────────────────
    email             = Column(String, nullable=True, index=True)
    secondary_email   = Column(String, nullable=True)
    title             = Column(String, nullable=True)           # Job title
    department        = Column(String, nullable=True)

    # Phone numbers
    phone             = Column(String, nullable=True)
    other_phone       = Column(String, nullable=True)
    home_phone        = Column(String, nullable=True)
    mobile            = Column(String, nullable=True)
    fax               = Column(String, nullable=True)

    # Assistant
    assistant         = Column(String, nullable=True)
    asst_phone        = Column(String, nullable=True)

    # Personal
    date_of_birth     = Column(Date, nullable=True)
    email_opt_out     = Column(Boolean, default=False, nullable=False)

    # Social / messaging
    skype_id          = Column(String, nullable=True)
    twitter           = Column(String, nullable=True)
    reporting_to      = Column(String, nullable=True)

    # ── Mailing address ──────────────────────────────────────────────────────
    mailing_building  = Column(String, nullable=True)
    mailing_street    = Column(String, nullable=True)
    mailing_city      = Column(String, nullable=True)
    mailing_state     = Column(String, nullable=True)
    mailing_zip       = Column(String, nullable=True)
    mailing_country   = Column(String, nullable=True)
    mailing_lat       = Column(String, nullable=True)
    mailing_lng       = Column(String, nullable=True)

    # ── Other address ────────────────────────────────────────────────────────
    other_building    = Column(String, nullable=True)
    other_street      = Column(String, nullable=True)
    other_city        = Column(String, nullable=True)
    other_state       = Column(String, nullable=True)
    other_zip         = Column(String, nullable=True)
    other_country     = Column(String, nullable=True)
    other_lat         = Column(String, nullable=True)
    other_lng         = Column(String, nullable=True)

    # ── Description & media ──────────────────────────────────────────────────
    description       = Column(Text, nullable=True)
    contact_image     = Column(String, nullable=True)  # relative path to uploaded image

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ── Relationships ────────────────────────────────────────────────────────
    deals = relationship("Deal", back_populates="contact")
    lead = relationship("Lead", back_populates="contacts")
    activities = relationship("Activity", back_populates="contact")