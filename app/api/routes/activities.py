from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services import activity as activity_service
from app.services import lead as lead_service
from app.schemas.activity import ActivityCreate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/activities", response_class=HTMLResponse)
async def list_activities(
    request: Request,
    filter_type: Optional[str] = None,
    filter_status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.activity import Activity
    query = db.query(Activity)
    if filter_type:
        query = query.filter(Activity.activity_type == filter_type)
    if filter_status:
        query = query.filter(Activity.status == filter_status)
    activities = query.order_by(Activity.created_at.desc()).limit(100).all()

    leads = lead_service.get_leads(db)

    from app.models.deal import Deal
    deals = db.query(Deal).order_by(Deal.created_at.desc()).all()

    return templates.TemplateResponse("activities.html", {
        "request": request,
        "activities": activities,
        "leads": leads,
        "deals": deals,
        "user": user,
        "title": "Activities",
        "filter_type": filter_type or "",
        "filter_status": filter_status or "",
    })


@router.post("/activities")
async def create_activity(
    request: Request,
    title: str = Form(...),
    activity_type: str = Form("Task"),
    status_val: str = Form("pending"),
    description: str = Form(""),
    lead_id: Optional[int] = Form(None),
    deal_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    activity_in = ActivityCreate(
        title=title,
        activity_type=activity_type,
        status=status_val,
        description=description or None,
        lead_id=lead_id or None,
        deal_id=deal_id or None,
    )
    activity_service.create_activity(db, activity_in)
    return RedirectResponse(url="/activities", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/activities/{activity_id}/complete")
async def complete_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    activity_service.mark_complete(db, activity_id)
    return RedirectResponse(url="/activities", status_code=status.HTTP_303_SEE_OTHER)
