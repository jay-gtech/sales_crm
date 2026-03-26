from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MeetingInsightBase(BaseModel):
    type: str  # 'point' or 'task'
    content: str
    deadline: Optional[str] = None
    owner: Optional[str] = None

class MeetingInsightResponse(MeetingInsightBase):
    id: int
    meeting_id: int

    class Config:
        from_attributes = True

class MeetingCreate(BaseModel):
    title: str
    transcript: str

class MeetingResponse(BaseModel):
    id: int
    title: str
    transcript: str
    created_by: int
    created_at: datetime
    insights: List[MeetingInsightResponse] = []

    class Config:
        from_attributes = True
