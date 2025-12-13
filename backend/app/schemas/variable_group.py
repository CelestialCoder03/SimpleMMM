"""Variable Group schemas."""

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class VariableGroupBase(BaseSchema):
    """Base schema for variable groups."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    variables: list[str] = Field(..., min_length=1)
    color: str | None = Field(None, max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")


class VariableGroupCreate(VariableGroupBase):
    """Schema for creating a variable group."""

    pass


class VariableGroupUpdate(BaseSchema):
    """Schema for updating a variable group."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    variables: list[str] | None = Field(None, min_length=1)
    color: str | None = Field(None, max_length=20, pattern=r"^#[0-9A-Fa-f]{6}$")


class VariableGroupRead(VariableGroupBase, UUIDSchema, TimestampSchema):
    """Schema for reading a variable group."""

    pass


class VariableGroupList(BaseSchema):
    """Schema for listing variable groups."""

    items: list[VariableGroupRead]
    total: int
