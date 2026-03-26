from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ActivityCreate(BaseModel):
    title: Optional[str] = None
    activity_type: str = "Task"          # Call, Email, Meeting, Task
    status: str = "pending"              # pending, completed
    description: Optional[str] = None
    lead_id: Optional[int] = None
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None


class ActivityResponse(BaseModel):
    id: int
    title: Optional[str] = None
    activity_type: str
    status: str
    description: Optional[str] = None
    lead_id: Optional[int] = None
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
