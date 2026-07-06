"""add quantity units

Revision ID: 4f72b0ac9d31
Revises: c7d8e9f0a1b2
Create Date: 2026-07-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f72b0ac9d31"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "quantity_unit",
            sa.String(length=20),
            server_default="шт",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_products_quantity_unit_not_empty",
        "products",
        "char_length(quantity_unit) > 0",
    )

    op.add_column(
        "stock_movement_lines",
        sa.Column(
            "quantity_unit_snapshot",
            sa.String(length=20),
            server_default="шт",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_stock_movement_lines_quantity_unit_snapshot_not_empty",
        "stock_movement_lines",
        "char_length(quantity_unit_snapshot) > 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_stock_movement_lines_quantity_unit_snapshot_not_empty",
        "stock_movement_lines",
        type_="check",
    )
    op.drop_column("stock_movement_lines", "quantity_unit_snapshot")

    op.drop_constraint(
        "ck_products_quantity_unit_not_empty",
        "products",
        type_="check",
    )
    op.drop_column("products", "quantity_unit")
