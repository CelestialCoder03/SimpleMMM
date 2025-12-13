"""Project endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.repositories.project import ProjectRepository
from app.schemas.base import PaginatedResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectSettings,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all projects for current user."""
    project_repo = ProjectRepository(db)
    skip = (page - 1) * limit

    projects = await project_repo.get_user_projects(
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    total = await project_repo.count_user_projects(current_user.id)

    items = [ProjectRead.model_validate(p) for p in projects]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectRead:
    """Create a new project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.create_project(project_in, current_user.id)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectRead:
    """Get a specific project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id_with_counts(project_id)

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

    response = ProjectRead.model_validate(project)
    response.dataset_count = len(project.datasets)
    response.model_count = len(project.model_configs)
    return response


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectRead:
    """Update a project."""
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
            detail="Not authorized to modify this project",
        )

    updated = await project_repo.update_project(project, project_in)
    return ProjectRead.model_validate(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a project."""
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
            detail="Not authorized to delete this project",
        )

    await project_repo.delete(project_id)


@router.get("/{project_id}/settings", response_model=ProjectSettings)
async def get_project_settings(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectSettings:
    """Get project settings."""
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

    return ProjectSettings.model_validate(project.settings or {})


@router.patch("/{project_id}/settings", response_model=ProjectSettings)
async def update_project_settings(
    project_id: UUID,
    settings_in: ProjectSettings,
    current_user: CurrentUser,
    db: DbSession,
) -> ProjectSettings:
    """Update project settings."""
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
            detail="Not authorized to modify this project",
        )

    # Merge new settings with existing
    current_settings = project.settings or {}
    new_settings = settings_in.model_dump(exclude_unset=True)
    merged_settings = {**current_settings, **new_settings}

    project.settings = merged_settings
    await db.commit()
    await db.refresh(project)

    return ProjectSettings.model_validate(project.settings)
