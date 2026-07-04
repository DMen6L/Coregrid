"""add low stock threshold

Revision ID: b7c9d0e1f2a3
Revises: e6a3f4d5c2b1
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "e6a3f4d5c2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_products_low_stock_threshold",
        "products",
        "low_stock_threshold >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_products_low_stock_threshold",
        "products",
        type_="check",
    )
    op.drop_column("products", "low_stock_threshold")
