"""Dataset endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.repositories.dataset import DatasetRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PaginatedResponse
from app.schemas.dataset import DatasetCreate, DatasetRead, DatasetVersion
from app.workers.tasks import process_dataset_file

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["Datasets"])


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


@router.get("", response_model=PaginatedResponse)
async def list_datasets(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all datasets for a project."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    skip = (page - 1) * limit

    datasets = await dataset_repo.get_project_datasets(
        project_id=project_id,
        skip=skip,
        limit=limit,
    )
    total = await dataset_repo.count_project_datasets(project_id)

    items = [DatasetRead.model_validate(d) for d in datasets]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    project_id: UUID,
    dataset_in: DatasetCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> DatasetRead:
    """Create a new dataset (metadata only, upload separately)."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.create_dataset(dataset_in, project_id)
    return DatasetRead.model_validate(dataset)


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DatasetRead:
    """Get a specific dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    return DatasetRead.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    await dataset_repo.delete(dataset_id)


@router.post("/{dataset_id}/reprocess", response_model=DatasetRead)
async def reprocess_dataset(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DatasetRead:
    """Re-trigger processing for a stuck dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    if not dataset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset has no file to process",
        )

    # Update status to processing
    from app.models.dataset import DatasetStatus

    dataset.status = DatasetStatus.PROCESSING.value
    await db.commit()
    await db.refresh(dataset)

    # Trigger async processing
    process_dataset_file.delay(
        dataset_id=str(dataset.id),
        file_path=dataset.file_path,
    )

    return DatasetRead.model_validate(dataset)


@router.get("/{dataset_id}/versions", response_model=list[DatasetVersion])
async def list_dataset_versions(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[DatasetVersion]:
    """List all versions of a dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Get all versions (including parent chain)
    versions = await dataset_repo.get_version_history(dataset_id)

    return [
        DatasetVersion(
            id=v.id,
            version=v.version,
            created_at=v.created_at.isoformat(),
            status=v.status,
            row_count=v.row_count,
            is_latest=v.is_latest,
        )
        for v in versions
    ]


@router.post(
    "/{dataset_id}/versions",
    response_model=DatasetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset_version(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DatasetRead:
    """
    Create a new version of an existing dataset.

    This creates a copy of the dataset metadata that can be updated
    with new data while preserving the original version.
    """
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Create new version
    new_version = await dataset_repo.create_version(dataset)

    return DatasetRead.model_validate(new_version)


@router.post("/{dataset_id}/revert/{version}", response_model=DatasetRead)
async def revert_to_version(
    project_id: UUID,
    dataset_id: UUID,
    version: int,
    current_user: CurrentUser,
    db: DbSession,
) -> DatasetRead:
    """Revert to a specific version of a dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Find the version to revert to
    target_version = await dataset_repo.get_version(dataset_id, version)

    if target_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found",
        )

    # Set as latest
    reverted = await dataset_repo.set_as_latest(target_version)

    return DatasetRead.model_validate(reverted)
