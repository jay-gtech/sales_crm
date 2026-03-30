from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, UploadFile, File, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import csv
import io
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services import lead as lead_service
from app.services import permission_service as perm
from app.schemas.lead import LeadCreate
from app.db import base as base_models # noqa

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

LEAD_SOURCES = ['website', 'facebook', 'google_ads', 'email', 'whatsapp', 'manual']

@router.get("/leads", response_class=HTMLResponse)
async def list_leads(
    request: Request,
    search: str = None,
    status_filter: str = None,
    source_filter: str = None,
    owner_id: int = None,
    sort_by: str = None,
    view: str = 'table',
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        leads = lead_service.get_leads(db, search=search, status=status_filter, owner_id=owner_id, sort_by=sort_by, source=source_filter)
        # RBAC: filter to records this user may see (fail-safe — returns all on error)
        leads = perm.filter_by_visibility(leads, user, db, owner_attr="owner_id")
        return templates.TemplateResponse("leads.html", {
            "request": request,
            "leads": leads,
            "user": user,
            "title": "Leads",
            "lead_sources": LEAD_SOURCES,
            "can_delete": perm.can_delete(user, "leads"),
            "filters": {"search": search, "status": status_filter, "source": source_filter, "owner_id": owner_id, "sort_by": sort_by, "view": view},
            "error": error,
        })
    except Exception as e:
        import traceback
        import sys
        print("UNCAUGHT EXCEPTION IN /leads ROUTE:", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leads/create")
async def leads_create_redirect(_user=Depends(get_current_user)):
    """Guard against direct navigation to /leads/create — was causing 422."""
    return RedirectResponse(url="/leads", status_code=303)


@router.post("/leads")
async def create_lead(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    form_data = await request.form()
    lead_in = LeadCreate(
        salutation=form_data.get("salutation"),
        first_name=form_data.get("first_name"),
        last_name=form_data.get("last_name"),
        email=form_data.get("email"),
        phone=form_data.get("phone"),
        company=form_data.get("company"),
        title=form_data.get("title"),
        source=form_data.get("source"),
        rating=int(form_data.get("rating") or 0),
        status=form_data.get("status", "New"),
        owner_id=user.id
    )
    result = lead_service.create_lead(db, lead_in)
    if result is None:
        return RedirectResponse(url="/leads?error=email_exists", status_code=303)
    return RedirectResponse(url="/leads", status_code=303)

@router.post("/leads/import")
async def import_leads(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV.")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    for row in reader:
        lead_in = LeadCreate(
            first_name=row.get('first_name') or row.get('First Name'),
            last_name=row.get('last_name') or row.get('Last Name'),
            email=row.get('email') or row.get('Email'),
            phone=row.get('phone') or row.get('Phone', ''),
            company=row.get('company') or row.get('Company', ''),
            status=row.get('status') or row.get('Status', 'New'),
            owner_id=user.id
        )
        lead_service.create_lead(db, lead_in)  # returns None on duplicate — silently skipped

    return RedirectResponse(url="/leads", status_code=303)

@router.get("/leads/{lead_id}", response_class=HTMLResponse)
async def get_lead_detail(
    request: Request, 
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    lead = lead_service.get_lead(db, lead_id)
    if not lead:
        return RedirectResponse(url="/leads")
    from app.services.activity import get_activities_by_lead
    from app.models.email_log import EmailLog
    lead_activities = get_activities_by_lead(db, lead_id)
    email_logs = (
        db.query(EmailLog)
        .filter(EmailLog.related_type == "lead", EmailLog.related_id == lead_id)
        .order_by(EmailLog.created_at.desc())
        .all()
    )
    return templates.TemplateResponse("lead_detail.html", {
        "request": request, "lead": lead, "user": user,
        "lead_activities": lead_activities,
        "email_logs": email_logs,
        "title": f"Lead: {lead.first_name}"
    })

@router.post("/leads/{lead_id}/status")
async def update_status(
    lead_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    new_status = status_data.get("status")
    notes = status_data.get("notes")
    if not new_status:
        raise HTTPException(status_code=400, detail="Status is required")
    
    lead = lead_service.update_lead_status(db, lead_id, new_status, user.id, notes)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Status updated successfully", "status": lead.status}

@router.post("/leads/{lead_id}/delete")
async def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # RBAC: only admins may delete leads
    if not perm.can_delete(user, "leads"):
        return RedirectResponse(url="/leads", status_code=status.HTTP_303_SEE_OTHER)
    lead_service.delete_lead(db, lead_id)
    return RedirectResponse(url="/leads", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/leads/{lead_id}/history")
async def get_history(
    lead_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.models.lead_history import LeadHistory
    history = db.query(LeadHistory).filter(LeadHistory.lead_id == lead_id).order_by(LeadHistory.changed_at.desc()).all()
    # Fix #6: Serialize manually — raw ORM objects are not JSON-serializable by FastAPI without a response_model
    return [
        {
            "id": h.id,
            "old_status": h.old_status,
            "new_status": h.new_status,
            "notes": h.notes,
            "changed_at": h.changed_at.isoformat() if h.changed_at else None,
        }
        for h in history
    ]
