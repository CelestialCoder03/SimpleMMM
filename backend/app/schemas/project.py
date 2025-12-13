"""Project schemas."""

from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class ProjectSettings(BaseSchema):
    """Project settings schema."""

    # Default model settings
    default_model_type: str | None = Field(None, description="Default model type for new models")
    default_hyperparameters: dict[str, Any] | None = Field(None, description="Default hyperparameters")

    # Data settings
    date_format: str | None = Field(None, description="Preferred date format")
    currency: str | None = Field(None, description="Currency for monetary values")

    # Display settings
    chart_theme: str | None = Field(None, description="Chart color theme")
    decimal_places: int | None = Field(None, ge=0, le=6, description="Decimal places for numbers")

    # Export settings
    export_format: str | None = Field(None, description="Default export format")
    include_raw_data: bool | None = Field(None, description="Include raw data in exports")


class ProjectBase(BaseSchema):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    settings: ProjectSettings | None = None


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    settings: ProjectSettings | None = None


class ProjectRead(ProjectBase, UUIDSchema, TimestampSchema):
    """Schema for reading a project."""

    owner_id: UUID
    model_count: int = 0
    dataset_count: int = 0
    settings: ProjectSettings | None = None


class ProjectList(BaseSchema):
    """Schema for project list item."""

    id: UUID
    name: str
    description: str | None
    model_count: int = 0
    dataset_count: int = 0
    created_at: str
    updated_at: str
