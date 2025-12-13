"""Project members API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Project, ProjectMember, ProjectRole, User
from app.schemas import (
    ProjectMemberCreate,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectMemberUpdate,
)
from app.schemas.project_member import ProjectMemberUser

router = APIRouter()


async def get_project_with_access(
    project_id: UUID,
    db: AsyncSession,
    user: User,
    required_role: ProjectRole | None = None,
) -> Project:
    """Get project and verify user has access."""
    result = await db.execute(select(Project).options(selectinload(Project.members)).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check if user is owner
    if project.owner_id == user.id:
        return project

    # Check if user is a member
    member = next((m for m in project.members if m.user_id == user.id), None)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project",
        )

    # Check role requirement
    if required_role:
        role_hierarchy = {
            ProjectRole.VIEWER: 0,
            ProjectRole.EDITOR: 1,
            ProjectRole.OWNER: 2,
        }
        if role_hierarchy.get(member.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {required_role.value} role or higher",
            )

    return project


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
async def list_project_members(
    project_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """List all members of a project."""
    project = await get_project_with_access(project_id, db, current_user)

    # Get all members with user info
    result = await db.execute(
        select(ProjectMember).options(selectinload(ProjectMember.user)).where(ProjectMember.project_id == project_id)
    )
    members = result.scalars().all()

    # Add owner as a virtual member
    owner_result = await db.execute(select(User).where(User.id == project.owner_id))
    owner = owner_result.scalar_one()

    # Create owner member response
    owner_member = ProjectMemberResponse(
        id=project.id,  # Use project id for owner
        project_id=project_id,
        user_id=owner.id,
        role=ProjectRole.OWNER,
        created_at=project.created_at,
        user=ProjectMemberUser(
            id=owner.id,
            email=owner.email,
            full_name=owner.full_name,
        ),
    )

    member_responses = [owner_member] + [ProjectMemberResponse.model_validate(m) for m in members]

    return ProjectMemberListResponse(
        members=member_responses,
        total=len(member_responses),
    )


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: UUID,
    member_data: ProjectMemberCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Add a member to a project. Only owner can add members."""
    project = await get_project_with_access(project_id, db, current_user, ProjectRole.OWNER)

    # Verify current user is owner
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can add members",
        )

    # Find the user to add
    result = await db.execute(select(User).where(User.email == member_data.email))
    user_to_add = result.scalar_one_or_none()

    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {member_data.email} not found",
        )

    # Can't add owner as member
    if user_to_add.id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add project owner as a member",
        )

    # Check if already a member
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_to_add.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    # Create membership
    member = ProjectMember(
        project_id=project_id,
        user_id=user_to_add.id,
        role=member_data.role,
        invited_by_id=current_user.id,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    # Load user relationship
    await db.refresh(member, ["user"])

    return ProjectMemberResponse.model_validate(member)


@router.patch(
    "/{project_id}/members/{member_id}",
    response_model=ProjectMemberResponse,
)
async def update_project_member(
    project_id: UUID,
    member_id: UUID,
    member_data: ProjectMemberUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update a member's role. Only owner can update members."""
    project = await get_project_with_access(project_id, db, current_user, ProjectRole.OWNER)

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can update members",
        )

    # Find the member
    result = await db.execute(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Update role
    member.role = member_data.role
    await db.commit()
    await db.refresh(member)

    return ProjectMemberResponse.model_validate(member)


@router.delete(
    "/{project_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    project_id: UUID,
    member_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Remove a member from a project.

    Owner can remove anyone, members can remove themselves.
    """
    project = await get_project_with_access(project_id, db, current_user)

    # Find the member
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Check permission: owner can remove anyone, users can remove themselves
    is_owner = project.owner_id == current_user.id
    is_self = member.user_id == current_user.id

    if not is_owner and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove yourself or be the owner to remove others",
        )

    await db.delete(member)
    await db.commit()
