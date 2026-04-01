from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.lead_ai_service import get_lead_summary_ai
from app.models.user import User

router = APIRouter(prefix="/leads", tags=["lead_ai"])

@router.get("/{id}/summary")
async def get_lead_summary(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an AI-generated summary for a specific lead.
    """
    result = get_lead_summary_ai(db, id)
    if result.get("summary") == "Lead not found.":
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return result
