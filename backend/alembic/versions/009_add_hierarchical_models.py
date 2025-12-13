"""Add hierarchical model tables.

Revision ID: 009
Revises: 008
Create Date: 2024-12-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hierarchical_model_configs table
    op.create_table(
        "hierarchical_model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension_columns", postgresql.JSONB(), nullable=False),
        sa.Column(
            "granularity_type", sa.String(50), nullable=False, server_default="region"
        ),
        sa.Column("model_type", sa.String(50), nullable=False, server_default="ridge"),
        sa.Column("target_variable", sa.String(255), nullable=False),
        sa.Column("date_column", sa.String(255), nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.Column(
            "inherit_constraints", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column(
            "constraint_relaxation", sa.Float(), nullable=False, server_default="0.2"
        ),
        sa.Column(
            "inherit_priors", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("prior_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "min_observations", sa.Integer(), nullable=False, server_default="30"
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("task_id", sa.String(255), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_model_id"], ["model_configs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hierarchical_model_configs_project_id",
        "hierarchical_model_configs",
        ["project_id"],
    )

    # Create sub_model_configs table
    op.create_table(
        "sub_model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "hierarchical_config_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("model_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dimension_values", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=True),
        sa.Column("r_squared", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("training_duration_seconds", sa.Float(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["hierarchical_config_id"],
            ["hierarchical_model_configs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_config_id"], ["model_configs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sub_model_configs_hierarchical_config_id",
        "sub_model_configs",
        ["hierarchical_config_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sub_model_configs_hierarchical_config_id", table_name="sub_model_configs"
    )
    op.drop_table("sub_model_configs")
    op.drop_index(
        "ix_hierarchical_model_configs_project_id",
        table_name="hierarchical_model_configs",
    )
    op.drop_table("hierarchical_model_configs")
