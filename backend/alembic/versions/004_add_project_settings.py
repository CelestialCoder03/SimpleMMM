"""Add project settings column.

Revision ID: 004
Revises: 003
Create Date: 2024-01-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add settings JSONB column to projects table
    op.add_column(
        "projects",
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "settings")
