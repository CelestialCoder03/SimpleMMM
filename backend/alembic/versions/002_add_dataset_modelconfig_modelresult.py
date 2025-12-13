"""Add dataset, model_config, model_result tables.

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("file_path", sa.String(512), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column(
            "columns_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_datasets_project_id"), "datasets", ["project_id"], unique=False
    )

    # Create model_configs table
    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_type", sa.String(20), nullable=False, server_default="ridge"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("target_variable", sa.String(255), nullable=False),
        sa.Column("date_column", sa.String(255), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "granularity", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("priors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "hyperparameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_configs_project_id"),
        "model_configs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_configs_dataset_id"),
        "model_configs",
        ["dataset_id"],
        unique=False,
    )

    # Create model_results table
    op.create_table(
        "model_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("model_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("training_duration_seconds", sa.Float(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "coefficients", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "contributions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "decomposition", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "response_curves", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "fitted_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("model_artifact_path", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["model_config_id"], ["model_configs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_config_id"),
    )
    op.create_index(
        op.f("ix_model_results_model_config_id"),
        "model_results",
        ["model_config_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_results_model_config_id"), table_name="model_results")
    op.drop_table("model_results")
    op.drop_index(op.f("ix_model_configs_dataset_id"), table_name="model_configs")
    op.drop_index(op.f("ix_model_configs_project_id"), table_name="model_configs")
    op.drop_table("model_configs")
    op.drop_index(op.f("ix_datasets_project_id"), table_name="datasets")
    op.drop_table("datasets")
