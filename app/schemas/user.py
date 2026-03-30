from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id:        int
    email:     EmailStr
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type:   str


# ── Settings / Role management ────────────────────────────────────────────────

class UserProfile(BaseModel):
    id:         int
    email:      str
    full_name:  Optional[str] = None
    role:       str = "sales_rep"
    manager_id: Optional[int] = None
    is_active:  bool = True

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None


class UserRoleUpdate(BaseModel):
    user_id:    int
    role:       str
    manager_id: Optional[int] = None
