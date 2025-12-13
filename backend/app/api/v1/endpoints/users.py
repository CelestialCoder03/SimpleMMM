"""User endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.repositories.user import UserRepository
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: CurrentUser,
) -> UserRead:
    """Get current user profile."""
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    user_in: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserRead:
    """Update current user profile."""
    user_repo = UserRepository(db)

    # Check if email is being changed and if it's already taken
    if user_in.email and user_in.email != current_user.email:
        existing = await user_repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    updated_user = await user_repo.update_user(current_user, user_in)
    return UserRead.model_validate(updated_user)
