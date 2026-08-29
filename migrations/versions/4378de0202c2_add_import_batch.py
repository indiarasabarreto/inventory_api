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
    with op.batch_alter_table("products", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("import_batch_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_products_import_batch_id_import_batches",
            "import_batches",
            ["import_batch_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("products", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "fk_products_import_batch_id_import_batches",
            type_="foreignkey",
        )
        batch_op.drop_column("import_batch_id")

    op.drop_table("import_batches")


