"""Model training endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_project_access
from app.core.deps import DbSession
from app.models import Project
from app.models.dataset import DatasetStatus
from app.models.model_config import ModelStatus
from app.repositories.dataset import DatasetRepository
from app.repositories.model_config import ModelConfigRepository
from app.schemas.model_config import ModelConfigRead
from app.schemas.responses import ModelTrainingStatus
from app.workers.tasks import train_mmm_model

router = APIRouter(prefix="/projects/{project_id}/models", tags=["Training"])


@router.post("/{model_id}/train", response_model=ModelConfigRead)
async def start_training(
    project_id: UUID,
    model_id: UUID,
    db: DbSession,
    project: Project = Depends(require_project_access()),
) -> ModelConfigRead:
    """
    Start model training.

    The model will be trained asynchronously using Celery.
    Use the /status endpoint to check training progress.
    """
    # Get model config
    model_repo = ModelConfigRepository(db)
    model_config = await model_repo.get_by_id(model_id)

    if model_config is None or model_config.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model configuration not found",
        )

    # Check if already training
    if model_config.status == ModelStatus.TRAINING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is already training",
        )

    # Get dataset
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(model_config.dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset not found",
        )

    if dataset.status != DatasetStatus.READY.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset is not ready. Status: {dataset.status}",
        )

    if not dataset.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset has no uploaded file",
        )

    # Build training config
    training_config = {
        "model_type": model_config.model_type,
        "features": model_config.features or [],
        "target_variable": model_config.target_variable,
        "date_column": model_config.date_column,
        "constraints": model_config.constraints,
        "priors": model_config.priors,
        "hyperparameters": model_config.hyperparameters or {},
        "seasonality": model_config.seasonality,
        "auto_fit_transformations": True,
    }

    # Start Celery task
    task = train_mmm_model.delay(
        model_config_id=str(model_id),
        dataset_path=dataset.file_path,
        config=training_config,
    )

    # Update model status
    model_config.status = ModelStatus.TRAINING.value
    model_config.task_id = task.id
    model_config.error_message = None

    await db.commit()
    await db.refresh(model_config)

    return ModelConfigRead.model_validate(model_config)


@router.get("/{model_id}/status", response_model=ModelTrainingStatus)
async def get_training_status(
    project_id: UUID,
    model_id: UUID,
    db: DbSession,
    project: Project = Depends(require_project_access()),
) -> ModelTrainingStatus:
    """Get model training status and progress."""

    model_repo = ModelConfigRepository(db)
    model_config = await model_repo.get_by_id(model_id)

    if model_config is None or model_config.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model configuration not found",
        )

    # Default response
    response = ModelTrainingStatus(
        model_id=model_id,
        status=model_config.status,
        progress=0,
        current_step=None,
    )

    if model_config.status == ModelStatus.COMPLETED.value:
        response.progress = 100
        response.current_step = "Training complete"
        return response

    if model_config.status == ModelStatus.FAILED.value:
        response.current_step = model_config.error_message or "Training failed"
        return response

    if model_config.status == ModelStatus.PENDING.value:
        response.current_step = "Waiting to start"
        return response

    # Check Celery task status
    if model_config.task_id:
        from celery.result import AsyncResult

        from app.workers.celery_app import celery_app

        result = AsyncResult(model_config.task_id, app=celery_app)

        if result.state == "PROGRESS":
            meta = result.info or {}
            response.progress = meta.get("progress", 0)
            response.current_step = meta.get("status", "Training in progress")
        elif result.state == "SUCCESS":
            response.progress = 100
            response.current_step = "Training complete"
            response.status = ModelStatus.COMPLETED.value
            # Update DB status if changed
            if model_config.status != ModelStatus.COMPLETED.value:
                model_config.status = ModelStatus.COMPLETED.value
                await db.commit()
        elif result.state == "FAILURE":
            response.current_step = str(result.result) if result.result else "Training failed"
            response.status = ModelStatus.FAILED.value
            # Update DB status if changed
            if model_config.status != ModelStatus.FAILED.value:
                model_config.status = ModelStatus.FAILED.value
                model_config.error_message = str(result.result) if result.result else "Training failed"
                await db.commit()
        elif result.state == "PENDING":
            # Task not yet started or result expired
            response.current_step = "Task pending or result expired"
        else:
            response.current_step = f"Status: {result.state}"

    return response


@router.post("/{model_id}/cancel")
async def cancel_training(
    project_id: UUID,
    model_id: UUID,
    db: DbSession,
    project: Project = Depends(require_project_access()),
) -> dict:
    """Cancel an ongoing training task."""

    model_repo = ModelConfigRepository(db)
    model_config = await model_repo.get_by_id(model_id)

    if model_config is None or model_config.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model configuration not found",
        )

    if model_config.status != ModelStatus.TRAINING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is not currently training",
        )

    # Revoke Celery task
    if model_config.task_id:
        from app.workers.celery_app import celery_app

        celery_app.control.revoke(model_config.task_id, terminate=True)

    # Update status
    model_config.status = ModelStatus.FAILED.value
    model_config.error_message = "Training cancelled by user"

    await db.commit()

    return {"message": "Training cancelled", "model_id": str(model_id)}


@router.get("/{model_id}/results")
async def get_training_results(
    project_id: UUID,
    model_id: UUID,
    db: DbSession,
    project: Project = Depends(require_project_access()),
) -> dict:
    """
    Get detailed training results.

    Returns full model results including coefficients, contributions,
    response curves, and diagnostics.
    """
    model_repo = ModelConfigRepository(db)
    model_config = await model_repo.get_with_result(model_id)

    if model_config is None or model_config.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model configuration not found",
        )

    if model_config.status != ModelStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model training not complete. Status: {model_config.status}",
        )

    # Get result from Celery if available
    if model_config.task_id:
        from celery.result import AsyncResult

        from app.workers.celery_app import celery_app

        result = AsyncResult(model_config.task_id, app=celery_app)

        if result.successful():
            celery_result = result.result
            # Validate that result is not None (can happen if Redis TTL expired)
            if celery_result is not None and isinstance(celery_result, dict):
                return celery_result

    # Fallback to stored result
    if model_config.result:
        return {
            "model_id": str(model_id),
            "status": "completed",
            "metrics": model_config.result.metrics,
            "coefficients": model_config.result.coefficients,
            "contributions": model_config.result.contributions,
            "decomposition": model_config.result.decomposition,
            "response_curves": model_config.result.response_curves,
            "diagnostics": model_config.result.diagnostics,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Training results not found",
    )
