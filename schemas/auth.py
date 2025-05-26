from pydantic import BaseModel, EmailStr
from typing import Optional

from uuid import UUID

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
  session: Optional[dict]
  user: Optional[dict]
