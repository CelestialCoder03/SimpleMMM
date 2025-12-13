"""Hierarchical model configuration and sub-model models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class GranularityType(str, Enum):
    """Granularity type for hierarchical models."""

    REGION = "region"
    CHANNEL = "channel"
    REGION_CHANNEL = "region_channel"
    CUSTOM = "custom"


class SubModelStatus(str, Enum):
    """Status of a sub-model."""

    PENDING = "pending"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class HierarchicalModelConfig(Base, UUIDMixin, TimestampMixin):
    """
    Hierarchical model configuration.

    Stores the configuration for training multiple sub-models
    based on dimension columns (e.g., region, channel).
    """

    __tablename__ = "hierarchical_model_configs"

    # Project relationship
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Model name
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Parent model (national/aggregate model)
    parent_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Dataset
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Dimension configuration
    dimension_columns: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        comment="List of dimension columns, e.g., ['region', 'channel']",
    )

    granularity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=GranularityType.REGION.value,
    )

    # Model type for sub-models
    model_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ridge",
    )

    # Feature configuration (same as parent or custom)
    target_variable: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    date_column: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    features: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Feature configurations for sub-models",
    )

    # Constraint inheritance settings
    inherit_constraints: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    constraint_relaxation: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.2,
        comment="Relaxation factor for inherited constraints (0-1)",
    )

    # Prior inheritance settings (for Bayesian models)
    inherit_priors: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    prior_weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        comment="Weight for inherited priors (0-1)",
    )

    # Minimum observations per sub-model
    min_observations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=30,
    )

    # Training status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
    )

    # Celery task ID for tracking
    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="hierarchical_configs",
    )

    parent_model: Mapped["ModelConfig"] = relationship(
        "ModelConfig",
        foreign_keys=[parent_model_id],
    )

    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
    )

    sub_models: Mapped[list["SubModelConfig"]] = relationship(
        "SubModelConfig",
        back_populates="hierarchical_config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<HierarchicalModelConfig {self.name}>"


class SubModelConfig(Base, UUIDMixin, TimestampMixin):
    """
    Sub-model configuration and result.

    Represents a single sub-model within a hierarchical model,
    e.g., the model for "华东" region.
    """

    __tablename__ = "sub_model_configs"

    # Parent hierarchical config
    hierarchical_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hierarchical_model_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Associated model config (created during training)
    model_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Dimension values for this sub-model
    dimension_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment='Dimension values, e.g., {"region": "华东", "channel": "线上"}',
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SubModelStatus.PENDING.value,
    )

    # Error message if failed
    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # Data statistics
    observation_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Quick access to key metrics (also in model_result)
    r_squared: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rmse: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    training_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Relationships
    hierarchical_config: Mapped["HierarchicalModelConfig"] = relationship(
        "HierarchicalModelConfig",
        back_populates="sub_models",
    )

    model_config: Mapped["ModelConfig"] = relationship(
        "ModelConfig",
        foreign_keys=[model_config_id],
    )

    def __repr__(self) -> str:
        return f"<SubModelConfig {self.dimension_values}>"
