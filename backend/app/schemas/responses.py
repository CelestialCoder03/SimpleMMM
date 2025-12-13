"""Response schemas for model results."""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema
from app.schemas.model_config import ModelStatus, ModelType


class ModelMetrics(BaseSchema):
    """Model fit metrics."""

    r_squared: float = Field(..., description="R-squared")
    adjusted_r_squared: float = Field(..., description="Adjusted R-squared")
    rmse: float = Field(..., description="Root Mean Square Error")
    mape: float = Field(..., description="Mean Absolute Percentage Error")
    aic: float | None = Field(None, description="Akaike Information Criterion")
    bic: float | None = Field(None, description="Bayesian Information Criterion")


class CoefficientResult(BaseSchema):
    """Coefficient estimate for a variable."""

    variable: str
    estimate: float
    std_error: float | None = None
    ci_lower: float | None = Field(None, description="95% CI lower bound")
    ci_upper: float | None = Field(None, description="95% CI upper bound")
    p_value: float | None = None
    is_significant: bool | None = None


class ContributionResult(BaseSchema):
    """Contribution result for a variable."""

    variable: str
    total_contribution: float = Field(..., description="Total absolute contribution")
    contribution_pct: float = Field(..., description="Percentage of total")
    avg_contribution: float = Field(..., description="Average per period")
    min_contribution: float | None = None
    max_contribution: float | None = None


class DecompositionTimeSeries(BaseSchema):
    """Time series decomposition data."""

    dates: list[str]
    actual: list[float]
    predicted: list[float]
    base: list[float]
    contributions: dict[str, list[float]] = Field(
        ...,
        description="Contribution by variable over time",
    )


class ResponseCurve(BaseSchema):
    """Response curve for a variable."""

    variable: str
    spend_levels: list[float]
    response_values: list[float]
    marginal_response: list[float] | None = None
    roi_values: list[float] | None = None


class DiagnosticsResult(BaseSchema):
    """Model diagnostics."""

    # Multicollinearity
    vif: dict[str, float] | None = Field(
        None,
        description="Variance Inflation Factor by variable",
    )

    # Bayesian diagnostics
    r_hat: dict[str, float] | None = Field(
        None,
        description="R-hat convergence diagnostic",
    )
    ess: dict[str, float] | None = Field(
        None,
        description="Effective Sample Size",
    )

    # Residual diagnostics
    durbin_watson: float | None = Field(
        None,
        description="Durbin-Watson statistic for autocorrelation",
    )
    jarque_bera_pvalue: float | None = Field(
        None,
        description="Jarque-Bera test p-value for normality",
    )


class ModelResultRead(UUIDSchema, TimestampSchema):
    """Complete model result."""

    name: str
    model_type: ModelType
    status: ModelStatus
    project_id: UUID
    dataset_id: UUID

    # Training info
    task_id: str | None = None
    training_duration_seconds: float | None = None

    # Results (only when status=completed)
    metrics: ModelMetrics | None = None
    coefficients: list[CoefficientResult] | None = None
    contributions: list[ContributionResult] | None = None
    diagnostics: DiagnosticsResult | None = None

    # Error info (only when status=failed)
    error_message: str | None = None


class ModelTrainingStatus(BaseSchema):
    """Model training status response."""

    model_id: UUID
    status: ModelStatus
    progress: int = Field(..., ge=0, le=100)
    current_step: str | None = None
    estimated_remaining_seconds: int | None = None


class TaskStatus(BaseSchema):
    """Generic task status."""

    task_id: str
    status: str
    progress: int = Field(default=0, ge=0, le=100)
    message: str | None = None
    result: dict[str, Any] | None = None
