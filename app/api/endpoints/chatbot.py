from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.api.deps import get_current_user
from app.services.chatbot_service import process_query

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def handle_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    response_text = process_query(request.query, db, user)
    return {"response": response_text}
