"""User schemas."""

from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class UserBase(BaseSchema):
    """Base user schema."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=128)


class UserRead(UserBase, UUIDSchema, TimestampSchema):
    """Schema for reading a user."""

    is_active: bool


class UserLogin(BaseSchema):
    """Schema for user login."""

    email: EmailStr
    password: str


class Token(BaseSchema):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenPayload(BaseSchema):
    """Schema for JWT token payload."""

    sub: UUID
    exp: int


class RefreshTokenRequest(BaseSchema):
    """Schema for refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseSchema):
    """Schema for requesting a password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    """Schema for confirming a password reset."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
