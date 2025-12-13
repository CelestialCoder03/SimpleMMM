"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import rate_limit
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.repositories.password_reset import PasswordResetRepository
from app.repositories.user import UserRepository
from app.schemas.user import (
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserRead,
)
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
async def register(
    user_in: UserCreate,
    db: DbSession,
) -> UserRead:
    """Register a new user."""
    user_repo = UserRepository(db)

    # Check if email already exists
    existing_user = await user_repo.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = await user_repo.create_user(user_in)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> Token:
    """Login and get access token."""
    user_repo = UserRepository(db)

    user = await user_repo.authenticate(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DbSession,
) -> Token:
    """Refresh access token using refresh token."""
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_repo = UserRepository(db)
    from uuid import UUID

    user = await user_repo.get_by_id(UUID(user_id))

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: CurrentUser,
) -> UserRead:
    """Get current user information."""
    return UserRead.model_validate(current_user)


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit(max_requests=3, window_seconds=60))],
)
async def request_password_reset(
    request: PasswordResetRequest,
    db: DbSession,
) -> dict:
    """
    Request a password reset.

    Sends an email with a reset link if the email exists.
    Always returns success to prevent email enumeration.
    """
    user_repo = UserRepository(db)
    reset_repo = PasswordResetRepository(db)

    user = await user_repo.get_by_email(request.email)

    if user and user.is_active:
        # Create reset token
        token = await reset_repo.create_token(user.id)

        # Send email (async, don't wait)
        try:
            await send_password_reset_email(
                to=user.email,
                reset_token=token.token,
                user_name=user.full_name,
            )
        except Exception:
            # Log but don't expose errors to user
            pass

    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: DbSession,
) -> dict:
    """
    Confirm password reset with token and new password.
    """
    reset_repo = PasswordResetRepository(db)
    user_repo = UserRepository(db)

    # Find valid token
    token = await reset_repo.get_valid_token(request.token)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get user
    user = await user_repo.get_by_id(token.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or inactive",
        )

    # Update password
    await user_repo.update_password(user, request.new_password)

    # Mark token as used
    await reset_repo.mark_as_used(token)

    return {"message": "Password has been reset successfully."}


@router.post("/password-reset/validate")
async def validate_reset_token(
    token: str,
    db: DbSession,
) -> dict:
    """
    Validate a password reset token without using it.

    Useful for checking if a token is valid before showing the reset form.
    """
    reset_repo = PasswordResetRepository(db)

    reset_token = await reset_repo.get_valid_token(token)

    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"valid": True}
