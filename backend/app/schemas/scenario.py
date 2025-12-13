"""Scenario schemas."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class ScenarioStatus(str, Enum):
    """Scenario calculation status."""

    DRAFT = "draft"
    CALCULATING = "calculating"
    READY = "ready"
    FAILED = "failed"


class AdjustmentType(str, Enum):
    """Type of variable adjustment."""

    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"
    MULTIPLIER = "multiplier"


class VariableAdjustment(BaseSchema):
    """Schema for a single variable adjustment."""

    variable: str
    type: AdjustmentType = AdjustmentType.PERCENTAGE
    value: float = Field(..., description="Adjustment value (e.g., 10 for 10% increase)")


class ScenarioCreate(BaseSchema):
    """Schema for creating a scenario."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    model_id: UUID
    adjustments: list[VariableAdjustment] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None


class ScenarioUpdate(BaseSchema):
    """Schema for updating a scenario."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    adjustments: list[VariableAdjustment] | None = None
    start_date: str | None = None
    end_date: str | None = None


class ScenarioRead(UUIDSchema, TimestampSchema):
    """Schema for reading a scenario."""

    name: str
    description: str | None
    project_id: UUID
    model_id: UUID
    status: ScenarioStatus
    adjustments: dict[str, Any]
    start_date: str | None
    end_date: str | None
    baseline_total: float | None
    scenario_total: float | None
    lift_percentage: float | None


class ScenarioResults(BaseSchema):
    """Schema for scenario calculation results."""

    scenario_id: UUID
    dates: list[str]
    baseline: list[float]
    scenario: list[float]
    baseline_contributions: dict[str, list[float]]
    scenario_contributions: dict[str, list[float]]
    summary: dict[str, Any]


class ScenarioComparison(BaseSchema):
    """Schema for comparing multiple scenarios."""

    scenarios: list[ScenarioRead]
    comparison: dict[str, Any]


class ScenarioForecast(BaseSchema):
    """Schema for scenario forecast request."""

    periods: int = Field(default=12, ge=1, le=52)
    adjustments: list[VariableAdjustment] = Field(default_factory=list)
