"""Transformation preview API endpoints."""

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbSession
from app.services.modeling.transformations import AdstockTransform, SaturationTransform

router = APIRouter(prefix="/transformations", tags=["Transformations"])


# --- Request/Response Models ---


class AdstockPreviewRequest(BaseModel):
    """Request for adstock transformation preview."""

    values: list[float] = Field(..., min_length=1, description="Input values")
    decay: float = Field(0.5, ge=0, le=1, description="Decay rate")
    max_lag: int = Field(8, ge=1, le=52, description="Maximum lag periods")
    adstock_type: str = Field("geometric", description="Type: geometric or weibull")
    shape: float | None = Field(None, description="Shape parameter for Weibull")
    scale: float | None = Field(None, description="Scale parameter for Weibull")


class SaturationPreviewRequest(BaseModel):
    """Request for saturation transformation preview."""

    values: list[float] = Field(..., min_length=1, description="Input values")
    saturation_type: str = Field("hill", description="Type: hill or logistic")
    k: float = Field(1.0, gt=0, description="Half-saturation point (Hill) or steepness (logistic)")
    s: float = Field(1.0, gt=0, description="Slope/shape parameter")


class CombinedPreviewRequest(BaseModel):
    """Request for combined adstock + saturation preview."""

    values: list[float] = Field(..., min_length=1, description="Input values")

    # Adstock parameters
    apply_adstock: bool = True
    decay: float = Field(0.5, ge=0, le=1)
    max_lag: int = Field(8, ge=1, le=52)
    adstock_type: str = "geometric"

    # Saturation parameters
    apply_saturation: bool = True
    saturation_type: str = "hill"
    k: float | str = Field(1.0, description="Half-saturation or 'auto'")
    s: float | str = Field(1.0, description="Shape or 'auto'")


class TransformationResult(BaseModel):
    """Result of transformation preview."""

    original: list[float]
    transformed: list[float]
    parameters: dict[str, Any]
    statistics: dict[str, float]


# --- Endpoints ---


