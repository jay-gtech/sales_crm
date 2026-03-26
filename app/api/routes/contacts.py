"""
Contact API routes — /contacts prefix.
Handles:
  GET    /contacts          → contact list
  GET    /contacts/new      → create form
  POST   /contacts/new      → submit new contact (multipart/form-data incl. image)
  GET    /contacts/{id}     → contact detail (JSON)
  DELETE /contacts/{id}     → delete contact (JSON)
  POST   /contacts/convert/{lead_id} → convert lead → contact
"""
from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Request, UploadFile, status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import contact as contact_service
from app.services import lead as lead_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])
templates = Jinja2Templates(directory="app/templates")

# ── Upload configuration ─────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join("app", "static", "uploads", "contacts")
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_image(file: UploadFile) -> Optional[str]:
    """
    Validate and save an uploaded contact image.
    Returns the web-accessible relative path, or None if no file supplied.
    Raises HTTPException on invalid file.
    """
    if not file or not file.filename:
        return None

    # Validate MIME via content-type header (fast, no file read needed)
    content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or ""
    if content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{content_type}'. "
                   f"Allowed: {', '.join(sorted(ALLOWED_MIMES))}",
        )

    # Generate a safe, unique filename
    ext = os.path.splitext(file.filename)[-1].lower() or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, unique_name)

    # Read & size-check
    contents = file.file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be smaller than 5 MB.",
        )

    with open(save_path, "wb") as f:
        f.write(contents)

    # Return the path that can be used in <img src="">
    return f"/static/uploads/contacts/{unique_name}"


def _build_contact_dict(
    salutation: str,
    first_name: str,
    last_name: str,
    contact_owner: str,
    lead_source: str,
    account_name: str,
    vendor_name: str,
    email: str,
    secondary_email: str,
    title: str,
    department: str,
    phone: str,
    other_phone: str,
    home_phone: str,
    mobile: str,
    fax: str,
    assistant: str,
    asst_phone: str,
    date_of_birth: str,
    email_opt_out: str,
    skype_id: str,
    twitter: str,
    reporting_to: str,
    mailing_building: str,
    mailing_street: str,
    mailing_city: str,
    mailing_state: str,
    mailing_zip: str,
    mailing_country: str,
    mailing_lat: str,
    mailing_lng: str,
    other_building: str,
    other_street: str,
    other_city: str,
    other_state: str,
    other_zip: str,
    other_country: str,
    other_lat: str,
    other_lng: str,
    description: str,
    image_path: Optional[str],
) -> dict:
    """Assemble the raw dict passed to the service layer."""
    from datetime import date as _date

    dob = None
    if date_of_birth:
        try:
            dob = _date.fromisoformat(date_of_birth)
        except ValueError:
            dob = None

    return {
        "salutation":        salutation or None,
        "first_name":        first_name.strip() or None,
        "last_name":         last_name.strip(),
        "contact_owner":     contact_owner or None,
        "lead_source":       lead_source or None,
        "account_name":      account_name or None,
        "vendor_name":       vendor_name or None,
        "email":             email.strip() or None,
        "secondary_email":   secondary_email.strip() or None,
        "title":             title or None,
        "department":        department or None,
        "phone":             phone or None,
        "other_phone":       other_phone or None,
        "home_phone":        home_phone or None,
        "mobile":            mobile or None,
        "fax":               fax or None,
        "assistant":         assistant or None,
        "asst_phone":        asst_phone or None,
        "date_of_birth":     dob,
        "email_opt_out":     email_opt_out == "1",
        "skype_id":          skype_id or None,
        "twitter":           twitter or None,
        "reporting_to":      reporting_to or None,
        "mailing_building":  mailing_building or None,
        "mailing_street":    mailing_street or None,
        "mailing_city":      mailing_city or None,
        "mailing_state":     mailing_state or None,
        "mailing_zip":       mailing_zip or None,
        "mailing_country":   mailing_country or None,
        "mailing_lat":       mailing_lat or None,
        "mailing_lng":       mailing_lng or None,
        "other_building":    other_building or None,
        "other_street":      other_street or None,
        "other_city":        other_city or None,
        "other_state":       other_state or None,
        "other_zip":         other_zip or None,
        "other_country":     other_country or None,
        "other_lat":         other_lat or None,
        "other_lng":         other_lng or None,
        "description":       description or None,
        "contact_image":     image_path,
    }


# ── GET /contacts — contact list ──────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def list_contacts(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contacts = contact_service.get_contacts(db)
    return templates.TemplateResponse(
        "contacts.html",
        {
            "request":  request,
            "contacts": contacts,
            "user":     user,
            "title":    "Contacts",
            "view":     "list",       # tells the template which view to render
        },
    )


# ── GET /contacts/new — create form ───────────────────────────────────────────

@router.get("/new", response_class=HTMLResponse)
async def new_contact_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "contacts.html",
        {
            "request": request,
            "user":    user,
            "title":   "Create Contact",
            "view":    "create",
            "msg":     request.query_params.get("msg"),
            "error":   request.query_params.get("error"),
        },
    )


# ── POST /contacts/new — submit form ──────────────────────────────────────────

