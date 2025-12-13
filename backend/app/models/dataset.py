"""Dataset model."""

import uuid
from enum import Enum

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class DatasetStatus(str, Enum):
    """Dataset processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Dataset(Base, UUIDMixin, TimestampMixin):
    """Dataset model for storing uploaded data files."""

    __tablename__ = "datasets"

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
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DatasetStatus.PENDING.value,
    )

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_latest: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    # File information
    file_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    # Data statistics
    row_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    column_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Column metadata stored as JSON
    columns_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Error message if processing failed
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="datasets",
    )
    model_configs: Mapped[list["ModelConfig"]] = relationship(
        "ModelConfig",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Dataset {self.name}>"
