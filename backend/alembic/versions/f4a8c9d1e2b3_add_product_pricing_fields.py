"""add product pricing fields

Revision ID: f4a8c9d1e2b3
Revises: b7c9d0e1f2a3
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4a8c9d1e2b3"
down_revision: Union[str, Sequence[str], None] = "b7c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column("purchase_price", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column(
            "margin_percent",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("sale_price", sa.Integer(), nullable=True),
    )

    op.execute(
        "UPDATE products "
        "SET purchase_price = price, margin_percent = 0, sale_price = price"
    )

    op.alter_column(
        "products",
        "purchase_price",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "products",
        "sale_price",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "products",
        "margin_percent",
        existing_type=sa.Integer(),
        server_default=None,
    )

    op.drop_constraint("ck_products_price", "products", type_="check")
    op.drop_column("products", "price")

    op.create_check_constraint(
        "ck_products_purchase_price",
        "products",
        "purchase_price > 0",
    )
    op.create_check_constraint(
        "ck_products_margin_percent",
        "products",
        "margin_percent >= 0",
    )
    op.create_check_constraint(
        "ck_products_sale_price",
        "products",
        "sale_price > 0",
    )
    op.create_check_constraint(
        "ck_products_sale_price_floor",
        "products",
        "sale_price * 100 >= purchase_price * (100 + margin_percent)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "products",
        sa.Column("price", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE products SET price = sale_price")
    op.alter_column(
        "products",
        "price",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint("ck_products_sale_price_floor", "products", type_="check")
    op.drop_constraint("ck_products_sale_price", "products", type_="check")
    op.drop_constraint("ck_products_margin_percent", "products", type_="check")
    op.drop_constraint("ck_products_purchase_price", "products", type_="check")

    op.drop_column("products", "sale_price")
    op.drop_column("products", "margin_percent")
    op.drop_column("products", "purchase_price")

    op.create_check_constraint(
        "ck_products_price",
        "products",
        "price > 0",
    )
