"""Pydantic schemas for project members."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.project_member import ProjectRole


class ProjectMemberBase(BaseModel):
    """Base schema for project members."""

    role: ProjectRole = Field(default=ProjectRole.VIEWER)


class ProjectMemberCreate(BaseModel):
    """Schema for adding a member to a project."""

    email: EmailStr = Field(..., description="Email of user to invite")
    role: ProjectRole = Field(default=ProjectRole.VIEWER)


class ProjectMemberUpdate(BaseModel):
    """Schema for updating a member's role."""

    role: ProjectRole


class ProjectMemberUser(BaseModel):
    """User info for member response."""

    id: UUID
    email: str
    full_name: str

    model_config = {"from_attributes": True}


class ProjectMemberResponse(BaseModel):
    """Schema for project member response."""

    id: UUID
    project_id: UUID
    user_id: UUID
    role: ProjectRole
    created_at: datetime
    user: ProjectMemberUser

    model_config = {"from_attributes": True}


class ProjectMemberListResponse(BaseModel):
    """Schema for list of project members."""

    members: list[ProjectMemberResponse]
    total: int
