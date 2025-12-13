"""ModelConfig repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ModelConfig
from app.models.model_config import ModelStatus
from app.repositories.base import BaseRepository
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate


class ModelConfigRepository(BaseRepository[ModelConfig]):
    """Repository for ModelConfig operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ModelConfig)

    async def get_with_result(self, id: UUID) -> ModelConfig | None:
        """Get model config with its result."""
        result = await self.db.execute(
            select(ModelConfig).options(selectinload(ModelConfig.result)).where(ModelConfig.id == id)
        )
        return result.scalar_one_or_none()

    async def get_project_models(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelConfig]:
        """Get all model configs for a project."""
        result = await self.db.execute(
            select(ModelConfig)
            .where(ModelConfig.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(ModelConfig.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_project_models(self, project_id: UUID) -> int:
        """Count model configs for a project."""
        result = await self.db.execute(
            select(func.count()).select_from(ModelConfig).where(ModelConfig.project_id == project_id)
        )
        return result.scalar_one()

    async def create_model_config(
        self,
        config_in: ModelConfigCreate,
        project_id: UUID,
    ) -> ModelConfig:
        """Create a new model config."""
        db_obj = ModelConfig(
            name=config_in.name,
            project_id=project_id,
            dataset_id=config_in.dataset_id,
            model_type=config_in.model_type.value,
            target_variable=config_in.target_variable,
            date_column=config_in.date_column,
            features=[f.model_dump() for f in config_in.features],
            granularity=config_in.granularity.model_dump() if config_in.granularity else None,
            constraints=config_in.constraints,
            priors=config_in.priors,
            hyperparameters=config_in.hyperparameters.model_dump() if config_in.hyperparameters else None,
            seasonality=config_in.seasonality.model_dump() if config_in.seasonality else None,
            status=ModelStatus.PENDING.value,
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_model_config(
        self,
        model_config: ModelConfig,
        config_in: ModelConfigUpdate,
    ) -> ModelConfig:
        """Update a model config with partial data."""
        update_data = config_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "features" and value is not None:
                setattr(
                    model_config,
                    field,
                    [f.model_dump() if hasattr(f, "model_dump") else f for f in value],
                )
            elif field == "granularity" and value is not None:
                setattr(
                    model_config,
                    field,
                    value.model_dump() if hasattr(value, "model_dump") else value,
                )
            elif field == "hyperparameters" and value is not None:
                setattr(
                    model_config,
                    field,
                    value.model_dump() if hasattr(value, "model_dump") else value,
                )
            elif field == "seasonality" and value is not None:
                setattr(
                    model_config,
                    field,
                    value.model_dump() if hasattr(value, "model_dump") else value,
                )
            elif field == "model_type" and value is not None:
                setattr(
                    model_config,
                    field,
                    value.value if hasattr(value, "value") else value,
                )
            else:
                setattr(model_config, field, value)

        await self.db.commit()
        await self.db.refresh(model_config)
        return model_config

    async def update_status(
        self,
        model_config: ModelConfig,
        status: ModelStatus,
        task_id: str | None = None,
        error_message: str | None = None,
    ) -> ModelConfig:
        """Update model config status."""
        model_config.status = status.value
        if task_id:
            model_config.task_id = task_id
        if error_message:
            model_config.error_message = error_message

        await self.db.commit()
        await self.db.refresh(model_config)
        return model_config
