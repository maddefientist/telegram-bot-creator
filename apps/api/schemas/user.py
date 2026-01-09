"""User-related schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from models.user import UserRole, AuthMethod


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: uuid.UUID
    email: str | None
    wallet_address: str | None
    auth_method: AuthMethod
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for user updates."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    role: str
    exp: datetime
    iat: datetime
    csrf: str


class WalletNonceRequest(BaseModel):
    """Request nonce for wallet signature."""

    wallet_address: str = Field(min_length=32, max_length=44)


class WalletNonceResponse(BaseModel):
    """Nonce response."""

    nonce: str
    message: str
    expires_in: int  # seconds


class WalletRegister(BaseModel):
    """Schema for wallet registration."""

    wallet_address: str = Field(min_length=32, max_length=44)
    signature: str
    nonce: str
    email: EmailStr | None = None  # Optional email for notifications


class WalletLogin(BaseModel):
    """Schema for wallet login."""

    wallet_address: str = Field(min_length=32, max_length=44)
    signature: str
    nonce: str
