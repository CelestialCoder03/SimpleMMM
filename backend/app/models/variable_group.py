"""Variable Group model."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class VariableGroup(Base, UUIDMixin, TimestampMixin):
    """Variable Group model for organizing marketing variables into logical groups.

    Examples: "Offline Media" (TV, Radio, OOH), "Online Media" (Social, Search, Display)
    Groups can be used for:
    - Applying constraints to entire groups
    - Viewing aggregated contributions
    - Organizing variables in the UI
    """

    __tablename__ = "variable_groups"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # List of variable names in this group (stored as JSON array)
    variables: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Color for visualization (hex code like "#3B82F6")
    color: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="variable_groups",
    )

    def __repr__(self) -> str:
        return f"<VariableGroup {self.name} ({len(self.variables)} vars)>"
