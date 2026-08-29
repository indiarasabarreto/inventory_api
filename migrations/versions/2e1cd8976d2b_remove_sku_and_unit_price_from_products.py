"""remove sku and unit price from products

Revision ID: 2e1cd8976d2b
Revises: 75c6d697b43a
Create Date: 2026-08-21 01:27:54.938124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e1cd8976d2b'
down_revision: Union[str, Sequence[str], None] = '75c6d697b43a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products", recreate="always") as batch_op:
        batch_op.drop_column("sku")
        batch_op.drop_column("unit_price")



def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "unit_price",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "sku",
            sa.String(length=100),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_products_sku", "products", ["sku"])

