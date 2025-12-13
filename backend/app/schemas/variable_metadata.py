"""Schemas for variable metadata."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VariableMetadataCreate(BaseModel):
    """Schema for creating variable metadata."""

    variable_name: str = Field(..., min_length=1, max_length=255)
    dataset_id: UUID | None = None
    display_name: str | None = None
    variable_type: str = "other"
    unit: str | None = None
    related_spending_variable: str | None = None
    cost_per_unit: float | None = None
    group_id: UUID | None = None
    description: str | None = None


class VariableMetadataUpdate(BaseModel):
    """Schema for updating variable metadata."""

    display_name: str | None = None
    variable_type: str | None = None
    unit: str | None = None
    related_spending_variable: str | None = None
    cost_per_unit: float | None = None
    group_id: UUID | None = None
    description: str | None = None


class VariableMetadataRead(BaseModel):
    """Schema for reading variable metadata."""

    id: UUID
    project_id: UUID
    dataset_id: UUID | None = None
    variable_name: str
    display_name: str | None = None
    variable_type: str
    unit: str | None = None
    related_spending_variable: str | None = None
    cost_per_unit: float | None = None
    group_id: UUID | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VariableMetadataBulkUpdate(BaseModel):
    """Schema for bulk updating variable metadata."""

    variables: list[VariableMetadataCreate]


class VariableTypeOption(BaseModel):
    """Schema for variable type options."""

    value: str
    label: str
    description: str


class VariableSummary(BaseModel):
    """Schema for variable summary with metadata."""

    name: str
    dtype: str | None = None
    metadata: VariableMetadataRead | None = None
    group_name: str | None = None
    group_color: str | None = None