@router.post("/new")
async def create_contact(
    request: Request,
    # ── Core identity ──
    salutation:        str = Form(""),
    first_name:        str = Form(""),
    last_name:         str = Form(...),
    contact_owner:     str = Form(""),
    lead_source:       str = Form(""),
    # ── Links ──
    account_name:      str = Form(""),
    vendor_name:       str = Form(""),
    # ── Contact details ──
    email:             str = Form(""),
    secondary_email:   str = Form(""),
    title:             str = Form(""),
    department:        str = Form(""),
    # ── Phones ──
    phone:             str = Form(""),
    other_phone:       str = Form(""),
    home_phone:        str = Form(""),
    mobile:            str = Form(""),
    fax:               str = Form(""),
    # ── Assistant ──
    assistant:         str = Form(""),
    asst_phone:        str = Form(""),
    # ── Personal ──
    date_of_birth:     str = Form(""),
    email_opt_out:     str = Form(""),   # "1" if checked, "" otherwise
    # ── Social ──
    skype_id:          str = Form(""),
    twitter:           str = Form(""),
    reporting_to:      str = Form(""),
    # ── Mailing address ──
    mailing_building:  str = Form(""),
    mailing_street:    str = Form(""),
    mailing_city:      str = Form(""),
    mailing_state:     str = Form(""),
    mailing_zip:       str = Form(""),
    mailing_country:   str = Form(""),
    mailing_lat:       str = Form(""),
    mailing_lng:       str = Form(""),
    # ── Other address ──
    other_building:    str = Form(""),
    other_street:      str = Form(""),
    other_city:        str = Form(""),
    other_state:       str = Form(""),
    other_zip:         str = Form(""),
    other_country:     str = Form(""),
    other_lat:         str = Form(""),
    other_lng:         str = Form(""),
    # ── Description & file ──
    description:       str = Form(""),
    contact_image:     UploadFile = File(None),
    save_and_new:      str = Form(""),   # "1" from saveAndNew()
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Validate required field (belt & suspenders alongside HTML required attr)
    if not last_name.strip():
        return RedirectResponse(
            url="/contacts/new?error=Last+Name+is+required",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Handle image upload securely
    try:
        image_path = _save_image(contact_image)
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/contacts/new?error={exc.detail.replace(' ', '+')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    data = _build_contact_dict(
        salutation, first_name, last_name, contact_owner, lead_source,
        account_name, vendor_name,
        email, secondary_email, title, department,
        phone, other_phone, home_phone, mobile, fax,
        assistant, asst_phone,
        date_of_birth, email_opt_out,
        skype_id, twitter, reporting_to,
        mailing_building, mailing_street, mailing_city, mailing_state,
        mailing_zip, mailing_country, mailing_lat, mailing_lng,
        other_building, other_street, other_city, other_state,
        other_zip, other_country, other_lat, other_lng,
        description, image_path,
    )

    try:
        contact_service.create_contact(db, data)
    except Exception as exc:
        logger.exception("Contact creation failed: %s", exc)
        return RedirectResponse(
            url="/contacts/new?error=Failed+to+save+contact.+Please+try+again.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    redirect_url = "/contacts/new?msg=Contact+created+successfully" if save_and_new == "1" else "/contacts?msg=Contact+created+successfully"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)


# ── GET /contacts/{id} — detail (JSON) ────────────────────────────────────────

@router.get("/{contact_id}")
async def get_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    contact = contact_service.get_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {
        "id":          contact.id,
        "first_name":  contact.first_name,
        "last_name":   contact.last_name,
        "email":       contact.email,
        "phone":       contact.phone,
        "mobile":      contact.mobile,
        "title":       contact.title,
        "department":  contact.department,
        "account_name":contact.account_name,
        "lead_source": contact.lead_source,
        "created_at":  contact.created_at.isoformat() if contact.created_at else None,
    }


# ── DELETE /contacts/{id} ─────────────────────────────────────────────────────

@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = contact_service.delete_contact(db, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return JSONResponse({"detail": "Contact deleted"})


# ── POST /contacts/convert/{lead_id} — lead → contact ────────────────────────

@router.post("/convert/{lead_id}")
async def convert_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lead = lead_service.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Check if this lead was already converted
    existing = db.query(__import__("app.models.contact", fromlist=["Contact"]).Contact)\
        .filter_by(lead_id=lead.id).first()
    if existing:
        return RedirectResponse(url="/contacts?msg=Lead+already+converted", status_code=status.HTTP_303_SEE_OTHER)

    data = {
        "first_name": lead.first_name,
        "last_name":  lead.last_name or "Unknown",
        "email":      lead.email,
        "phone":      lead.phone,
        "lead_id":    lead.id,
        "lead_source": getattr(lead, "lead_source", None),
    }

    try:
        contact_service.create_contact(db, data)
        # Mark lead as converted
        lead.status = "Qualified"
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Lead conversion failed: %s", exc)
        raise HTTPException(status_code=500, detail="Conversion failed. Please try again.")

    return RedirectResponse(url="/contacts?msg=Lead+converted+successfully", status_code=status.HTTP_303_SEE_OTHER)
