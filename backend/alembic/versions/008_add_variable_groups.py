"""Add variable_groups table.

Revision ID: 008
Revises: 007
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "variable_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("variables", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("color", sa.String(20), nullable=True),
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
    )

    # Add unique constraint for name within a project
    op.create_unique_constraint(
        "uq_variable_groups_project_name",
        "variable_groups",
        ["project_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_variable_groups_project_name", "variable_groups", type_="unique"
    )
    op.drop_table("variable_groups")