@router.post("/adstock/preview", response_model=TransformationResult)
async def preview_adstock(
    request: AdstockPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TransformationResult:
    """
    Preview adstock transformation on sample values.

    Shows how advertising effects carry over time.
    - **geometric**: Exponential decay (most common)
    - **weibull**: Delayed peak then decay (for brand building)
    """
    values = np.array(request.values)

    try:
        transform = AdstockTransform(
            decay=request.decay,
            max_lag=request.max_lag,
            adstock_type=request.adstock_type,
            shape=request.shape,
            scale=request.scale,
        )

        transformed = transform.transform(values)

        return TransformationResult(
            original=values.tolist(),
            transformed=transformed.tolist(),
            parameters=transform.get_params(),
            statistics={
                "original_sum": float(values.sum()),
                "transformed_sum": float(transformed.sum()),
                "original_mean": float(values.mean()),
                "transformed_mean": float(transformed.mean()),
                "original_max": float(values.max()),
                "transformed_max": float(transformed.max()),
                "carryover_ratio": float(transformed.sum() / values.sum()) if values.sum() > 0 else 0,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transformation error: {str(e)}",
        )


@router.post("/saturation/preview", response_model=TransformationResult)
async def preview_saturation(
    request: SaturationPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TransformationResult:
    """
    Preview saturation transformation on sample values.

    Shows diminishing returns effect.
    - **hill**: S-curve, most common for marketing
    - **logistic**: Similar S-curve, different parameterization
    """
    values = np.array(request.values)

    try:
        transform = SaturationTransform(
            k=request.k,
            s=request.s,
            saturation_type=request.saturation_type,
        )

        transformed = transform.transform(values)

        # Calculate marginal effects at different points
        marginal_at_mean = _calculate_marginal(transform, values.mean())
        marginal_at_max = _calculate_marginal(transform, values.max())

        return TransformationResult(
            original=values.tolist(),
            transformed=transformed.tolist(),
            parameters=transform.get_params(),
            statistics={
                "original_mean": float(values.mean()),
                "transformed_mean": float(transformed.mean()),
                "original_max": float(values.max()),
                "transformed_max": float(transformed.max()),
                "saturation_at_mean": float(marginal_at_mean),
                "saturation_at_max": float(marginal_at_max),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transformation error: {str(e)}",
        )


@router.post("/combined/preview", response_model=TransformationResult)
async def preview_combined(
    request: CombinedPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> TransformationResult:
    """
    Preview combined adstock + saturation transformation.

    This is the typical MMM transformation pipeline:
    1. Adstock: Capture carryover effects
    2. Saturation: Capture diminishing returns
    """
    values = np.array(request.values)
    transformed = values.copy()
    params = {}

    try:
        # Apply adstock
        if request.apply_adstock:
            adstock = AdstockTransform(
                decay=request.decay,
                max_lag=request.max_lag,
                adstock_type=request.adstock_type,
            )
            transformed = adstock.transform(transformed)
            params["adstock"] = adstock.get_params()

        # Apply saturation
        if request.apply_saturation:
            # Handle auto-fit
            k = request.k
            s = request.s

            if k == "auto" or s == "auto":
                # Simple auto-fit: use percentiles
                k_auto = float(np.percentile(transformed[transformed > 0], 50)) if (transformed > 0).any() else 1.0
                s_auto = 1.0
                k = k_auto if k == "auto" else k
                s = s_auto if s == "auto" else s

            saturation = SaturationTransform(
                k=float(k),
                s=float(s),
                saturation_type=request.saturation_type,
            )
            transformed = saturation.transform(transformed)
            params["saturation"] = saturation.get_params()

        return TransformationResult(
            original=values.tolist(),
            transformed=transformed.tolist(),
            parameters=params,
            statistics={
                "original_sum": float(values.sum()),
                "transformed_sum": float(transformed.sum()),
                "original_mean": float(values.mean()),
                "transformed_mean": float(transformed.mean()),
                "compression_ratio": float(transformed.sum() / values.sum()) if values.sum() > 0 else 0,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transformation error: {str(e)}",
        )


@router.get("/parameters/defaults")
async def get_default_parameters(
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get default transformation parameters and recommended ranges.

    Useful for building configuration UI with sensible defaults.
    """
    return {
        "adstock": {
            "types": ["geometric", "weibull"],
            "defaults": {
                "geometric": {
                    "decay": 0.5,
                    "max_lag": 8,
                },
                "weibull": {
                    "decay": 0.5,
                    "max_lag": 8,
                    "shape": 2.0,
                    "scale": 1.0,
                },
            },
            "ranges": {
                "decay": {"min": 0, "max": 1, "step": 0.05},
                "max_lag": {"min": 1, "max": 52, "step": 1},
                "shape": {"min": 0.5, "max": 10, "step": 0.5},
                "scale": {"min": 0.1, "max": 5, "step": 0.1},
            },
            "descriptions": {
                "decay": "How quickly the effect diminishes (0=no carryover, 1=full carryover)",
                "max_lag": "Maximum number of periods for carryover effect",
                "shape": "Weibull shape parameter (>1 = delayed peak)",
                "scale": "Weibull scale parameter",
            },
        },
        "saturation": {
            "types": ["hill", "logistic"],
            "defaults": {
                "hill": {
                    "k": "auto",
                    "s": 1.0,
                },
                "logistic": {
                    "k": 0.001,
                    "s": 1.0,
                },
            },
            "ranges": {
                "k": {"min": 0.001, "max": "auto", "step": "variable"},
                "s": {"min": 0.1, "max": 5, "step": 0.1},
            },
            "descriptions": {
                "k": "Half-saturation point (spend level at 50% response)",
                "s": "Shape parameter (higher = sharper S-curve)",
            },
        },
    }


def _calculate_marginal(transform: SaturationTransform, x: float) -> float:
    """Calculate marginal effect at a point."""
    epsilon = x * 0.01 if x > 0 else 0.01
    y1 = transform.transform(np.array([x]))[0]
    y2 = transform.transform(np.array([x + epsilon]))[0]
    return float((y2 - y1) / epsilon)
