from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    password: str = Field(..., min_length=8)
    # role removed - admin created manually in seed data only


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    customer_id: int
    name: str
    email: EmailStr
    phone: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    user: UserResponse
    token: str


class LoginResponse(BaseModel):
    user: UserResponse
    token: str
