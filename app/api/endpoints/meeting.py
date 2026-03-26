from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.meeting import MeetingCreate
from app.services.meeting_service import process_meeting

router = APIRouter(prefix="/meetings", tags=["Meetings"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/process", response_class=HTMLResponse)
async def process_new_meeting(
    request: Request,
    title: str = Form(...),
    transcript: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if not title.strip() or not transcript.strip():
        return RedirectResponse(url="/?error=MissingInput", status_code=303)
        
    meeting_in = MeetingCreate(title=title, transcript=transcript)
    db_meeting = process_meeting(db, meeting_in, user.id)
    
    # Render Dashboard directly to show results without needing a redirect
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "processed_meeting": db_meeting
    })
