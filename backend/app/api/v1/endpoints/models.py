"""Model configuration endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.repositories.dataset import DatasetRepository
from app.repositories.model_config import ModelConfigRepository
from app.repositories.project import ProjectRepository
from app.schemas.base import PaginatedResponse
from app.schemas.constraint_validation import (
    ConstraintConflictResponse,
    ValidateConstraintsRequest,
    ValidateConstraintsResponse,
)
from app.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigRead,
    ModelConfigUpdate,
)
from app.services.modeling.conflict_detector import validate_constraints

router = APIRouter(prefix="/projects/{project_id}/models", tags=["Models"])


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
async def list_models(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all model configs for a project."""
    await verify_project_access(project_id, current_user, db)

    model_repo = ModelConfigRepository(db)
    skip = (page - 1) * limit

    models = await model_repo.get_project_models(
        project_id=project_id,
        skip=skip,
        limit=limit,
    )
    total = await model_repo.count_project_models(project_id)

    items = [ModelConfigRead.model_validate(m) for m in models]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ModelConfigRead, status_code=status.HTTP_201_CREATED)
async def create_model(
    project_id: UUID,
    model_in: ModelConfigCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ModelConfigRead:
    """Create a new model configuration."""
    await verify_project_access(project_id, current_user, db)

    # Verify dataset exists and belongs to project
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(model_in.dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset not found or doesn't belong to this project",
        )

    model_repo = ModelConfigRepository(db)
    model = await model_repo.create_model_config(model_in, project_id)
    return ModelConfigRead.model_validate(model)


@router.get("/{model_id}", response_model=ModelConfigRead)
async def get_model(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ModelConfigRead:
    """Get a specific model configuration."""
    await verify_project_access(project_id, current_user, db)

    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_with_result(model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    return ModelConfigRead.model_validate(model)


@router.put("/{model_id}", response_model=ModelConfigRead)
async def update_model(
    project_id: UUID,
    model_id: UUID,
    model_in: ModelConfigUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ModelConfigRead:
    """Update a model configuration. Only allowed when status is 'pending'."""
    await verify_project_access(project_id, current_user, db)

    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    if model.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update model with status '{model.status}'. Only 'pending' models can be updated.",
        )

    updated = await model_repo.update_model_config(model, model_in)
    return ModelConfigRead.model_validate(updated)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a model configuration."""
    await verify_project_access(project_id, current_user, db)

    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    await model_repo.delete(model_id)


@router.post("/validate-constraints", response_model=ValidateConstraintsResponse)
async def validate_model_constraints(
    project_id: UUID,
    request: ValidateConstraintsRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ValidateConstraintsResponse:
    """
    Validate a set of constraints and detect any conflicts.

    Returns validation results including:
    - Whether constraints are valid (no blocking errors)
    - List of conflicts (errors, warnings, info)
    - Suggestions for resolving conflicts
    """
    await verify_project_access(project_id, current_user, db)

    result = validate_constraints(
        coefficient_constraints=request.coefficient_constraints,
        contribution_constraints=request.contribution_constraints,
        group_constraints=request.group_constraints,
    )

    return ValidateConstraintsResponse(
        valid=result.valid,
        conflicts=[
            ConstraintConflictResponse(
                type=c.type,
                code=c.code,
                message=c.message,
                affected_variables=c.affected_variables,
                affected_groups=c.affected_groups,
                suggestion=c.suggestion,
            )
            for c in result.conflicts
        ],
        warnings_count=result.warnings_count,
        errors_count=result.errors_count,
    )


@router.post(
    "/{model_id}/apply-to-dataset",
    response_model=ModelConfigRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_model_config_to_dataset(
    project_id: UUID,
    model_id: UUID,
    target_dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    new_name: str | None = None,
) -> ModelConfigRead:
    """
    Apply an existing model configuration to a different dataset.

    This creates a new model config with the same settings (features, constraints,
    priors, hyperparameters) but linked to a different dataset.

    Features that don't exist in the target dataset will be excluded with a warning.

    Args:
        model_id: Source model to copy configuration from
        target_dataset_id: Target dataset to apply configuration to
        new_name: Optional name for the new model (defaults to "{original_name} (copy)")

    Returns:
        The newly created model configuration with warnings about excluded features
    """
    await verify_project_access(project_id, current_user, db)

    # Get source model
    model_repo = ModelConfigRepository(db)
    source_model = await model_repo.get_by_id(model_id)

    if source_model is None or source_model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source model not found",
        )

    # Verify target dataset exists and belongs to project
    dataset_repo = DatasetRepository(db)
    target_dataset = await dataset_repo.get_by_id(target_dataset_id)

    if target_dataset is None or target_dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target dataset not found or doesn't belong to this project",
        )

    if target_dataset.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target dataset not ready. Status: {target_dataset.status}",
        )

    # Get target dataset columns
    target_columns = set()
    if target_dataset.columns_metadata:
        target_columns = {col.get("name") for col in target_dataset.columns_metadata if col.get("name")}

    # Filter features to only include those that exist in target dataset
    excluded_features = []
    valid_features = []

    if source_model.features:
        for feature in source_model.features:
            feature_name = feature.get("column") if isinstance(feature, dict) else getattr(feature, "column", None)
            if feature_name and feature_name in target_columns:
                valid_features.append(feature)
            else:
                excluded_features.append(feature_name)

    # Check target variable exists
    if source_model.target_variable not in target_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target variable '{source_model.target_variable}' not found in target dataset",
        )

    # Check date column exists
    if source_model.date_column not in target_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date column '{source_model.date_column}' not found in target dataset",
        )

    # Filter constraints to only include valid features
    valid_feature_names = {
        f.get("column") if isinstance(f, dict) else getattr(f, "column", None) for f in valid_features
    }
    filtered_constraints = None

    if source_model.constraints:
        filtered_constraints = dict(source_model.constraints)

        # Filter coefficient constraints
        if "coefficients" in filtered_constraints:
            filtered_constraints["coefficients"] = [
                c for c in filtered_constraints["coefficients"] if c.get("variable") in valid_feature_names
            ]

        # Filter contribution constraints
        if "contributions" in filtered_constraints:
            filtered_constraints["contributions"] = [
                c for c in filtered_constraints["contributions"] if c.get("variable") in valid_feature_names
            ]

    # Filter priors similarly
    filtered_priors = None
    if source_model.priors:
        filtered_priors = {k: v for k, v in source_model.priors.items() if k in valid_feature_names or k == "intercept"}

    # Create new model config
    model_name = new_name or f"{source_model.name} (copy)"

    new_model_data = ModelConfigCreate(
        name=model_name,
        dataset_id=target_dataset_id,
        model_type=source_model.model_type,
        target_variable=source_model.target_variable,
        date_column=source_model.date_column,
        features=valid_features,
        granularity=source_model.granularity,
        constraints=filtered_constraints,
        priors=filtered_priors,
        hyperparameters=source_model.hyperparameters,
    )

    new_model = await model_repo.create_model_config(new_model_data, project_id)

    # Return result with warnings about excluded features
    result = ModelConfigRead.model_validate(new_model)

    # Log warnings (in production, this could be returned in response headers or a separate field)
    if excluded_features:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Model config applied with {len(excluded_features)} excluded features: {excluded_features}")

    return result
