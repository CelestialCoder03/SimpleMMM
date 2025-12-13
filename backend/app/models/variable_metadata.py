"""Variable Metadata model for variable type classification."""

import uuid
from enum import Enum

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class VariableType(str, Enum):
    """Type classification for variables."""

    TARGET = "target"  # Target variable (sales value, revenue)
    SPENDING = "spending"  # Spending/investment (media spend)
    SUPPORT = "support"  # Support metric without spending (GRPs, impressions)
    DIMENSION = "dimension"  # Dimension column (region, channel, date)
    CONTROL = "control"  # Control variable (price, distribution)
    OTHER = "other"  # Other/unclassified


class VariableMetadata(Base, UUIDMixin, TimestampMixin):
    """
    Variable metadata for classifying and organizing dataset variables.

    This model stores metadata about each variable in a dataset,
    including its type, display name, unit, and relationships.

    Key use cases:
    - ROI calculation: knowing which variables are spending vs support
    - Variable grouping: organizing related variables
    - Display: showing user-friendly names and units
    - Relationships: linking support metrics to their spending counterparts
    """

    __tablename__ = "variable_metadata"

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Dataset relationship (optional - can be project-wide)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Variable name (as in the dataset column)
    variable_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Display name (user-friendly)
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Variable type classification
    variable_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=VariableType.OTHER.value,
    )

    # Unit of measurement
    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of measurement (e.g., 元, 次, GRP, %)",
    )

    # Related variable (for support -> spending mapping)
    # e.g., tv_grp -> tv_spend (for ROI calculation)
    related_spending_variable: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Related spending variable for ROI calculation",
    )

    # Cost per unit (if known, for converting support to spending)
    # e.g., cost per GRP, cost per impression
    cost_per_unit: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Cost per unit for converting support to spending",
    )

    # Group assignment
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("variable_groups.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Description/notes
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
    )

    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
    )

    group: Mapped["VariableGroup"] = relationship(
        "VariableGroup",
    )

    def __repr__(self) -> str:
        return f"<VariableMetadata {self.variable_name} ({self.variable_type})>"

    @property
    def is_spending(self) -> bool:
        """Check if this variable represents spending."""
        return self.variable_type == VariableType.SPENDING.value

    @property
    def is_support(self) -> bool:
        """Check if this variable is a support metric."""
        return self.variable_type == VariableType.SUPPORT.value

    @property
    def can_calculate_roi(self) -> bool:
        """Check if ROI can be calculated for this variable."""
        return self.is_spending or (self.is_support and self.related_spending_variable)
