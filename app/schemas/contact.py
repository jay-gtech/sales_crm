"""
Contact Pydantic schemas — aligned with Contact SQLAlchemy model.
Supports Pydantic v1 (orm_mode) with v2 fall-through compatibility.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator


# ── Create ───────────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    # Core identity
    salutation:       Optional[str] = None
    first_name:       Optional[str] = None
    last_name:        str                        # required
    contact_owner:    Optional[str] = None
    lead_source:      Optional[str] = None

    # Links
    account_name:     Optional[str] = None
    vendor_name:      Optional[str] = None
    lead_id:          Optional[int] = None

    # Contact details
    email:            Optional[str] = None
    secondary_email:  Optional[str] = None
    title:            Optional[str] = None
    department:       Optional[str] = None

    # Phones
    phone:            Optional[str] = None
    other_phone:      Optional[str] = None
    home_phone:       Optional[str] = None
    mobile:           Optional[str] = None
    fax:              Optional[str] = None

    # Assistant
    assistant:        Optional[str] = None
    asst_phone:       Optional[str] = None

    # Personal
    date_of_birth:    Optional[date] = None
    email_opt_out:    bool = False

    # Social / messaging
    skype_id:         Optional[str] = None
    twitter:          Optional[str] = None
    reporting_to:     Optional[str] = None

    # Mailing address
    mailing_building: Optional[str] = None
    mailing_street:   Optional[str] = None
    mailing_city:     Optional[str] = None
    mailing_state:    Optional[str] = None
    mailing_zip:      Optional[str] = None
    mailing_country:  Optional[str] = None
    mailing_lat:      Optional[str] = None
    mailing_lng:      Optional[str] = None

    # Other address
    other_building:   Optional[str] = None
    other_street:     Optional[str] = None
    other_city:       Optional[str] = None
    other_state:      Optional[str] = None
    other_zip:        Optional[str] = None
    other_country:    Optional[str] = None
    other_lat:        Optional[str] = None
    other_lng:        Optional[str] = None

    # Description & media
    description:      Optional[str] = None
    contact_image:    Optional[str] = None   # relative path set by service layer

    @validator("last_name")
    def last_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("last_name must not be empty")
        return v


# ── Update (all optional) ────────────────────────────────────────────────────

class ContactUpdate(BaseModel):
    salutation:       Optional[str] = None
    first_name:       Optional[str] = None
    last_name:        Optional[str] = None
    contact_owner:    Optional[str] = None
    lead_source:      Optional[str] = None
    account_name:     Optional[str] = None
    vendor_name:      Optional[str] = None
    lead_id:          Optional[int] = None
    email:            Optional[str] = None
    secondary_email:  Optional[str] = None
    title:            Optional[str] = None
    department:       Optional[str] = None
    phone:            Optional[str] = None
    other_phone:      Optional[str] = None
    home_phone:       Optional[str] = None
    mobile:           Optional[str] = None
    fax:              Optional[str] = None
    assistant:        Optional[str] = None
    asst_phone:       Optional[str] = None
    date_of_birth:    Optional[date] = None
    email_opt_out:    Optional[bool] = None
    skype_id:         Optional[str] = None
    twitter:          Optional[str] = None
    reporting_to:     Optional[str] = None
    mailing_building: Optional[str] = None
    mailing_street:   Optional[str] = None
    mailing_city:     Optional[str] = None
    mailing_state:    Optional[str] = None
    mailing_zip:      Optional[str] = None
    mailing_country:  Optional[str] = None
    mailing_lat:      Optional[str] = None
    mailing_lng:      Optional[str] = None
    other_building:   Optional[str] = None
    other_street:     Optional[str] = None
    other_city:       Optional[str] = None
    other_state:      Optional[str] = None
    other_zip:        Optional[str] = None
    other_country:    Optional[str] = None
    other_lat:        Optional[str] = None
    other_lng:        Optional[str] = None
    description:      Optional[str] = None
    contact_image:    Optional[str] = None


# ── Response ─────────────────────────────────────────────────────────────────

class ContactResponse(BaseModel):
    id:               int
    salutation:       Optional[str]
    first_name:       Optional[str]
    last_name:        str
    contact_owner:    Optional[str]
    lead_source:      Optional[str]
    account_name:     Optional[str]
    vendor_name:      Optional[str]
    lead_id:          Optional[int]
    email:            Optional[str]
    secondary_email:  Optional[str]
    title:            Optional[str]
    department:       Optional[str]
    phone:            Optional[str]
    other_phone:      Optional[str]
    home_phone:       Optional[str]
    mobile:           Optional[str]
    fax:              Optional[str]
    assistant:        Optional[str]
    asst_phone:       Optional[str]
    date_of_birth:    Optional[date]
    email_opt_out:    bool
    skype_id:         Optional[str]
    twitter:          Optional[str]
    reporting_to:     Optional[str]
    mailing_building: Optional[str]
    mailing_street:   Optional[str]
    mailing_city:     Optional[str]
    mailing_state:    Optional[str]
    mailing_zip:      Optional[str]
    mailing_country:  Optional[str]
    mailing_lat:      Optional[str]
    mailing_lng:      Optional[str]
    other_building:   Optional[str]
    other_street:     Optional[str]
    other_city:       Optional[str]
    other_state:      Optional[str]
    other_zip:        Optional[str]
    other_country:    Optional[str]
    other_lat:        Optional[str]
    other_lng:        Optional[str]
    description:      Optional[str]
    contact_image:    Optional[str]
    created_at:       datetime

    class Config:
        from_attributes = True   # Pydantic v2
