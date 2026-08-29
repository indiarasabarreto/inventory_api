"""add parent category

Revision ID: d8fb18c2c01d
Revises: 2e1cd8976d2b
Create Date: 2026-08-28 21:14:45.309624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8fb18c2c01d'
down_revision: Union[str, Sequence[str], None] = '2e1cd8976d2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_categories_parent_id_categories",
        "categories",
        "categories",
        ["parent_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_categories_parent_id_categories",
        "categories",
        type_="foreignkey",
    )
    op.drop_column("categories", "parent_id")

