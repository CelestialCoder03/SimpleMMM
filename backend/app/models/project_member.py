"""Project member model for collaboration."""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ProjectRole(str, enum.Enum):
    """Roles for project members."""

    OWNER = "owner"  # Full control, can delete project and manage members
    EDITOR = "editor"  # Can edit models, datasets, run training
    VIEWER = "viewer"  # Read-only access to project and results


class ProjectMember(Base, UUIDMixin, TimestampMixin):
    """Project member model for sharing projects with other users."""

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ProjectRole] = mapped_column(
        Enum(ProjectRole),
        nullable=False,
        default=ProjectRole.VIEWER,
    )
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="project_memberships",
    )
    invited_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[invited_by_id],
    )

    def __repr__(self) -> str:
        return f"<ProjectMember {self.user_id} in {self.project_id} as {self.role}>"
