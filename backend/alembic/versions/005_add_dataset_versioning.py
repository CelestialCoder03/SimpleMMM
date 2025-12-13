"""Add dataset versioning columns.

Revision ID: 005
Revises: 004
Create Date: 2024-01-15

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add versioning columns to datasets table
    op.add_column(
        "datasets",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "datasets",
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "datasets",
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Create index on parent_id
    op.create_index("ix_datasets_parent_id", "datasets", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_datasets_parent_id", table_name="datasets")
    op.drop_column("datasets", "is_latest")
    op.drop_column("datasets", "parent_id")
    op.drop_column("datasets", "version")
