"""Schemas for constraint validation API."""

from typing import Literal

from pydantic import BaseModel, Field


class ConstraintConflictResponse(BaseModel):
    """Response schema for a single constraint conflict."""

    type: Literal["error", "warning", "info"]
    code: str
    message: str
    affected_variables: list[str] = Field(default_factory=list)
    affected_groups: list[str] = Field(default_factory=list)
    suggestion: str | None = None


class ValidateConstraintsRequest(BaseModel):
    """Request schema for constraint validation."""

    coefficient_constraints: list[dict] = Field(default_factory=list)
    contribution_constraints: list[dict] = Field(default_factory=list)
    group_constraints: list[dict] = Field(default_factory=list)


class ValidateConstraintsResponse(BaseModel):
    """Response schema for constraint validation."""

    valid: bool
    conflicts: list[ConstraintConflictResponse] = Field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0
