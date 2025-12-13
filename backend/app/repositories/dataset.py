"""Dataset repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset
from app.models.dataset import DatasetStatus
from app.repositories.base import BaseRepository
from app.schemas.dataset import DatasetCreate


class DatasetRepository(BaseRepository[Dataset]):
    """Repository for Dataset operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Dataset)

    async def get_project_datasets(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Dataset]:
        """Get all datasets for a project."""
        result = await self.db.execute(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(Dataset.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_project_datasets(self, project_id: UUID) -> int:
        """Count datasets for a project."""
        result = await self.db.execute(
            select(func.count()).select_from(Dataset).where(Dataset.project_id == project_id)
        )
        return result.scalar_one()

    async def create_dataset(
        self,
        dataset_in: DatasetCreate,
        project_id: UUID,
    ) -> Dataset:
        """Create a new dataset."""
        db_obj = Dataset(
            name=dataset_in.name,
            description=dataset_in.description,
            project_id=project_id,
            status=DatasetStatus.PENDING.value,
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_status(
        self,
        dataset: Dataset,
        status: DatasetStatus,
        error_message: str | None = None,
    ) -> Dataset:
        """Update dataset status."""
        dataset.status = status.value
        if error_message:
            dataset.error_message = error_message

        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def update_metadata(
        self,
        dataset: Dataset,
        file_name: str,
        file_path: str,
        file_size: int,
        row_count: int,
        column_count: int,
        columns_metadata: dict,
    ) -> Dataset:
        """Update dataset file metadata after processing."""
        dataset.file_name = file_name
        dataset.file_path = file_path
        dataset.file_size = file_size
        dataset.row_count = row_count
        dataset.column_count = column_count
        dataset.columns_metadata = columns_metadata
        dataset.status = DatasetStatus.READY.value

        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get_version_history(self, dataset_id: UUID) -> list[Dataset]:
        """
        Get version history for a dataset.

        Returns all versions related to this dataset (parent chain and children).
        """
        dataset = await self.get_by_id(dataset_id)
        if not dataset:
            return []

        # Get all datasets with the same name in the project, ordered by version
        result = await self.db.execute(
            select(Dataset)
            .where(
                Dataset.project_id == dataset.project_id,
                Dataset.name == dataset.name,
            )
            .order_by(Dataset.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, dataset_id: UUID, version: int) -> Dataset | None:
        """Get a specific version of a dataset."""
        dataset = await self.get_by_id(dataset_id)
        if not dataset:
            return None

        result = await self.db.execute(
            select(Dataset).where(
                Dataset.project_id == dataset.project_id,
                Dataset.name == dataset.name,
                Dataset.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def create_version(self, dataset: Dataset) -> Dataset:
        """
        Create a new version of an existing dataset.

        The new version inherits metadata from the parent but gets a new ID.
        """
        # Mark current as not latest
        dataset.is_latest = False

        # Get the max version for this dataset name
        result = await self.db.execute(
            select(func.max(Dataset.version)).where(
                Dataset.project_id == dataset.project_id,
                Dataset.name == dataset.name,
            )
        )
        max_version = result.scalar() or 0

        # Create new version
        new_dataset = Dataset(
            name=dataset.name,
            description=dataset.description,
            project_id=dataset.project_id,
            status=DatasetStatus.PENDING.value,
            version=max_version + 1,
            parent_id=dataset.id,
            is_latest=True,
        )

        self.db.add(new_dataset)
        await self.db.commit()
        await self.db.refresh(new_dataset)
        return new_dataset

    async def set_as_latest(self, dataset: Dataset) -> Dataset:
        """Set a dataset version as the latest."""
        # First, unset is_latest for all versions of this dataset
        all_versions = await self.get_version_history(dataset.id)
        for v in all_versions:
            if v.is_latest:
                v.is_latest = False

        # Set the target as latest
        dataset.is_latest = True

        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset
