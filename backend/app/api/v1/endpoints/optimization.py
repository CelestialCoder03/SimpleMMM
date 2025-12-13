"""Budget optimization endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.repositories.model_config import ModelConfigRepository
from app.repositories.project import ProjectRepository
from app.services.optimization import optimize_budget

router = APIRouter(prefix="/projects/{project_id}/optimize", tags=["Optimization"])


class ChannelConstraintInput(BaseModel):
    """Input schema for channel constraint."""

    channel: str
    min_budget: float | None = None
    max_budget: float | None = None
    min_share: float | None = Field(None, ge=0, le=100)
    max_share: float | None = Field(None, ge=0, le=100)


class OptimizationRequest(BaseModel):
    """Request schema for budget optimization."""

    model_id: UUID
    total_budget: float = Field(..., gt=0)
    objective: str = Field(default="maximize_response")
    constraints: list[ChannelConstraintInput] = Field(default_factory=list)


class OptimizationResponse(BaseModel):
    """Response schema for optimization results."""

    success: bool
    message: str
    objective: str
    total_budget: float
    current_allocation: dict[str, float]
    current_response: float
    current_roi: float
    optimized_allocation: dict[str, float]
    optimized_response: float
    optimized_roi: float
    response_lift: float
    response_lift_pct: float
    roi_improvement: float
    channel_changes: dict[str, dict[str, float]]


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


@router.post("/budget", response_model=OptimizationResponse)
async def optimize_budget_allocation(
    project_id: UUID,
    request: OptimizationRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> OptimizationResponse:
    """
    Optimize budget allocation across marketing channels.

    Uses model coefficients and response curves to find the optimal
    budget distribution that maximizes response or ROI.
    """
    await verify_project_access(project_id, current_user, db)

    # Get model
    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(request.model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found in this project",
        )

    if model.status != "completed" or model.result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model must be trained with results available",
        )

    # Extract model data
    coefficients = model.result.coefficients or {}
    contributions = model.result.contributions or {}

    # Get marketing channels (features with positive/non-zero contributions)
    channels = [
        ch
        for ch in coefficients.keys()
        if ch not in ["intercept", "base", "trend", "seasonality"] and coefficients.get(ch, 0) != 0
    ]

    if not channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No marketing channels found in model",
        )

    # Estimate current spend from contributions (simplified)
    # In production, this would come from actual spend data
    current_spend = {}
    for ch in channels:
        contrib = contributions.get(ch, [])
        if contrib:
            # Use average contribution as proxy for spend
            current_spend[ch] = sum(contrib) / len(contrib) if contrib else 0
        else:
            current_spend[ch] = 0

    # Get saturation parameters if available
    saturation_params = {}
    features_config = model.features or {}
    for ch in channels:
        if ch in features_config:
            feat_config = features_config[ch]
            if "saturation" in feat_config:
                sat_config = feat_config["saturation"]
                saturation_params[ch] = {
                    "half_saturation": sat_config.get("half_saturation", 1.0),
                    "slope": sat_config.get("slope", 1.0),
                }

    # Convert constraints
    constraints = [
        {
            "channel": c.channel,
            "min_budget": c.min_budget,
            "max_budget": c.max_budget,
            "min_share": c.min_share,
            "max_share": c.max_share,
        }
        for c in request.constraints
    ]

    # Run optimization
    try:
        result = optimize_budget(
            channels=channels,
            coefficients=coefficients,
            current_spend=current_spend,
            total_budget=request.total_budget,
            objective=request.objective,
            constraints=constraints if constraints else None,
            saturation_params=saturation_params if saturation_params else None,
        )

        return OptimizationResponse(**result.to_dict())

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}",
        )


@router.get("/channels")
async def get_optimization_channels(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """
    Get available channels and their current allocation for optimization.
    """
    await verify_project_access(project_id, current_user, db)

    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    if model.result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model results not available",
        )

    coefficients = model.result.coefficients or {}
    contributions = model.result.contributions or {}

    channels = []
    total_contribution = 0

    for ch, coef in coefficients.items():
        if ch in ["intercept", "base", "trend", "seasonality"]:
            continue

        contrib = contributions.get(ch, [])
        avg_contrib = sum(contrib) / len(contrib) if contrib else 0
        total_contrib = sum(contrib) if contrib else 0
        total_contribution += total_contrib

        channels.append(
            {
                "name": ch,
                "coefficient": round(coef, 4),
                "average_contribution": round(avg_contrib, 2),
                "total_contribution": round(total_contrib, 2),
            }
        )

    # Calculate share percentages
    for ch in channels:
        ch["share_pct"] = round(
            ch["total_contribution"] / total_contribution * 100 if total_contribution > 0 else 0,
            2,
        )

    return {
        "model_id": str(model_id),
        "channels": channels,
        "total_contribution": round(total_contribution, 2),
    }
