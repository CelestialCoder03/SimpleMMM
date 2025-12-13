"""Model configuration model."""

import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ModelType(str, Enum):
    """Supported model types."""

    OLS = "ols"
    RIDGE = "ridge"
    ELASTICNET = "elasticnet"
    BAYESIAN = "bayesian"


class ModelStatus(str, Enum):
    """Model training status."""

    PENDING = "pending"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelConfig(Base, UUIDMixin, TimestampMixin):
    """Model configuration for MMM training."""

    __tablename__ = "model_configs"

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
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Model type
    model_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ModelType.RIDGE.value,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ModelStatus.PENDING.value,
    )

    # Target and date columns
    target_variable: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    date_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Feature configuration (JSON)
    features: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Granularity configuration (JSON)
    granularity: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Constraints configuration (JSON)
    constraints: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Priors for Bayesian models (JSON)
    priors: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Hyperparameters (JSON)
    hyperparameters: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Seasonality configuration (JSON)
    seasonality: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Celery task ID for async training
    task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Error message if training failed
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="model_configs",
    )
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        back_populates="model_configs",
    )
    result: Mapped["ModelResult"] = relationship(
        "ModelResult",
        back_populates="model_config",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario",
        back_populates="model_config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ModelConfig {self.name} ({self.model_type})>"
