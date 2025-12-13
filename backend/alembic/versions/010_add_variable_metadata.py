"""Add variable metadata table.

Revision ID: 010
Revises: 009
Create Date: 2024-12-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "variable_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variable_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column(
            "variable_type", sa.String(50), nullable=False, server_default="other"
        ),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("related_spending_variable", sa.String(255), nullable=True),
        sa.Column("cost_per_unit", sa.Float(), nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["group_id"], ["variable_groups.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_variable_metadata_project_id", "variable_metadata", ["project_id"]
    )
    op.create_index(
        "ix_variable_metadata_dataset_id", "variable_metadata", ["dataset_id"]
    )
    op.create_index(
        "ix_variable_metadata_variable_name",
        "variable_metadata",
        ["project_id", "variable_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_variable_metadata_variable_name", table_name="variable_metadata")
    op.drop_index("ix_variable_metadata_dataset_id", table_name="variable_metadata")
    op.drop_index("ix_variable_metadata_project_id", table_name="variable_metadata")
    op.drop_table("variable_metadata")
