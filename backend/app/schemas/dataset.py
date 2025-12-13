"""Dataset schemas."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class DatasetStatus(str, Enum):
    """Dataset processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ColumnType(str, Enum):
    """Column data types."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


class ColumnInfo(BaseSchema):
    """Schema for column information."""

    name: str
    dtype: str
    column_type: ColumnType
    non_null_count: int
    null_count: int
    unique_count: int

    # Numeric stats (optional)
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    median: float | None = None

    # Categorical stats (optional)
    top_values: list[dict[str, Any]] | None = None


class DatasetCreate(BaseSchema):
    """Schema for creating a dataset."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class DatasetRead(UUIDSchema, TimestampSchema):
    """Schema for reading a dataset."""

    name: str
    description: str | None
    project_id: UUID
    status: DatasetStatus
    file_name: str | None
    file_size: int | None
    row_count: int | None
    column_count: int | None = None
    columns_metadata: list[ColumnInfo] | None = Field(default=None, serialization_alias="columns")
    error_message: str | None = None

    # Versioning
    version: int = 1
    parent_id: UUID | None = None
    is_latest: bool = True


class DatasetVersion(BaseSchema):
    """Schema for dataset version info."""

    id: UUID
    version: int
    created_at: str
    status: DatasetStatus
    row_count: int | None
    is_latest: bool


class DatasetPreview(BaseSchema):
    """Schema for dataset preview."""

    dataset_id: UUID
    columns: list[str]
    data: list[dict[str, Any]]
    total_rows: int
    preview_rows: int


class DatasetStats(BaseSchema):
    """Schema for dataset statistics."""

    dataset_id: UUID
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    memory_usage_bytes: int
    date_range: dict[str, str] | None = None
    correlation_matrix: dict[str, dict[str, float]] | None = None
