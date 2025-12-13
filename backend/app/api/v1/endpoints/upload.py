"""File upload endpoints."""

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.models.dataset import DatasetStatus
from app.repositories.dataset import DatasetRepository
from app.repositories.project import ProjectRepository
from app.schemas.dataset import DatasetRead
from app.services.file_storage import FileStorageService
from app.workers.tasks import process_dataset_file

router = APIRouter(prefix="/projects/{project_id}", tags=["Upload"])


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


@router.post("/upload/datasets", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def upload_and_create_dataset(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> DatasetRead:
    """
    Upload a file and create a dataset in one step.

    This endpoint creates the dataset record and uploads the file together,
    matching the frontend's expected API contract.
    """
    await verify_project_access(project_id, current_user, db)

    storage = FileStorageService()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not storage.validate_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read file content
    content = await file.read()

    if not storage.validate_size(len(content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    # Save file first
    file_path, file_size = await storage.save_file(
        project_id=project_id,
        filename=file.filename,
        content=content,
    )

    # Create dataset record
    from app.schemas.dataset import DatasetCreate

    dataset_name = name or file.filename.rsplit(".", 1)[0]
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.create_dataset(
        DatasetCreate(name=dataset_name),
        project_id,
    )

    # Update with file info
    dataset.file_name = file.filename
    dataset.file_path = file_path
    dataset.file_size = file_size
    dataset.status = DatasetStatus.PROCESSING.value

    await db.commit()
    await db.refresh(dataset)

    # Trigger async processing
    process_dataset_file.delay(
        dataset_id=str(dataset.id),
        file_path=file_path,
    )

    return DatasetRead.model_validate(dataset)


@router.post("/datasets/{dataset_id}/upload", response_model=DatasetRead)
async def upload_dataset_file(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> DatasetRead:
    """Upload a file to an existing dataset and trigger processing."""
    await verify_project_access(project_id, current_user, db)

    # Validate file
    storage = FileStorageService()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not storage.validate_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Get dataset
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Read file content
    content = await file.read()

    if not storage.validate_size(len(content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    # Save file
    file_path, file_size = await storage.save_file(
        project_id=project_id,
        filename=file.filename,
        content=content,
    )

    # Update dataset with file info
    dataset.file_name = file.filename
    dataset.file_path = file_path
    dataset.file_size = file_size
    dataset.status = DatasetStatus.PROCESSING.value

    await db.commit()
    await db.refresh(dataset)

    # Trigger async processing
    task = process_dataset_file.delay(
        dataset_id=str(dataset_id),
        file_path=file_path,
    )

    # Store task ID
    dataset.task_id = task.id if hasattr(dataset, "task_id") else None
    await db.commit()

    return DatasetRead.model_validate(dataset)


@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = 100,
) -> dict:
    """Get preview of dataset contents."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    if dataset.status != DatasetStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset not ready. Status: {dataset.status}",
        )

    if not dataset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file uploaded for this dataset",
        )

    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()
    df = processor.read_file(dataset.file_path)
    preview = processor.get_preview(df, rows=min(limit, 500))

    return {
        "dataset_id": str(dataset_id),
        **preview,
    }


@router.get("/datasets/{dataset_id}/stats")
async def get_dataset_stats(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get detailed statistics for a dataset."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    if dataset.status != DatasetStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset not ready. Status: {dataset.status}",
        )

    # Return cached metadata
    return {
        "dataset_id": str(dataset_id),
        "name": dataset.name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "file_name": dataset.file_name,
        "file_size": dataset.file_size,
        "columns": dataset.columns_metadata,
    }


@router.get("/datasets/{dataset_id}/correlation")
async def get_correlation_matrix(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get correlation matrix for numeric columns."""
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    if dataset.status != DatasetStatus.READY.value or not dataset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset not ready or no file uploaded",
        )

    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()
    df = processor.read_file(dataset.file_path)
    correlation = processor.compute_correlation_matrix(df)

    return {
        "dataset_id": str(dataset_id),
        "correlation_matrix": correlation,
    }


@router.post("/datasets/{dataset_id}/update", response_model=DatasetRead)
async def update_dataset_file(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    mode: str = Form(default="new_version"),  # "new_version" or "replace"
    preserve_metadata: bool = Form(default=True),
) -> DatasetRead:
    """
    Update a dataset with a new file.

    Modes:
    - new_version: Create a new version of the dataset (default, safer)
    - replace: Replace the existing file in place (preserves dataset ID)

    If preserve_metadata is True, variable metadata (types, groups) will be
    preserved for columns that exist in both old and new files.
    """
    await verify_project_access(project_id, current_user, db)

    storage = FileStorageService()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not storage.validate_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Get existing dataset
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Read file content
    content = await file.read()

    if not storage.validate_size(len(content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    # Store old metadata for comparison
    if dataset.columns_metadata and preserve_metadata:
        {col.get("name") for col in dataset.columns_metadata if col.get("name")}

    # Save new file
    file_path, file_size = await storage.save_file(
        project_id=project_id,
        filename=file.filename,
        content=content,
    )

    if mode == "new_version":
        # Create a new version
        new_dataset = await dataset_repo.create_version(dataset)
        new_dataset.file_name = file.filename
        new_dataset.file_path = file_path
        new_dataset.file_size = file_size
        new_dataset.status = DatasetStatus.PROCESSING.value
        await db.commit()
        await db.refresh(new_dataset)

        # Trigger async processing
        process_dataset_file.delay(
            dataset_id=str(new_dataset.id),
            file_path=file_path,
        )

        return DatasetRead.model_validate(new_dataset)
    else:
        # Replace in place
        dataset.file_name = file.filename
        dataset.file_path = file_path
        dataset.file_size = file_size
        dataset.status = DatasetStatus.PROCESSING.value
        await db.commit()
        await db.refresh(dataset)

        # Trigger async processing
        process_dataset_file.delay(
            dataset_id=str(dataset_id),
            file_path=file_path,
        )

        return DatasetRead.model_validate(dataset)


@router.get("/datasets/{dataset_id}/column-diff")
async def get_column_diff(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    compare_to: UUID | None = None,
) -> dict:
    """
    Compare columns between two datasets.

    If compare_to is provided, compares with that dataset.
    Otherwise, compares with the parent version (if exists).

    Returns added, removed, and unchanged columns.
    """
    await verify_project_access(project_id, current_user, db)

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    if dataset.status != DatasetStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset not ready. Status: {dataset.status}",
        )

    # Get current columns
    current_columns = set()
    if dataset.columns_metadata:
        current_columns = {col.get("name") for col in dataset.columns_metadata if col.get("name")}

    # Get comparison dataset
    compare_dataset = None
    if compare_to:
        compare_dataset = await dataset_repo.get_by_id(compare_to)
    elif dataset.parent_id:
        compare_dataset = await dataset_repo.get_by_id(dataset.parent_id)

    if compare_dataset is None:
        return {
            "dataset_id": str(dataset_id),
            "compare_to": None,
            "added_columns": list(current_columns),
            "removed_columns": [],
            "unchanged_columns": [],
        }

    # Get comparison columns
    compare_columns = set()
    if compare_dataset.columns_metadata:
        compare_columns = {col.get("name") for col in compare_dataset.columns_metadata if col.get("name")}

    added = current_columns - compare_columns
    removed = compare_columns - current_columns
    unchanged = current_columns & compare_columns

    return {
        "dataset_id": str(dataset_id),
        "compare_to": str(compare_dataset.id),
        "added_columns": sorted(list(added)),
        "removed_columns": sorted(list(removed)),
        "unchanged_columns": sorted(list(unchanged)),
    }
