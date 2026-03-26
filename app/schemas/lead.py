from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LeadBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str = "New"
    salutation: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    website: Optional[str] = None
    secondary_email: Optional[str] = None
    skype_id: Optional[str] = None
    twitter: Optional[str] = None
    rating: Optional[int] = 0
    tag: Optional[str] = None
    owner_id: Optional[int] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    salutation: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    website: Optional[str] = None
    secondary_email: Optional[str] = None
    skype_id: Optional[str] = None
    twitter: Optional[str] = None
    rating: Optional[int] = None
    tag: Optional[str] = None
    lead_score: Optional[int] = None
    is_converted: Optional[bool] = None

class LeadResponse(LeadBase):
    id: int
    lead_score: int
    is_converted: bool
    created_at: datetime
    updated_at: Optional[datetime]
    owner_id: Optional[int]

    class Config:
        from_attributes = True
