"""
POST /api/zia-llm — Enhanced LLM-powered ZIA assistant.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.ai_router import route_query

router = APIRouter(prefix="/api/zia-llm", tags=["zia-llm"])

class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Natural language query")

@router.post("")
async def query_zia_llm(
    body: AssistantRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Process a natural language CRM query using the enhanced LLM-first router.
    Returns: { message, items, links, type }
    """
    return await route_query(body.message, db, user)
