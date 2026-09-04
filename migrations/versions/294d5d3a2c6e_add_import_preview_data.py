"""add import preview data

Revision ID: 294d5d3a2c6e
Revises: 4378de0202c2
Create Date: 2026-09-03 21:09:46.504876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '294d5d3a2c6e'
down_revision: Union[str, Sequence[str], None] = '4378de0202c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "import_batches",
        sa.Column("preview_data", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("import_batches", "preview_data")
