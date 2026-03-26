from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Truncate to 72 bytes before verification to match hashing logic
    return pwd_context.verify(plain_password.encode("utf-8")[:72], hashed_password)

def get_password_hash(password: str) -> str:
    # Bcrypt has a hard 72-byte limit for the input secret. 
    # Encoding to UTF-8 and truncating ensures we never exceed this.
    return pwd_context.hash(password.encode("utf-8")[:72])
