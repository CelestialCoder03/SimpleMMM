"""Schemas for hierarchical models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HierarchicalModelCreate(BaseModel):
    """Schema for creating a hierarchical model configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    parent_model_id: UUID | None = None
    dataset_id: UUID
    dimension_columns: list[str] = Field(..., min_length=1)
    granularity_type: str = "region"
    model_type: str = "ridge"
    target_variable: str
    date_column: str | None = None
    features: list[dict] | None = None
    inherit_constraints: bool = True
    constraint_relaxation: float = Field(default=0.2, ge=0, le=1)
    inherit_priors: bool = True
    prior_weight: float = Field(default=0.5, ge=0, le=1)
    min_observations: int = Field(default=30, ge=10)


class HierarchicalModelUpdate(BaseModel):
    """Schema for updating a hierarchical model configuration."""

    name: str | None = None
    inherit_constraints: bool | None = None
    constraint_relaxation: float | None = Field(default=None, ge=0, le=1)
    inherit_priors: bool | None = None
    prior_weight: float | None = Field(default=None, ge=0, le=1)
    min_observations: int | None = Field(default=None, ge=10)


class SubModelRead(BaseModel):
    """Schema for reading a sub-model."""

    id: UUID
    dimension_values: dict
    status: str
    error_message: str | None = None
    observation_count: int | None = None
    r_squared: float | None = None
    rmse: float | None = None
    training_duration_seconds: float | None = None
    model_config_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HierarchicalModelRead(BaseModel):
    """Schema for reading a hierarchical model configuration."""

    id: UUID
    project_id: UUID
    name: str
    parent_model_id: UUID | None = None
    dataset_id: UUID
    dimension_columns: list[str]
    granularity_type: str
    model_type: str
    target_variable: str
    date_column: str | None = None
    features: list[dict] | None = None
    inherit_constraints: bool
    constraint_relaxation: float
    inherit_priors: bool
    prior_weight: float
    min_observations: int
    status: str
    task_id: str | None = None
    sub_models: list[SubModelRead] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HierarchicalModelList(BaseModel):
    """Schema for listing hierarchical models."""

    id: UUID
    name: str
    granularity_type: str
    model_type: str
    status: str
    sub_model_count: int = 0
    completed_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class TrainingProgress(BaseModel):
    """Schema for training progress."""

    total: int
    completed: int
    failed: int
    in_progress: int
    pending: int


class HierarchicalTrainingStatus(BaseModel):
    """Schema for hierarchical training status."""

    status: str
    progress: TrainingProgress
    sub_models: list[SubModelRead]


class DimensionCombination(BaseModel):
    """Schema for a dimension combination."""

    values: dict
    observation_count: int


class DimensionAnalysis(BaseModel):
    """Schema for dimension analysis."""

    dimension_columns: list[str]
    combinations: list[DimensionCombination]
    total_combinations: int


class CoefficientComparison(BaseModel):
    """Schema for coefficient comparison across sub-models."""

    variable: str
    national_estimate: float | None = None
    national_ci_lower: float | None = None
    national_ci_upper: float | None = None
    sub_model_estimates: dict[str, float]  # dimension_key -> estimate


class HierarchicalResultsSummary(BaseModel):
    """Schema for hierarchical results summary."""

    id: UUID
    name: str
    total_sub_models: int
    completed_sub_models: int
    avg_r_squared: float | None = None
    min_r_squared: float | None = None
    max_r_squared: float | None = None
    coefficient_comparisons: list[CoefficientComparison] = []
