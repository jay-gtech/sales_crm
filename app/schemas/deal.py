from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DealCreate(BaseModel):
    name: str
    amount: float = 0.0
    description: Optional[str] = None
    stage: str = "New"
    closing_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    contact_id: int
    lead_id: Optional[int] = None
    owner_id: int

class DealUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    stage: Optional[str] = None
    closing_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    contact_id: Optional[int] = None
    lead_id: Optional[int] = None
    owner_id: Optional[int] = None

class DealResponse(BaseModel):
    id: int
    name: str
    amount: float
    description: Optional[str]
    stage: str
    closing_date: Optional[datetime]
    follow_up_date: Optional[datetime]
    last_stage_change: datetime
    contact_id: int
    lead_id: Optional[int]
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True
