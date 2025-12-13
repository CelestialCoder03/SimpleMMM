"""Add scenarios table.

Revision ID: 007
Revises: 006
Create Date: 2024-01-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
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
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_configs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column(
            "adjustments", postgresql.JSONB(), nullable=False, server_default="{}"
        ),
        sa.Column("start_date", sa.String(20), nullable=True),
        sa.Column("end_date", sa.String(20), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("baseline_total", sa.Float(), nullable=True),
        sa.Column("scenario_total", sa.Float(), nullable=True),
        sa.Column("lift_percentage", sa.Float(), nullable=True),
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


def downgrade() -> None:
    op.drop_table("scenarios")
