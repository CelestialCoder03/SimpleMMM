"""Scenario model for what-if analysis."""

import uuid
from enum import Enum

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ScenarioStatus(str, Enum):
    """Scenario calculation status."""

    DRAFT = "draft"
    CALCULATING = "calculating"
    READY = "ready"
    FAILED = "failed"


class Scenario(Base, UUIDMixin, TimestampMixin):
    """
    Scenario model for what-if analysis.

    Allows users to create hypothetical scenarios by adjusting
    marketing spend levels and forecasting outcomes.
    """

    __tablename__ = "scenarios"

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
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ScenarioStatus.DRAFT.value,
    )

    # Scenario configuration - variable adjustments
    # Format: {"variable_name": {"type": "percentage|absolute", "value": 10.0}}
    adjustments: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Time range for scenario (optional, defaults to model's range)
    start_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    end_date: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Calculated results
    # Format: {"dates": [...], "baseline": [...], "scenario": [...],
    #          "contributions": {...}, "summary": {...}}
    results: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Summary metrics
    baseline_total: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    scenario_total: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    lift_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="scenarios",
    )
    model_config: Mapped["ModelConfig"] = relationship(
        "ModelConfig",
        back_populates="scenarios",
    )

    def __repr__(self) -> str:
        return f"<Scenario {self.name}>"
