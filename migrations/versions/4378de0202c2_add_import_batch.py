"""add import batch

Revision ID: 4378de0202c2
Revises: d8fb18c2c01d
Create Date: 2026-08-29 02:50:31.906258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4378de0202c2'
down_revision: Union[str, Sequence[str], None] = 'd8fb18c2c01d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "products",
        sa.Column("import_batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_import_batch_id_import_batches",
        "products",
        "import_batches",
        ["import_batch_id"],
        ["id"],
    )

def downgrade() -> None:
    op.drop_constraint(
        "fk_products_import_batch_id_import_batches",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "import_batch_id")
    op.drop_table("import_batches")


