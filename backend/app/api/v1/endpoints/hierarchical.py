"""Hierarchical model endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import (
    Dataset,
    HierarchicalModelConfig,
    ModelConfig,
    Project,
    SubModelStatus,
)
from app.schemas.hierarchical import (
    DimensionAnalysis,
    DimensionCombination,
    HierarchicalModelCreate,
    HierarchicalModelList,
    HierarchicalModelRead,
    HierarchicalResultsSummary,
    HierarchicalTrainingStatus,
    SubModelRead,
    TrainingProgress,
)

router = APIRouter(prefix="/projects/{project_id}/hierarchical-models", tags=["Hierarchical Models"])


async def get_project_or_404(
    project_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Project:
    """Get project or raise 404."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[HierarchicalModelList])
async def list_hierarchical_models(
    project_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """List all hierarchical models in a project."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig)
        .where(HierarchicalModelConfig.project_id == project_id)
        .options(selectinload(HierarchicalModelConfig.sub_models))
        .order_by(HierarchicalModelConfig.created_at.desc())
    )
    configs = result.scalars().all()

    return [
        HierarchicalModelList(
            id=c.id,
            name=c.name,
            granularity_type=c.granularity_type,
            model_type=c.model_type,
            status=c.status,
            sub_model_count=len(c.sub_models),
            completed_count=sum(1 for s in c.sub_models if s.status == SubModelStatus.COMPLETED.value),
            created_at=c.created_at,
        )
        for c in configs
    ]


@router.post("", response_model=HierarchicalModelRead, status_code=status.HTTP_201_CREATED)
async def create_hierarchical_model(
    project_id: UUID,
    data: HierarchicalModelCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create a new hierarchical model configuration."""
    await get_project_or_404(project_id, db, current_user)

    # Validate dataset exists
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == data.dataset_id,
            Dataset.project_id == project_id,
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Validate parent model if specified
    if data.parent_model_id:
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.id == data.parent_model_id,
                ModelConfig.project_id == project_id,
            )
        )
        parent_model = result.scalar_one_or_none()
        if not parent_model:
            raise HTTPException(status_code=404, detail="Parent model not found")

    # Create hierarchical config
    config = HierarchicalModelConfig(
        project_id=project_id,
        name=data.name,
        parent_model_id=data.parent_model_id,
        dataset_id=data.dataset_id,
        dimension_columns=data.dimension_columns,
        granularity_type=data.granularity_type,
        model_type=data.model_type,
        target_variable=data.target_variable,
        date_column=data.date_column,
        features=data.features,
        inherit_constraints=data.inherit_constraints,
        constraint_relaxation=data.constraint_relaxation,
        inherit_priors=data.inherit_priors,
        prior_weight=data.prior_weight,
        min_observations=data.min_observations,
        status="pending",
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config


@router.get("/{config_id}", response_model=HierarchicalModelRead)
async def get_hierarchical_model(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a hierarchical model configuration."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig)
        .where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
        .options(selectinload(HierarchicalModelConfig.sub_models))
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hierarchical_model(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a hierarchical model configuration."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig).where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    await db.delete(config)
    await db.commit()


@router.get("/{config_id}/dimensions", response_model=DimensionAnalysis)
async def analyze_dimensions(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Analyze dimension combinations in the dataset."""
    import pandas as pd

    from app.services.file_storage import FileStorage

    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig)
        .where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
        .options(selectinload(HierarchicalModelConfig.dataset))
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    # Load dataset
    storage = FileStorage()
    df = pd.read_csv(storage.get_path(config.dataset.file_path))

    # Validate dimension columns exist
    for col in config.dimension_columns:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Dimension column '{col}' not found in dataset")

    # Get unique combinations
    if len(config.dimension_columns) == 1:
        col = config.dimension_columns[0]
        combinations = [
            DimensionCombination(
                values={col: str(v)},
                observation_count=int((df[col] == v).sum()),
            )
            for v in df[col].unique()
        ]
    else:
        grouped = df.groupby(config.dimension_columns).size().reset_index(name="count")
        combinations = [
            DimensionCombination(
                values={col: str(row[col]) for col in config.dimension_columns},
                observation_count=int(row["count"]),
            )
            for _, row in grouped.iterrows()
        ]

    return DimensionAnalysis(
        dimension_columns=config.dimension_columns,
        combinations=combinations,
        total_combinations=len(combinations),
    )


@router.post("/{config_id}/train", status_code=status.HTTP_202_ACCEPTED)
async def start_training(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Start training all sub-models."""
    from app.workers.tasks import train_hierarchical_model

    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig).where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    if config.status == "training":
        raise HTTPException(status_code=400, detail="Training already in progress")

    # Start Celery task
    task = train_hierarchical_model.delay(str(config_id))

    # Update status
    config.status = "training"
    config.task_id = task.id
    await db.commit()

    return {
        "status": "started",
        "task_id": task.id,
        "config_id": str(config_id),
    }


@router.get("/{config_id}/status", response_model=HierarchicalTrainingStatus)
async def get_training_status(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get training status for a hierarchical model."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig)
        .where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
        .options(selectinload(HierarchicalModelConfig.sub_models))
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    # Calculate progress
    total = len(config.sub_models)
    completed = sum(1 for s in config.sub_models if s.status == SubModelStatus.COMPLETED.value)
    failed = sum(1 for s in config.sub_models if s.status == SubModelStatus.FAILED.value)
    in_progress = sum(1 for s in config.sub_models if s.status == SubModelStatus.TRAINING.value)
    pending = sum(1 for s in config.sub_models if s.status == SubModelStatus.PENDING.value)

    return HierarchicalTrainingStatus(
        status=config.status,
        progress=TrainingProgress(
            total=total,
            completed=completed,
            failed=failed,
            in_progress=in_progress,
            pending=pending,
        ),
        sub_models=[SubModelRead.model_validate(s) for s in config.sub_models],
    )


@router.post("/{config_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_training(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Cancel training for a hierarchical model."""
    from app.workers.celery_app import celery_app

    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig).where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    if config.task_id:
        # Revoke the task
        celery_app.control.revoke(config.task_id, terminate=True)

    config.status = "cancelled"
    await db.commit()

    return {"status": "cancelled"}


@router.get("/{config_id}/results", response_model=HierarchicalResultsSummary)
async def get_results_summary(
    project_id: UUID,
    config_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get summary of hierarchical model results."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(HierarchicalModelConfig)
        .where(
            HierarchicalModelConfig.id == config_id,
            HierarchicalModelConfig.project_id == project_id,
        )
        .options(
            selectinload(HierarchicalModelConfig.sub_models),
            selectinload(HierarchicalModelConfig.parent_model),
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Hierarchical model not found")

    completed_subs = [s for s in config.sub_models if s.status == SubModelStatus.COMPLETED.value]
    r_squared_values = [s.r_squared for s in completed_subs if s.r_squared is not None]

    # Build coefficient comparisons (simplified - would need to load full results)
    coefficient_comparisons = []

    return HierarchicalResultsSummary(
        id=config.id,
        name=config.name,
        total_sub_models=len(config.sub_models),
        completed_sub_models=len(completed_subs),
        avg_r_squared=sum(r_squared_values) / len(r_squared_values) if r_squared_values else None,
        min_r_squared=min(r_squared_values) if r_squared_values else None,
        max_r_squared=max(r_squared_values) if r_squared_values else None,
        coefficient_comparisons=coefficient_comparisons,
    )
