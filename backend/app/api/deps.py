"""API dependencies for authentication and database access."""

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import async_session as async_session_maker
from app.models import Project, ProjectRole, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency for getting current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_project_with_access_check(
    project_id: UUID,
    db: AsyncSession,
    user: User,
    min_role: ProjectRole = ProjectRole.VIEWER,
) -> Project:
    """
    Get a project and verify the user has access with at least the specified role.

    Args:
        project_id: The project UUID
        db: Database session
        user: Current user
        min_role: Minimum role required (VIEWER, EDITOR, or OWNER)

    Returns:
        The project if user has access

    Raises:
        HTTPException: If project not found or user lacks access
    """
    result = await db.execute(select(Project).options(selectinload(Project.members)).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Owner has full access
    if project.owner_id == user.id:
        return project

    # Check membership
    member = next((m for m in project.members if m.user_id == user.id), None)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    # Check role hierarchy
    role_hierarchy = {
        ProjectRole.VIEWER: 0,
        ProjectRole.EDITOR: 1,
        ProjectRole.OWNER: 2,
    }

    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires {min_role.value} role or higher",
        )

    return project


def require_project_access(min_role: ProjectRole = ProjectRole.VIEWER):
    """
    Dependency factory for requiring project access with a minimum role.

    Usage:
        @router.get("/{project_id}/data")
        async def get_data(
            project: Project = Depends(require_project_access(ProjectRole.VIEWER)),
        ):
            ...
    """

    async def dependency(
        project_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> Project:
        return await get_project_with_access_check(project_id, db, current_user, min_role)

    return dependency
