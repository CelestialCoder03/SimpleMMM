"""Base schema classes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""

    created_at: datetime
    updated_at: datetime


class UUIDSchema(BaseSchema):
    """Schema with UUID field."""

    id: UUID


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""

    items: list
    total: int
    page: int
    limit: int
    pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, limit: int):
        """Create paginated response."""
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(items=items, total=total, page=page, limit=limit, pages=pages)
