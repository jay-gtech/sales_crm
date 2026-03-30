from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services import deal as deal_service
from app.services import permission_service as perm
from app.schemas.deal import DealCreate, DealUpdate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/deals", response_class=HTMLResponse)
async def list_deals(
    request: Request, 
    stage: str = None,
    owner_id: int = None,
    search: str = None,
    view_type: str = "list", # list or pipeline
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    skip = (page - 1) * limit
    deals, total_count = deal_service.get_deals(
        db, skip=skip, limit=limit if view_type == "list" else 1000,
        stage=stage, owner_id=owner_id, search=search,
        sort_by=sort_by, order=order
    )
    # RBAC: filter to records this user may see (fail-safe — returns all on error)
    deals = perm.filter_by_visibility(deals, user, db, owner_attr="owner_id")
    total_count = len(deals)
    stats = deal_service.get_pipeline_stats(db)
    
    # Organize deals by stage for Pipeline view
    stages = [
        "New", "Qualification", "Needs Analysis", 
        "Proposal", "Negotiation", "Closed Won", "Closed Lost"
    ]
    pipeline = {s: [] for s in stages}
    
    if view_type == "pipeline":
        for deal in deals:
            if deal.stage in pipeline:
                pipeline[deal.stage].append(deal)
            else:
                if "New" not in pipeline: pipeline["New"] = []
                pipeline["New"].append(deal)

    from app.services import contact as contact_service
    contacts = contact_service.get_contacts(db)
    owners = db.query(User).all()

    return templates.TemplateResponse("deals.html", {
        "request": request,
        "deals": deals,
        "pipeline": pipeline,
        "user": user,
        "stats": stats,
        "contacts": contacts,
        "owners": owners,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "view_type": view_type,
        "title": "Deals",
        "can_delete": perm.can_delete(user, "deals"),
        "current_filters": {
            "stage": stage,
            "owner_id": owner_id,
            "search": search,
            "sort_by": sort_by,
            "order": order,
        }
    })

@router.get("/deals/create")
async def deals_create_redirect(_user=Depends(get_current_user)):
    """Guard against direct navigation to /deals/create — was causing 422."""
    return RedirectResponse(url="/deals", status_code=303)


@router.post("/deals")
async def create_deal(
    request: Request,
    name: str = Form(...),
    amount: float = Form(...),
    contact_id: int = Form(None),
    owner_id: int = Form(None),
    lead_id: int = Form(None),
    stage: str = Form("New"),
    description: str = Form(None),
    closing_date: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    closing_dt = None
    if closing_date:
        try:
            closing_dt = datetime.strptime(closing_date, "%Y-%m-%d")
        except ValueError:
            pass
        
    deal_in = DealCreate(
        name=name,
        amount=amount,
        contact_id=contact_id,
        closing_date=closing_dt,
        owner_id=owner_id or user.id,
        lead_id=lead_id,
        stage=stage,
        description=description
    )
    deal_service.create_deal(db, deal_in, user.id)
    return RedirectResponse(url="/deals", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/deals/move/{deal_id}")
async def move_deal(
    deal_id: int,
    stage: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    deal_service.update_deal(db, deal_id, DealUpdate(stage=stage), user.id)
    return RedirectResponse(url="/deals", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/deals/convert/{lead_id}")
async def convert_lead(
    lead_id: int,
    deal_name: str = Form(...),
    deal_amount: float = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.services import lead as lead_service
    deal = lead_service.convert_lead_to_deal(
        db, lead_id, user.id, deal_name, deal_amount
    )
    if not deal:
        raise HTTPException(status_code=400, detail="Lead conversion failed")
    return RedirectResponse(url="/deals", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/deals/{deal_id}", response_class=HTMLResponse)
async def get_deal(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    deal = deal_service.get_deal(db, deal_id)
    if not deal:
        return RedirectResponse(url="/deals", status_code=303)

    # Fetch history
    from app.models.deal_history import DealHistory
    from app.models.email_log import EmailLog
    history = db.query(DealHistory).filter(DealHistory.deal_id == deal_id).order_by(DealHistory.changed_at.desc()).all()

    # Fetch activities
    from app.services import activity as activity_service
    activities = activity_service.get_activities_by_deal(db, deal_id)

    # Fetch email logs
    email_logs = (
        db.query(EmailLog)
        .filter(EmailLog.related_type == "deal", EmailLog.related_id == deal_id)
        .order_by(EmailLog.created_at.desc())
        .all()
    )

    return templates.TemplateResponse("deal_detail.html", {
        "request": request,
        "deal": deal,
        "history": history,
        "activities": activities,
        "email_logs": email_logs,
        "user": user,
        "title": f"Deal: {deal.name}"
    })

@router.get("/deals/{deal_id}/edit", response_class=HTMLResponse)
async def edit_deal_form(
    request: Request,
    deal_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    deal = deal_service.get_deal(db, deal_id)
    if not deal:
        return RedirectResponse(url="/deals", status_code=303)
    
    from app.services import contact as contact_service
    contacts = contact_service.get_contacts(db)
    stages = ["New", "Qualification", "Needs Analysis", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    
    return templates.TemplateResponse("deal_edit.html", {
        "request": request,
        "deal": deal,
        "contacts": contacts,
        "stages": stages,
        "user": user,
        "title": f"Edit Deal: {deal.name}"
    })

@router.post("/deals/{deal_id}")
async def update_deal_route(
    deal_id: int,
    name: str = Form(...),
    amount: float = Form(...),
    stage: str = Form(...),
    description: str = Form(None),
    closing_date: str = Form(None),
    follow_up_date: str = Form(None),
    contact_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    from app.schemas.deal import DealUpdate
    from datetime import datetime
    
    closing_dt = None
    if closing_date:
        try:
            closing_dt = datetime.strptime(closing_date, "%Y-%m-%d")
        except ValueError:
            pass
            
    follow_up_dt = None
    if follow_up_date:
        try:
            follow_up_dt = datetime.strptime(follow_up_date, "%Y-%m-%d")
        except ValueError:
            pass
    
    deal_update = DealUpdate(
        name=name,
        amount=amount,
        stage=stage,
        description=description,
        closing_date=closing_dt,
        follow_up_date=follow_up_dt,
        contact_id=contact_id
    )
    
    updated_deal = deal_service.update_deal(db, deal_id, deal_update, user.id)
    if not updated_deal:
        return RedirectResponse(url="/deals", status_code=303)
    
    return RedirectResponse(url=f"/deals/{deal_id}", status_code=status.HTTP_303_SEE_OTHER)
