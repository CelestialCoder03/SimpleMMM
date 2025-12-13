"""Variable Group management endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.variable_group import VariableGroup
from app.repositories.project import ProjectRepository
from app.schemas.variable_group import (
    VariableGroupCreate,
    VariableGroupList,
    VariableGroupRead,
    VariableGroupUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/variable-groups", tags=["Variable Groups"])


async def verify_project_access(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Verify user has access to project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not await project_repo.is_owner(project, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )


@router.get("", response_model=VariableGroupList)
async def list_variable_groups(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> VariableGroupList:
    """List all variable groups for a project."""
    await verify_project_access(project_id, current_user, db)

    # Get all groups for the project
    result = await db.execute(
        select(VariableGroup).where(VariableGroup.project_id == project_id).order_by(VariableGroup.name)
    )
    groups = result.scalars().all()

    items = [VariableGroupRead.model_validate(g) for g in groups]
    return VariableGroupList(items=items, total=len(items))


@router.post("", response_model=VariableGroupRead, status_code=status.HTTP_201_CREATED)
async def create_variable_group(
    project_id: UUID,
    group_in: VariableGroupCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> VariableGroupRead:
    """Create a new variable group."""
    await verify_project_access(project_id, current_user, db)

    # Check for duplicate name
    existing = await db.execute(
        select(VariableGroup).where(VariableGroup.project_id == project_id).where(VariableGroup.name == group_in.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Variable group with name '{group_in.name}' already exists",
        )

    # Create group
    group = VariableGroup(
        project_id=project_id,
        name=group_in.name,
        description=group_in.description,
        variables=group_in.variables,
        color=group_in.color,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return VariableGroupRead.model_validate(group)


@router.get("/{group_id}", response_model=VariableGroupRead)
async def get_variable_group(
    project_id: UUID,
    group_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> VariableGroupRead:
    """Get a specific variable group."""
    await verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(VariableGroup).where(VariableGroup.id == group_id).where(VariableGroup.project_id == project_id)
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable group not found",
        )

    return VariableGroupRead.model_validate(group)


@router.put("/{group_id}", response_model=VariableGroupRead)
async def update_variable_group(
    project_id: UUID,
    group_id: UUID,
    group_in: VariableGroupUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> VariableGroupRead:
    """Update a variable group."""
    await verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(VariableGroup).where(VariableGroup.id == group_id).where(VariableGroup.project_id == project_id)
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable group not found",
        )

    # Check for duplicate name if name is being changed
    if group_in.name and group_in.name != group.name:
        existing = await db.execute(
            select(VariableGroup)
            .where(VariableGroup.project_id == project_id)
            .where(VariableGroup.name == group_in.name)
            .where(VariableGroup.id != group_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variable group with name '{group_in.name}' already exists",
            )

    # Update fields
    update_data = group_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)

    return VariableGroupRead.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variable_group(
    project_id: UUID,
    group_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a variable group."""
    await verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(VariableGroup).where(VariableGroup.id == group_id).where(VariableGroup.project_id == project_id)
    )
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable group not found",
        )

    await db.delete(group)
    await db.commit()


@router.get("/check-overlap", response_model=dict)
async def check_variable_overlap(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Check if any variables appear in multiple groups (potential conflict)."""
    await verify_project_access(project_id, current_user, db)

    result = await db.execute(select(VariableGroup).where(VariableGroup.project_id == project_id))
    groups = result.scalars().all()

    # Track variable -> groups mapping
    variable_groups: dict[str, list[str]] = {}
    for group in groups:
        for var in group.variables:
            if var not in variable_groups:
                variable_groups[var] = []
            variable_groups[var].append(group.name)

    # Find overlapping variables
    overlaps = {var: group_names for var, group_names in variable_groups.items() if len(group_names) > 1}

    return {
        "has_overlaps": len(overlaps) > 0,
        "overlaps": overlaps,
    }
