"""
POST /api/ai-assistant  — Global CRM AI assistant (Zia).
GET  /api/ai-assistant/ping — Health probe for the frontend.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.ai_router import route_query

router = APIRouter(prefix="/api/ai-assistant", tags=["ai-assistant"])


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language query")


@router.post("")
def query_assistant(
    body: AssistantRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Process a natural language CRM query.
    Returns: { message, items, links, type }
    Never raises on data errors — returns a friendly fallback instead.
    """
    return route_query(body.message, db, user)


@router.get("/ping")
def ping(user=Depends(get_current_user)):
    """Lightweight health check — lets the frontend verify auth before opening the panel."""
    return {"ok": True}
