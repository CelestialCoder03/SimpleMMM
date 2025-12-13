"""add_seasonality_to_model_config

Revision ID: 011
Revises: 010
Create Date: 2025-12-31 13:26:44.618171

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add seasonality column to model_configs
    op.add_column(
        "model_configs",
        sa.Column(
            "seasonality", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    # Remove seasonality column from model_configs
    op.drop_column("model_configs", "seasonality")
