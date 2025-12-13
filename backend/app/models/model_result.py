"""Model result model."""

import uuid

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class ModelResult(Base, UUIDMixin, TimestampMixin):
    """Model result storing trained model outputs."""

    __tablename__ = "model_results"

    model_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_configs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Training metadata
    training_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Model fit metrics (JSON)
    metrics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="R², adj R², RMSE, MAPE, AIC, BIC",
    )

    # Coefficient estimates (JSON)
    coefficients: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Variable coefficients with CI",
    )

    # Contribution decomposition (JSON)
    contributions: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Total and percentage contributions",
    )

    # Time series decomposition (JSON)
    decomposition: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Time series with actual, predicted, contributions",
    )

    # Response curves (JSON)
    response_curves: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Spend vs response curves per variable",
    )

    # Model diagnostics (JSON)
    diagnostics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="VIF, R-hat, ESS, residual tests",
    )

    # Fitted transformation parameters (JSON)
    fitted_params: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Fitted adstock decay, saturation params",
    )

    # Serialized model artifact path
    model_artifact_path: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="Path to pickled model file",
    )

    # Relationship
    model_config: Mapped["ModelConfig"] = relationship(
        "ModelConfig",
        back_populates="result",
    )

    def __repr__(self) -> str:
        return f"<ModelResult for config {self.model_config_id}>"
