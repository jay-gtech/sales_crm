from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services import ai as ai_service
from app.services import lead as lead_service

router = APIRouter(prefix="/ai", tags=["AI"])

@router.get("/score/{lead_id}")
async def get_lead_score(
    lead_id: int, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    lead = lead_service.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    score = ai_service.calculate_lead_score(lead)
    return {"lead_id": lead.id, "score": score}

@router.get("/email/{lead_id}")
async def generate_email(
    lead_id: int, 
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    lead = lead_service.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    draft = ai_service.generate_followup_email(lead)
    return {"lead_id": lead.id, "draft": draft}
